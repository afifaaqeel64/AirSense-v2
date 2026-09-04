from pydantic_settings import BaseSettings
from typing import List, Optional
from functools import lru_cache

class Settings(BaseSettings):
    # App
    APP_NAME: str = "AirSense"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    SECRET_KEY: str = "change-this-in-production-min-32-chars"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://airsense:password@timescaledb:5432/airsense"
    DATABASE_URL_SYNC: str = "postgresql://airsense:password@timescaledb:5432/airsense"
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 40

    # Redis
    REDIS_URL: str = "redis://redis:6379/0"
    CACHE_TTL_SECONDS: int = 300

    # MLflow
    MLFLOW_TRACKING_URI: str = "http://mlflow:5000"
    MLFLOW_S3_BUCKET: str = "airsense-models"

    # Data Source API Keys
    OPENAQ_API_KEY: str = ""
    WAQI_TOKEN: str = ""
    IQAIR_API_KEY: str = ""
    OWM_API_KEY: str = ""
    NASA_FIRMS_KEY: str = ""
    MAPBOX_TOKEN: str = ""

    # JWT
    JWT_SECRET: str = "change-this-jwt-secret-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 10080  # 7 days

    # Email (SMTP)
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    EMAILS_FROM: str = "alerts@airsense.pk"

    # Twilio SMS (optional)
    TWILIO_SID: str = ""
    TWILIO_TOKEN: str = ""
    TWILIO_FROM: str = ""

    # Sentry
    SENTRY_DSN: str = ""

    # CORS
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "https://airsense.pk",
        "https://www.airsense.pk",
    ]

    # ML Pipeline
    RETRAIN_THRESHOLD_RECORDS: int = 500
    RETRAIN_MAX_INTERVAL_HOURS: int = 24
    MODEL_PROMOTION_MIN_IMPROVEMENT: float = 0.01  # 1%
    FEATURE_LOOKBACK_DAYS: int = 90

    # Lahore bounding box
    LAHORE_BBOX: dict = {
        "lon_min": 73.9, "lon_max": 74.7,
        "lat_min": 31.2, "lat_max": 31.8,
        "center_lat": 31.5497, "center_lon": 74.3436
    }

    class Config:
        env_file = ".env"
        case_sensitive = True

@lru_cache()
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
