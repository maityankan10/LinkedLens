import json
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.schemas.linkedin import LinkedInAnalyzeResponse, LinkedInInsights
from app.services.ai import analyze_profile, summarize_posts, generate_insights, chat_with_ai
from app.services.profile_parser import trim_profile_for_llm, extract_display_info
from app.services.posts_parser import get_posts_for_profile
from app.services.apify import fetch_linkedin_profile, fetch_linkedin_posts
from app.models.session import Session
from app.models.analysis import Analysis
from app.models.chat_message import ChatMessage


# ── Cache builder ──────────────────────────────────────────────────────────────

def _build_response_from_cache(session_id: str, analysis: Analysis) -> LinkedInAnalyzeResponse:
    insights = LinkedInInsights(
        profile_summary=analysis.profile_summary,
        strengths=json.loads(analysis.strengths or "[]"),
        areas_for_improvement=json.loads(analysis.improvements or "[]"),
        content_ideas=json.loads(analysis.content_ideas or "[]"),
        recommended_topics=json.loads(analysis.recommended_topics or "[]"),
        profile_score=analysis.profile_score,
    )

    return LinkedInAnalyzeResponse(
        session_id=session_id,
        name=analysis.profile_name or "",
        headline=analysis.profile_headline or "",
        location=analysis.profile_location,
        profile_picture=analysis.profile_picture,
        follower_count=analysis.follower_count or 0,
        insights=insights,
    )


# ── Main service functions ─────────────────────────────────────────────────────

async def get_profile_insights(linkedin_url: str, db: AsyncSession) -> LinkedInAnalyzeResponse | None:
    url = linkedin_url.rstrip("/")

    # 1. Check cache — return immediately if analysis already exists
    result = await db.execute(
        select(Session, Analysis)
        .join(Analysis, Analysis.session_id == Session.id)
        .where(Session.linkedin_url == url)
    )
    existing = result.first()
    if existing:
        session, analysis = existing
        print(f"[cache hit] Returning cached analysis for {url}")
        return _build_response_from_cache(session.id, analysis)

    # 2. Fetch profile + posts from Apify concurrently
    import asyncio
    print(f"[apify] Fetching profile and posts for {url}")
    profile, raw_posts = await asyncio.gather(
        fetch_linkedin_profile(url),
        fetch_linkedin_posts(url),
    )

    if not profile:
        print(f"[not found] Apify returned no profile for {url}")
        return None

    # 3. Trim profile for LLM and extract display fields
    trimmed_profile = trim_profile_for_llm(profile)
    display = extract_display_info(profile)

    # 4. Posts pipeline
    posts_summary = None
    posts_text = get_posts_for_profile(url, raw_posts)
    print("IMPORTANT: Raw posts text to be fed into LLM (after trimming):")
    print(posts_text)

    if posts_text and posts_text != "No posts available.":
        print(f"[posts] Found posts for {url}, running summarization...")
        posts_summary = await summarize_posts(posts_text)
        print(f"[posts] Summary generated ({len(posts_summary)} chars)")
    else:
        print(f"[posts] No posts found for {url}, skipping summarization")

    # 5. Generate insights
    if posts_summary:
        print(f"[insights] Running two-stage pipeline (profile + posts)")
        insights = await generate_insights(trimmed_profile, posts_summary)
    else:
        print(f"[insights] Running profile-only analysis (no posts data)")
        insights = await analyze_profile(trimmed_profile)

    # 6. Persist session
    session = Session(id=str(uuid.uuid4()), linkedin_url=url)
    db.add(session)
    await db.flush()

    # 7. Persist analysis (including display fields for future cache hits)
    analysis = Analysis(
        id=str(uuid.uuid4()),
        session_id=session.id,
        linkedin_url=url,
        profile_summary=insights.profile_summary,
        strengths=json.dumps(insights.strengths),
        improvements=json.dumps(insights.areas_for_improvement),
        content_ideas=json.dumps(insights.content_ideas),
        recommended_topics=json.dumps(insights.recommended_topics),
        profile_score=insights.profile_score,
        posts_summary=posts_summary,
        profile_name=display["name"],
        profile_headline=display["headline"],
        profile_location=display["location"],
        profile_picture=display["profile_picture"],
        follower_count=display["follower_count"],
    )
    db.add(analysis)
    await db.commit()

    return LinkedInAnalyzeResponse(
        session_id=session.id,
        name=display["name"],
        headline=display["headline"],
        location=display["location"],
        profile_picture=display["profile_picture"],
        follower_count=display["follower_count"],
        insights=insights,
    )


async def chat_with_profile(session_id: str, message: str, db: AsyncSession) -> str | None:
    # 1. Load session + analysis
    result = await db.execute(
        select(Session, Analysis)
        .join(Analysis, Analysis.session_id == Session.id)
        .where(Session.id == session_id)
    )
    existing = result.first()
    if not existing:
        return None

    session, analysis = existing

    # 2. Fetch last 5 messages for context
    messages_result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.desc())
        .limit(5)
    )
    last_5 = messages_result.scalars().all()[::-1]

    # 3. Save user message
    user_msg = ChatMessage(
        id=str(uuid.uuid4()),
        session_id=session_id,
        role="user",
        content=message,
    )
    print(f"[chat] Saving user message: '{message}'")
    db.add(user_msg)

    # 4. Get AI reply
    reply = await chat_with_ai(analysis, last_5, message)

    # 5. Save assistant message
    assistant_msg = ChatMessage(
        id=str(uuid.uuid4()),
        session_id=session_id,
        role="assistant",
        content=reply,
    )
    db.add(assistant_msg)
    await db.commit()

    return reply
