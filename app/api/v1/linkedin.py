from fastapi import APIRouter, HTTPException
from app.schemas.linkedin import LinkedInAnalyzeRequest, LinkedInAnalyzeResponse
from app.services.linkedin import get_profile_insights

router = APIRouter()

@router.post("/analyze", response_model=LinkedInAnalyzeResponse)
async def analyze_linkedin_profile(request: LinkedInAnalyzeRequest):
    result = await get_profile_insights(request.linkedin_url)
    if not result:
        raise HTTPException(status_code=404, detail="Profile not found in sample data")
    return result