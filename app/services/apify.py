import asyncio
from apify_client import ApifyClient
from app.core.config import get_settings


def _fetch_profile_sync(linkedin_url: str) -> dict | None:
    settings = get_settings()
    client = ApifyClient(settings.apify_api_token)

    run = client.actor(settings.apify_profile_actor).call(run_input={
        "urls": [linkedin_url],
        "profileScraperMode": "Profile details no email ($4 per 1k)",
    })
    items = list(client.dataset(run.default_dataset_id).iterate_items())
    if not items:
        return None

    url_clean = linkedin_url.rstrip("/")
    for item in items:
        if (item.get("linkedinUrl") or "").rstrip("/") == url_clean:
            return item
    return items[0]


def _fetch_posts_sync(linkedin_url: str) -> list:
    settings = get_settings()
    client = ApifyClient(settings.apify_api_token)

    run = client.actor(settings.apify_posts_actor).call(run_input={
        "authorUrls": [linkedin_url],
        "maxPosts": 30,
        "scrapeComments": True,
        "commentsPostedLimit": "year",
        "maxComments": 5,
    })
    return list(client.dataset(run.default_dataset_id).iterate_items())


async def fetch_linkedin_profile(linkedin_url: str) -> dict | None:
    return await asyncio.to_thread(_fetch_profile_sync, linkedin_url)


async def fetch_linkedin_posts(linkedin_url: str) -> list:
    return await asyncio.to_thread(_fetch_posts_sync, linkedin_url)
