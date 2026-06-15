from pydantic import BaseModel
from typing import Optional

class LinkedInAnalyzeRequest(BaseModel):
    linkedin_url: str

class LinkedInInsights(BaseModel):
    profile_summary: str
    strengths: list[str]
    areas_for_improvement: list[str]
    content_ideas: list[str]
    recommended_topics: list[str]
    profile_score: Optional[int] = None  # 0-100

class LinkedInAnalyzeResponse(BaseModel):
    session_id: str
    name: str
    headline: str
    location: Optional[str]
    profile_picture: Optional[str]
    follower_count: int
    insights: LinkedInInsights

class ChatRequest(BaseModel):
    session_id: str
    message: str

class ChatResponse(BaseModel):
    reply: str