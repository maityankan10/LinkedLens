from fastapi import APIRouter, HTTPException, Depends, Request
from app.schemas.linkedin import LinkedInAnalyzeRequest, LinkedInAnalyzeResponse, ChatRequest, ChatResponse, FeedbackRequest
from app.services.linkedin import get_profile_insights, chat_with_profile
from app.core.database import AsyncSession, get_db
from app.core.limiter import limiter
from app.models.feedback import Feedback
import uuid

router = APIRouter()


@router.post("/analyze", response_model=LinkedInAnalyzeResponse)
@limiter.limit("5/minute")
async def analyze_linkedin_profile(request: Request, body: LinkedInAnalyzeRequest, db: AsyncSession = Depends(get_db)):
    result = await get_profile_insights(body.linkedin_url, db)
    if not result:
        raise HTTPException(status_code=404, detail="Profile not found in sample data")
    return result


@router.post("/chat", response_model=ChatResponse)
@limiter.limit("30/minute")
async def chat(request: Request, body: ChatRequest, db: AsyncSession = Depends(get_db)):
    reply = await chat_with_profile(body.session_id, body.message, db)
    if not reply:
        raise HTTPException(status_code=404, detail="Session not found")
    return ChatResponse(reply=reply)


@router.post("/feedback", status_code=201)
async def submit_feedback(body: FeedbackRequest, db: AsyncSession = Depends(get_db)):
    feedback = Feedback(
        id=str(uuid.uuid4()),
        session_id=body.session_id,
        helpful=body.helpful,
        comment=body.comment,
    )
    db.add(feedback)
    await db.commit()
    return {"status": "ok"}
