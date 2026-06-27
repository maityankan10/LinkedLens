import json
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.schemas.linkedin import LinkedInAnalyzeResponse, LinkedInInsights
from app.services.ai import analyze_profile, summarize_posts, generate_insights, chat_with_ai
from app.services.profile_parser import trim_profile_for_llm, extract_display_info
from app.services.posts_parser import get_posts_for_profile
from app.services.apify import fetch_linkedin_profile, fetch_linkedin_posts
from app.models.session import Session
from app.models.analysis import Analysis
from app.models.chat_message import ChatMessage
from app.core.database import AsyncSessionLocal


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
        status="ready",
        name=analysis.profile_name or "",
        headline=analysis.profile_headline or "",
        location=analysis.profile_location,
        profile_picture=analysis.profile_picture,
        follower_count=analysis.follower_count or 0,
        insights=insights,
    )


# ── Background analysis task ───────────────────────────────────────────────────

async def run_analysis_background(session_id: str, url: str):
    print(f"[background] Starting analysis for session {session_id}")
    try:
        import asyncio
        profile, raw_posts = await asyncio.gather(
            fetch_linkedin_profile(url),
            fetch_linkedin_posts(url),
        )

        if not profile:
            raise ValueError(f"No profile found for {url}")

        trimmed_profile = trim_profile_for_llm(profile)
        display = extract_display_info(profile)

        posts_summary = None
        posts_text = get_posts_for_profile(url, raw_posts)
        if posts_text and posts_text != "No posts available.":
            print(f"[background] Summarizing posts for {session_id}")
            posts_summary = await summarize_posts(posts_text)

        if posts_summary:
            print(f"[background] Running two-stage pipeline for {session_id}")
            insights = await generate_insights(trimmed_profile, posts_summary)
        else:
            print(f"[background] Running profile-only analysis for {session_id}")
            insights = await analyze_profile(trimmed_profile)

        async with AsyncSessionLocal() as db:
            analysis = Analysis(
                id=str(uuid.uuid4()),
                session_id=session_id,
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
            await db.execute(
                update(Session).where(Session.id == session_id).values(status="ready")
            )
            await db.commit()
            print(f"[background] Analysis complete for session {session_id}")

    except Exception as e:
        print(f"[background error] session {session_id}: {e}")
        try:
            async with AsyncSessionLocal() as db:
                await db.execute(
                    update(Session).where(Session.id == session_id).values(status="error")
                )
                await db.commit()
        except Exception as db_err:
            print(f"[background error] failed to update status: {db_err}")


# ── Main service functions ─────────────────────────────────────────────────────

async def create_analysis_session(linkedin_url: str, db: AsyncSession) -> LinkedInAnalyzeResponse:
    url = linkedin_url.rstrip("/")

    # 1. Return cached ready session if exists
    result = await db.execute(
        select(Session, Analysis)
        .join(Analysis, Analysis.session_id == Session.id)
        .where(Session.linkedin_url == url)
        .where(Session.status == "ready")
    )
    existing = result.first()
    if existing:
        session, analysis = existing
        print(f"[cache hit] Returning cached analysis for {url}")
        return _build_response_from_cache(session.id, analysis)

    # 2. Return existing pending session if already in progress
    pending = await db.execute(
        select(Session)
        .where(Session.linkedin_url == url)
        .where(Session.status == "pending")
    )
    pending_session = pending.scalar_one_or_none()
    if pending_session:
        print(f"[pending] Analysis already in progress for {url}")
        return LinkedInAnalyzeResponse(session_id=pending_session.id, status="pending")

    # 3. Create new session immediately and return
    session_id = str(uuid.uuid4())
    session = Session(id=session_id, linkedin_url=url, status="pending")
    db.add(session)
    await db.commit()
    print(f"[new session] Created session {session_id} for {url}")

    return LinkedInAnalyzeResponse(session_id=session_id, status="pending")


async def get_session_status(session_id: str, db: AsyncSession) -> LinkedInAnalyzeResponse | None:
    result = await db.execute(
        select(Session, Analysis)
        .outerjoin(Analysis, Analysis.session_id == Session.id)
        .where(Session.id == session_id)
    )
    row = result.first()
    if not row:
        return None

    session, analysis = row

    if session.status == "ready" and analysis:
        return _build_response_from_cache(session_id, analysis)

    return LinkedInAnalyzeResponse(session_id=session_id, status=session.status)


async def chat_with_profile(session_id: str, message: str, db: AsyncSession) -> str | None:
    result = await db.execute(
        select(Session, Analysis)
        .join(Analysis, Analysis.session_id == Session.id)
        .where(Session.id == session_id)
    )
    existing = result.first()
    if not existing:
        return None

    session, analysis = existing

    messages_result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.desc())
        .limit(5)
    )
    last_5 = messages_result.scalars().all()[::-1]

    user_msg = ChatMessage(
        id=str(uuid.uuid4()),
        session_id=session_id,
        role="user",
        content=message,
    )
    db.add(user_msg)

    reply = await chat_with_ai(analysis, last_5, message)

    assistant_msg = ChatMessage(
        id=str(uuid.uuid4()),
        session_id=session_id,
        role="assistant",
        content=reply,
    )
    db.add(assistant_msg)
    await db.commit()

    return reply
