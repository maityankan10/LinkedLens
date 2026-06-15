import json
import re
from app.schemas.linkedin import LinkedInInsights
from openai import AsyncOpenAI
from app.core.config import get_settings
from app.models.analysis import Analysis
from app.models.chat_message import ChatMessage
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

def build_chat_system_prompt(analysis: Analysis) -> str:
    return f"""You are a LinkedIn growth coach helping a professional improve their LinkedIn presence and personal brand.

    You have already analyzed their LinkedIn profile. Here is the analysis:

    Profile Summary: {analysis.profile_summary}

    Strengths:
    {chr(10).join(f"- {s}" for s in json.loads(analysis.strengths or "[]"))}

    Areas for Improvement:
    {chr(10).join(f"- {s}" for s in json.loads(analysis.improvements or "[]"))}

    Content Ideas:
    {chr(10).join(f"- {s}" for s in json.loads(analysis.content_ideas or "[]"))}

    Recommended Topics:
    {chr(10).join(f"- {s}" for s in json.loads(analysis.recommended_topics or "[]"))}

    Profile Score: {analysis.profile_score}/100

    Answer the user's questions based on this profile context. Be specific, actionable, and encouraging.
    Keep responses concise and to the point."""

def clean_json(raw: str) -> str:
    # Strip markdown code fences
    raw = re.sub(r"```json|```", "", raw).strip()
    # Extract first JSON object if there's extra text around it
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        return match.group()
    return raw

async def analyze_profile(profile: dict) -> LinkedInInsights:
    prompt = build_prompt(profile)

    response = await client.chat.completions.create(
        model="llama3.2",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1024,
    )

    raw = response.choices[0].message.content
    print(f"LLM raw response: {raw}")  # helpful for debugging

    try:
        cleaned = clean_json(raw)
        data = json.loads(cleaned)
    except json.JSONDecodeError as e:
        print(f"JSON parse error: {e}\nRaw response: {raw}")
        raise ValueError(f"LLM returned invalid JSON: {e}")

    return LinkedInInsights(**data)


async def chat_with_ai(analysis: Analysis, history: list[ChatMessage], message: str) -> str:
    system_prompt = build_chat_system_prompt(analysis)

    # Build message history for LLM
    messages = [{"role": "system", "content": system_prompt}]

    # Add last 5 messages as context
    for msg in history:
        messages.append({"role": msg.role, "content": msg.content})

    # Add current user message
    messages.append({"role": "user", "content": message})

    print(f"Sending {len(messages)} messages to LLM")
    print(f"History count (excl system + current): {len(history)}")
    for m in messages:
        print(f"  [{m['role']}]: {m['content'][:80]}...")
        
    response = await client.chat.completions.create(
        model="llama3.2",
        messages=messages,
        max_tokens=1024,
    )

    return response.choices[0].message.content.strip()