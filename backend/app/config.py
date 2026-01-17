from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://postgres:postgres@localhost:5432/pdb_insights"

    # ProductBoard API
    productboard_api_token: str = ""
    productboard_api_url: str = "https://api.productboard.com"

    # Auth
    auth_username: str = "admin"
    auth_password: str = "changeme"
    session_secret: str = "change-this-secret-key"

    # Sync
    sync_interval_hours: int = 4
    sync_enabled: bool = True

    # Exports
    export_schedule_hour: int = 2
    export_retention_days: int = 30
    export_path: str = "./exports"

    class Config:
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()
