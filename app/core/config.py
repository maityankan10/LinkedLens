from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "Social Content App"
    app_version: str = "1.0.0"
    database_url: str = ""
    debug: bool = False
    xai_api_key: str = ""
    deepseek_api_key: str = ""
    apify_api_token: str = ""
    apify_profile_actor: str = "harvestapi/linkedin-profile-scraper"
    apify_posts_actor: str = "harvestapi/linkedin-post-search"
    model_config = SettingsConfigDict(env_file=".env")

from functools import lru_cache
@lru_cache()
def get_settings():
    return Settings()
