from pydantic_settings import BaseSettings
from functools import lru_cache
import os

class Settings(BaseSettings):
    gemini_model: str = "gemini-2.0-flash"
    api_key: str = "dev-key"
    database_url_local: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/intel_hub"
    database_url: str = ""
    google_api_key: str = ""

    def model_post_init(self, __context):
        if not self.database_url:
            object.__setattr__(self, "database_url", self.database_url_local)
        if self.google_api_key:
            os.environ["GOOGLE_API_KEY"] = self.google_api_key

    class Config:
        env_file = ".env"
        extra = "ignore"

@lru_cache
def get_settings():
    return Settings()

settings = get_settings()
