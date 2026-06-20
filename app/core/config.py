from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "Social Content App"
    app_version: str = "1.0.0"
    database_url: str = ""
    debug: bool = False
    anthropic_api_key: str = ""
    apify_profile_actor: str = "harvestapi/linkedin-profile-scraper"
    apify_posts_actor: str = "harvestapi/linkedin-post-search"
    model_config = SettingsConfigDict(env_file=".env")
    apify_api_token: str = ""

from functools import lru_cache
@lru_cache()
def get_settings():
    return Settings()
