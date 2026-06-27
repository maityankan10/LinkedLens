import json
import re
import anthropic
from app.schemas.linkedin import LinkedInInsights
from app.core.config import get_settings
from app.models.analysis import Analysis
from app.models.chat_message import ChatMessage

settings = get_settings()

client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

HAIKU = "claude-haiku-4-5-20251001"
SONNET = "claude-sonnet-4-6"

# ── Helpers ────────────────────────────────────────────────────────────────────

def clean_json(raw: str) -> str:
    """Strip markdown fences and extract the first JSON object found."""
    raw = re.sub(r"```json|```", "", raw).strip()
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        return match.group()
    return raw


# ── Prompt builders ────────────────────────────────────────────────────────────

def build_profile_prompt(trimmed_profile: dict) -> str:
    experience_lines = "\n".join(
        f"- {e.get('title')} at {e.get('company')} ({e.get('duration', '')})"
        for e in trimmed_profile.get("experience", [])
    )
    education_lines = "\n".join(
        f"- {e.get('school')} — {e.get('degree') or 'N/A'} ({e.get('period', '')})"
        for e in trimmed_profile.get("education", [])
    )
    skills = ", ".join(trimmed_profile.get("skills", [])[:20])

    return f"""
You are a LinkedIn profile analyst.

Analyze the profile below and return a JSON object with these exact keys:
- profile_summary: a 2-3 sentence overview combining who this person is professionally and where they currently stand in their LinkedIn journey (career stage, presence strength, notable highlights)
- strengths: list of 3-5 concise strengths observed from the profile (e.g. "Strong technical background across multiple domains")
- areas_for_improvement: list of 3-5 specific actionable improvements for the profile (e.g. "Add a featured section to showcase key projects")
- content_ideas: list of 5 specific post ideas tailored to this person's background (e.g. "Share lessons learned from transitioning into product management")
- recommended_topics: list of 5 topics to consistently post about to build authority
- profile_score: integer from 0 to 100 rating the LinkedIn profile completeness and strength

Return ONLY valid JSON. No explanation, no markdown, no backticks.

Profile:
Name: {trimmed_profile.get('name')}
Headline: {trimmed_profile.get('headline')}
About: {trimmed_profile.get('about')}
Location: {trimmed_profile.get('location')}
Followers: {trimmed_profile.get('follower_count')}
Is Creator: {trimmed_profile.get('is_creator')}
Open to Work: {trimmed_profile.get('open_to_work')}
Top Skills: {trimmed_profile.get('top_skills')}

Experience:
{experience_lines}

Education:
{education_lines}

Skills:
{skills}
"""


def build_summarization_prompt(posts_text: str) -> str:
    return f"""You are summarizing a LinkedIn user's own posting activity to be used as context for a personalized coaching session with them.

Summarize the following posts and comments in under 1000 words, written as notes about the person's content behavior — not addressed to them directly.

Cover these points:
- Main topics and themes they post about
- Writing style and tone (formal, casual, inspirational, technical, etc.)
- Posting frequency patterns (if dates are available)
- Types of content formats used (text only, images, job postings, opinions, etc.)
- Engagement patterns (which posts get more likes/comments)
- How they interact with commenters (do they reply? how often?)
- Emotional tone of audience reactions (LIKE, EMPATHY, PRAISE, etc.)

Be concise and factual. Do not invent information not present in the posts.
Return plain text only, no JSON, no markdown headers.

Posts:
{posts_text}
"""


