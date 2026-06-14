import json
import os
from app.schemas.linkedin import LinkedInAnalyzeResponse
from app.services.ai import analyze_profile

SAMPLE_DATA_PATH = os.path.join(os.path.dirname(__file__), "../../sample_data/profiles.json")

def load_sample_profiles() -> dict:
    with open(SAMPLE_DATA_PATH, "r") as f:
        profiles = json.load(f)
    return {p["linkedinUrl"]: p for p in profiles if p.get("linkedinUrl")}

SAMPLE_PROFILES = load_sample_profiles()

async def get_profile_insights(linkedin_url: str) -> LinkedInAnalyzeResponse:
    url = linkedin_url.rstrip("/")
    
    profile = SAMPLE_PROFILES.get(url)
    if not profile:
        return None

    insights = await analyze_profile(profile)

    return LinkedInAnalyzeResponse(
        name=f"{profile.get('firstName', '')} {profile.get('lastName', '')}".strip(),
        headline=profile.get("headline", ""),
        location=profile.get("location", {}).get("linkedinText"),
        profile_picture=profile.get("photo"),
        follower_count=profile.get("followerCount", 0),
        insights=insights,
    )