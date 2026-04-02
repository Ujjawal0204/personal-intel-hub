from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    gcp_project_id: str = ""
    gcp_region: str = "us-central1"
    gemini_model: str = "gemini-2.5-flash"
    api_key: str = "dev-key"
    env: str = "local"
    database_url_local: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/intel_hub"
    database_url: str = ""
    google_api_key: str = ""

    def model_post_init(self, __context):
        if not self.database_url:
            object.__setattr__(self, "database_url", self.database_url_local)

    class Config:
        env_file = ".env"
        extra = "ignore"

@lru_cache
def get_settings():
    return Settings()

settings = get_settings()
