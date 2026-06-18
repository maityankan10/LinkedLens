import json
import os
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.schemas.linkedin import LinkedInAnalyzeResponse, LinkedInInsights
from app.services.ai import analyze_profile, summarize_posts, generate_insights, chat_with_ai
from app.services.profile_parser import trim_profile_for_llm, extract_display_info
from app.services.posts_parser import get_posts_for_profile
from app.models.session import Session
from app.models.analysis import Analysis
from app.models.chat_message import ChatMessage

# ── Sample data loading ────────────────────────────────────────────────────────

PROFILES_PATH = os.path.join(os.path.dirname(__file__), "../../sample_data/profiles.json")
ENGAGEMENT_PATH = os.path.join(os.path.dirname(__file__), "../../sample_data/engagements.json")


def load_sample_profiles() -> dict:
    with open(PROFILES_PATH, "r") as f:
        profiles = json.load(f)
    return {p["linkedinUrl"]: p for p in profiles if p.get("linkedinUrl")}


def load_sample_engagement() -> list:
    if not os.path.exists(ENGAGEMENT_PATH):
        print("[warning] engagement.json not found, posts pipeline will be skipped")
        return []
    with open(ENGAGEMENT_PATH, "r") as f:
        return json.load(f)


SAMPLE_PROFILES = load_sample_profiles()
SAMPLE_ENGAGEMENT = load_sample_engagement()


# ── Cache builder ──────────────────────────────────────────────────────────────

def _build_response_from_cache(url: str, session_id: str, analysis: Analysis) -> LinkedInAnalyzeResponse:
    """Builds the API response from an already-cached analysis in the DB."""
    profile = SAMPLE_PROFILES.get(url)
    display = extract_display_info(profile)

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
        name=display["name"],
        headline=display["headline"],
        location=display["location"],
        profile_picture=display["profile_picture"],
        follower_count=display["follower_count"],
        insights=insights,
    )


# ── Main service functions ─────────────────────────────────────────────────────

async def get_profile_insights(linkedin_url: str, db: AsyncSession) -> LinkedInAnalyzeResponse | None:
    url = linkedin_url.rstrip("/")

    # 1. Check cache — if analysis already exists, return it immediately
    result = await db.execute(
        select(Session, Analysis)
        .join(Analysis, Analysis.session_id == Session.id)
        .where(Session.linkedin_url == url)
    )
    existing = result.first()
    if existing:
        session, analysis = existing
        print(f"[cache hit] Returning cached analysis for {url}")
        return _build_response_from_cache(url, session.id, analysis)

    # 2. Load raw profile
    profile = SAMPLE_PROFILES.get(url)
    if not profile:
        print(f"[not found] No profile found for {url}")
        return None

    # 3. Trim profile for LLM
    trimmed_profile = trim_profile_for_llm(profile)
    display = extract_display_info(profile)

    # 4. Posts pipeline — summarize if engagement data is available
    posts_summary = None
    posts_text = get_posts_for_profile(url, SAMPLE_ENGAGEMENT, max_comments=5)
    print("IMPORTANT: Raw posts text to be fed into LLM (after trimming):")
    print(posts_text)

    if posts_text and posts_text != "No posts available.":
        print(f"[posts] Found posts for {url}, running summarization...")
        posts_summary = await summarize_posts(posts_text)
        print(f"[posts] Summary generated ({len(posts_summary)} chars)")
    else:
        print(f"[posts] No posts found for {url}, skipping summarization")

    # 5. Generate insights
    # If we have posts summary → use two-stage pipeline (richer insights)
    # If no posts → fall back to profile-only analysis
    if posts_summary:
        print(f"[insights] Running two-stage pipeline (profile + posts)")
        insights = await generate_insights(trimmed_profile, posts_summary)
    else:
        print(f"[insights] Running profile-only analysis (no posts data)")
        insights = await analyze_profile(trimmed_profile)

    # 6. Persist session
    session = Session(id=str(uuid.uuid4()), linkedin_url=url)
    db.add(session)
    await db.flush()  # need session.id before creating analysis

    # 7. Persist analysis
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
        posts_summary=posts_summary,  # None if no posts, string if available
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
    last_5 = messages_result.scalars().all()[::-1]  # reverse to chronological order

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
    #print(f"[chat] AI reply: '{reply[:80]}...'")

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