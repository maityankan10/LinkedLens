from fastapi import APIRouter, HTTPException, Depends, Request, BackgroundTasks
from app.schemas.linkedin import LinkedInAnalyzeRequest, LinkedInAnalyzeResponse, ChatRequest, ChatResponse, FeedbackRequest
from app.services.linkedin import create_analysis_session, get_session_status, chat_with_profile, run_analysis_background
from app.core.database import AsyncSession, get_db
from app.core.limiter import limiter
from app.models.feedback import Feedback
import uuid

router = APIRouter()


@router.post("/analyze", response_model=LinkedInAnalyzeResponse)
@limiter.limit("5/minute")
async def analyze_linkedin_profile(
    request: Request,
    body: LinkedInAnalyzeRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    result = await create_analysis_session(body.linkedin_url, db)
    if result.status == "pending" and not result.name:
        # Freshly created session — kick off background analysis
        background_tasks.add_task(run_analysis_background, result.session_id, body.linkedin_url.rstrip("/"))
    return result


@router.get("/status/{session_id}", response_model=LinkedInAnalyzeResponse)
async def get_status(session_id: str, db: AsyncSession = Depends(get_db)):
    result = await get_session_status(session_id, db)
    if not result:
        raise HTTPException(status_code=404, detail="Session not found")
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
