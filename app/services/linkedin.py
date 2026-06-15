import json
import os
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.schemas.linkedin import LinkedInAnalyzeResponse
from app.services.ai import analyze_profile, chat_with_ai
from app.models.session import Session
from app.models.analysis import Analysis
from app.models.chat_message import ChatMessage

SAMPLE_DATA_PATH = os.path.join(os.path.dirname(__file__), "../../sample_data/profiles.json")

def load_sample_profiles() -> dict:
    with open(SAMPLE_DATA_PATH, "r") as f:
        profiles = json.load(f)
    return {p["linkedinUrl"]: p for p in profiles if p.get("linkedinUrl")}

SAMPLE_PROFILES = load_sample_profiles()

def _build_response_from_cache(url: str, session_id: str, analysis: Analysis) -> LinkedInAnalyzeResponse:
    profile = SAMPLE_PROFILES.get(url)

    from app.schemas.linkedin import LinkedInInsights
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
        name=f"{profile.get('firstName', '')} {profile.get('lastName', '')}".strip(),
        headline=profile.get("headline", ""),
        location=profile.get("location", {}).get("linkedinText"),
        profile_picture=profile.get("photo"),
        follower_count=profile.get("followerCount", 0),
        insights=insights,
    )

async def get_profile_insights(linkedin_url: str, db: AsyncSession) -> LinkedInAnalyzeResponse | None:
    url = linkedin_url.rstrip("/")
    
    result = await db.execute(
        select(Session, Analysis)
        .join(Analysis, Analysis.session_id == Session.id)
        .where(Session.linkedin_url == url)
    )
    existing = result.first()

    if existing:
        session, analysis = existing
        return _build_response_from_cache(url, session.id, analysis)
    
    profile = SAMPLE_PROFILES.get(url)
    if not profile:
        return None

    insights = await analyze_profile(profile)

    # Create session
    session = Session(id=str(uuid.uuid4()), linkedin_url=url)
    db.add(session)
    await db.flush()  # get session.id before creating analysis

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
    )
    db.add(analysis)
    await db.commit()

    return LinkedInAnalyzeResponse(
        session_id=session.id,
        name=f"{profile.get('firstName', '')} {profile.get('lastName', '')}".strip(),
        headline=profile.get("headline", ""),
        location=profile.get("location", {}).get("linkedinText"),
        profile_picture=profile.get("photo"),
        follower_count=profile.get("followerCount", 0),
        insights=insights,
    )

async def chat_with_profile(session_id: str, message: str, db: AsyncSession) -> str | None:
    # Load session + analysis
    result = await db.execute(
        select(Session, Analysis)
        .join(Analysis, Analysis.session_id == Session.id)
        .where(Session.id == session_id)
    )
    existing = result.first()
    if not existing:
        return None

    session, analysis = existing

    # Fetch last 5 messages
    messages_result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.desc())
        .limit(5)
    )
    last_5 = messages_result.scalars().all()[::-1]  # reverse to chronological order

    # Save user message
    user_msg = ChatMessage(
        id=str(uuid.uuid4()),
        session_id=session_id,
        role="user",
        content=message,
    )
    print(f"Saving user message: '{message}'")  
    db.add(user_msg)

    # Get AI reply
    reply = await chat_with_ai(analysis, last_5, message)
    print(f"AI reply: '{reply}'") 
    # Save assistant message
    assistant_msg = ChatMessage(
        id=str(uuid.uuid4()),
        session_id=session_id,
        role="assistant",
        content=reply,
    )
    db.add(assistant_msg)
    await db.commit()

    return reply


