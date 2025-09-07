from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Database
    database_url: str = "sqlite+aiosqlite:///./takedown.db"
    
    # JWT
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # SLA Configuration
    sla_hours: int = 24
    
    # Redis (optional)
    redis_url: Optional[str] = None
    
    # Rate limiting
    rate_limit_per_minute: int = 10
    
    class Config:
        env_file = ".env"


settings = Settings()