def build_insights_prompt(trimmed_profile: dict, posts_summary: str) -> str:
    experience_lines = "\n".join(
        f"- {e.get('title')} at {e.get('company')} ({e.get('duration', '')})"
        for e in trimmed_profile.get("experience", [])
    )
    skills = ", ".join(trimmed_profile.get("skills", [])[:20])

    return f"""You are a LinkedIn growth analyst.

Using both the profile and content activity summary below, return a JSON object with these exact keys:
- profile_summary: a 2-3 sentence overview combining who this person is professionally and where they currently stand — covering their career background, LinkedIn presence strength, and content activity highlights
- strengths: list of 3-5 concise strengths observed from the profile and content (e.g. "Consistent posting cadence with strong engagement on technical topics")
- areas_for_improvement: list of 3-5 specific actionable improvements across both profile and content strategy (e.g. "Increase comment engagement to build visibility beyond direct followers")
- content_ideas: list of 5 specific post ideas tailored to this person's background and existing style (e.g. "Share a behind-the-scenes look at a recent project milestone")
- recommended_topics: list of 5 topics to consistently post about to grow authority
- profile_score: integer from 0 to 100 rating the overall LinkedIn presence

Return ONLY valid JSON. No explanation, no markdown, no backticks.

--- PROFILE ---
Name: {trimmed_profile.get('name')}
Headline: {trimmed_profile.get('headline')}
About: {trimmed_profile.get('about')}
Location: {trimmed_profile.get('location')}
Followers: {trimmed_profile.get('follower_count')}
Is Creator: {trimmed_profile.get('is_creator')}
Top Skills: {trimmed_profile.get('top_skills')}

Experience:
{experience_lines}

Skills:
{skills}

--- CONTENT ACTIVITY ---
{posts_summary}
"""


def build_chat_system_prompt(analysis: Analysis, history: list[ChatMessage]) -> str:
    posts_section = ""
    if analysis.posts_summary:
        posts_section = f"\nContent Activity Summary:\n{analysis.posts_summary}\n"

    history_section = ""
    if history:
        lines = "\n".join(
            f"{'You' if msg.role == 'user' else 'Coach'}: {msg.content}"
            for msg in history
        )
        history_section = f"\n--- PREVIOUS CONVERSATION (for context only) ---\n{lines}\n--- END OF HISTORY ---\n"

    return f"""You are a LinkedIn growth coach having a direct conversation with the person you've already analyzed.
Always speak to them in second person — say "you" and "your", never "they" or "the user". Be warm, direct, and encouraging.

Here is what you already know about them:

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
{posts_section}{history_section}
Respond ONLY to the user's latest message below. Use the previous conversation as context to avoid repeating yourself, but do not address or summarise earlier messages."""


# ── LLM calls ──────────────────────────────────────────────────────────────────

async def analyze_profile(trimmed_profile: dict) -> LinkedInInsights:
    prompt = build_profile_prompt(trimmed_profile)

    response = await client.messages.create(
        model=SONNET,
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = response.content[0].text
    print(f"[analyze_profile] LLM raw response: {raw}")

    try:
        cleaned = clean_json(raw)
        data = json.loads(cleaned)
    except json.JSONDecodeError as e:
        print(f"[analyze_profile] JSON parse error: {e}\nRaw: {raw}")
        raise ValueError(f"LLM returned invalid JSON: {e}")

    return LinkedInInsights(**data)


async def summarize_posts(posts_text: str) -> str:
    prompt = build_summarization_prompt(posts_text)

    response = await client.messages.create(
        model=HAIKU,
        max_tokens=1200,
        messages=[{"role": "user", "content": prompt}],
    )

    summary = response.content[0].text.strip()
    print(f"[summarize_posts] Summary length: {len(summary)} chars")
    return summary


async def generate_insights(trimmed_profile: dict, posts_summary: str) -> LinkedInInsights:
    prompt = build_insights_prompt(trimmed_profile, posts_summary)

    response = await client.messages.create(
        model=SONNET,
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = response.content[0].text
    print(f"[generate_insights] LLM raw response: {raw}")

    try:
        cleaned = clean_json(raw)
        data = json.loads(cleaned)
    except json.JSONDecodeError as e:
        print(f"[generate_insights] JSON parse error: {e}\nRaw: {raw}")
        raise ValueError(f"LLM returned invalid JSON: {e}")

    return LinkedInInsights(**data)


async def chat_with_ai(analysis: Analysis, history: list[ChatMessage], message: str) -> str:
    system_prompt = build_chat_system_prompt(analysis, history)

    response = await client.messages.create(
        model=SONNET,
        max_tokens=1024,
        system=system_prompt,
        messages=[{"role": "user", "content": message}],
    )

    return response.content[0].text.strip()
