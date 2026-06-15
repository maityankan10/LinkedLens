from fastapi import APIRouter, HTTPException, Depends
from app.schemas.linkedin import LinkedInAnalyzeRequest, LinkedInAnalyzeResponse, ChatRequest, ChatResponse
from app.services.linkedin import get_profile_insights, chat_with_profile
from app.core.database import AsyncSession, get_db
router = APIRouter()


# service returns LinkedInAnalyzeResponse object
# → FastAPI route receives it
# → FastAPI serializes to JSON
# → client gets JSON response
@router.post("/analyze", response_model=LinkedInAnalyzeResponse)
async def analyze_linkedin_profile(request: LinkedInAnalyzeRequest, db: AsyncSession = Depends(get_db)):
    result = await get_profile_insights(request.linkedin_url, db)
    if not result:
        raise HTTPException(status_code=404, detail="Profile not found in sample data")
    return result

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, db: AsyncSession = Depends(get_db)):
    reply = await chat_with_profile(request.session_id, request.message, db)
    if not reply:
        raise HTTPException(status_code=404, detail="Session not found")
    return ChatResponse(reply=reply)