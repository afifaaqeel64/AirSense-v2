"""AirSense Pakistan Configuration Management Layer."""

import os
from pathlib import Path
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # App Information
    APP_NAME: str = "AirSense Pakistan"
    APP_VERSION: str = "0.1.0-foundation"
    AIR_SENSE_ENV: str = "development"
    AIR_SENSE_TIMEZONE: str = "Asia/Karachi"
    DEBUG: bool = True

    # Database URLs (Supports SQLite local development & Supabase PostgreSQL cloud production)
    DATABASE_URL: str = (
        "postgresql+asyncpg://postgres.vppczkvawiaptiygrqhx:7EZgyMcqYi%269qUE@aws-0-ap-northeast-2.pooler.supabase.com:5432/postgres"
        if os.getenv("VERCEL")
        else os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./data/airsense.db")
    )
    
    # Application & CORS
    BACKEND_BASE_URL: str = "http://localhost:8000"
    FRONTEND_BASE_URL: str = "http://localhost:3000"
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"

    # Security Tokens
    ADMIN_API_TOKEN: str = "change-this-admin-token-placeholder"
    DEVICE_TOKEN_SALT: str = "change-this-device-token-salt-placeholder"

    # Paths
    MODEL_ARTIFACT_PATH: str = "./data/models"
    IMPORT_PATH: str = "./data/imports"
    EXPORT_PATH: str = "./data/exports"

    # Campus Settings - Islamabad
    ISLAMABAD_CAMPUS_NAME: str = "Islamabad Campus"
    ISLAMABAD_CAMPUS_CODE: str = "ISB_CAMPUS"
    ISLAMABAD_LATITUDE: Optional[float] = None
    ISLAMABAD_LONGITUDE: Optional[float] = None
    ISLAMABAD_CONTACT_NAME: str = "Muhammad M. Qureshi"

    # Campus Settings - Karachi
    KARACHI_CAMPUS_NAME: str = "Karachi Campus"
    KARACHI_CAMPUS_CODE: str = "KHI_CAMPUS"
    KARACHI_LATITUDE: Optional[float] = None
    KARACHI_LONGITUDE: Optional[float] = None
    KARACHI_CONTACT_NAME: str = "Areesha"

    # Provider API Keys
    OPENAQ_API_KEY: str = ""
    OPENWEATHER_API_KEY: str = ""
    OPENWEATHERMAP_API_KEY: str = ""
    WEATHERAPI_KEY: str = ""
    TOMORROW_IO_KEY: str = ""
    WAQI_API_TOKEN: str = ""
    IQAIR_API_KEY: str = ""
    NASA_FIRMS_MAP_KEY: str = ""

    # Feature Flags
    EXTERNAL_SYNC_ENABLED: bool = True
    EXTERNAL_SYNC_INTERVAL_MINUTES: int = 60
    MODEL_TRAINING_ENABLED: bool = False
    ALERT_EVALUATION_ENABLED: bool = True
    DEMO_DATA_ENABLED: bool = False

    # Phase 2 Production Hardening Flags
    SECURITY_HEADERS_ENABLED: bool = True
    RATE_LIMIT_ENABLED: bool = True
    COPILOT_RATE_LIMIT_RPM: int = 30
    INGEST_RATE_LIMIT_RPM: int = 120
    BACKUP_RETENTION_COUNT: int = 14
    BACKGROUND_SCHEDULER_ENABLED: bool = True

    model_config = SettingsConfigDict(
        env_file=(
            str(Path(__file__).resolve().parent.parent.parent.parent / ".env"),
            ".env"
        ),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    def get_cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    def is_islamabad_configured(self) -> bool:
        return self.ISLAMABAD_LATITUDE is not None and self.ISLAMABAD_LONGITUDE is not None

    def is_karachi_configured(self) -> bool:
        return self.KARACHI_LATITUDE is not None and self.KARACHI_LONGITUDE is not None


settings = Settings()
