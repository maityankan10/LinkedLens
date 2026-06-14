import json
from app.schemas.linkedin import LinkedInInsights
from openai import AsyncOpenAI
from app.core.config import get_settings


settings = get_settings()
client = AsyncOpenAI( 
    api_key="ollama",
    base_url="http://localhost:11434/v1"
)

def build_prompt(profile: dict) -> str:
    name = f"{profile.get('firstName', '')} {profile.get('lastName', '')}"
    headline = profile.get('headline', '')
    about = profile.get('about', '')
    location = profile.get('location', {}).get('linkedinText', '')
    follower_count = profile.get('followerCount', 0)
    
    experience = []
    for exp in profile.get('experience', []):
        experience.append(f"- {exp.get('position')} at {exp.get('companyName')} ({exp.get('duration', '')})")
    
    education = []
    for edu in profile.get('profileTopEducation', []):
        education.append(f"- {edu.get('schoolName')} ({edu.get('period', '')})")

    skills = [s.get('name') for s in profile.get('skills', []) if s.get('name')]

    return f"""
You are a LinkedIn profile analyst and content strategist.

Analyze the following LinkedIn profile and return a JSON object with these exact keys:
- profile_summary: a 2-3 sentence summary of who this person is professionally
- strengths: list of 3-5 strengths based on their profile
- areas_for_improvement: list of 3-5 specific actionable improvements for their LinkedIn profile
- content_ideas: list of 5 specific post ideas tailored to their background
- recommended_topics: list of 5 topics they should consistently post about to build authority
- profile_score: integer from 0 to 100 rating their LinkedIn profile completeness and strength

Return ONLY valid JSON. No explanation, no markdown, no backticks.

Profile:
Name: {name}
Headline: {headline}
About: {about}
Location: {location}
Followers: {follower_count}

Experience:
{chr(10).join(experience)}

Education:
{chr(10).join(education)}

Skills:
{', '.join(skills[:20])}
"""

async def analyze_profile(profile: dict) -> LinkedInInsights:
    prompt = build_prompt(profile)

    response = await client.chat.completions.create(
        model="llama3.2",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1024,
    )

    raw = response.choices[0].message.content
    data = json.loads(raw)

    return LinkedInInsights(**data)