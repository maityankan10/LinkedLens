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
    status: str = "ready"          # "pending" | "ready" | "error"
    name: Optional[str] = None
    headline: Optional[str] = None
    location: Optional[str] = None
    profile_picture: Optional[str] = None
    follower_count: Optional[int] = None
    insights: Optional[LinkedInInsights] = None

class ChatRequest(BaseModel):
    session_id: str
    message: str

class ChatResponse(BaseModel):
    reply: str

class FeedbackRequest(BaseModel):
    session_id: str
    helpful: bool
    comment: Optional[str] = None