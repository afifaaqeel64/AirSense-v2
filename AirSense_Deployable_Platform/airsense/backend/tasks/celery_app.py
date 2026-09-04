"""Celery application configuration."""
from celery import Celery
from celery.schedules import crontab
from app.core.config import settings

app = Celery(
    "airsense",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["tasks.data_fetchers", "tasks.ml_pipeline"],
)

app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Karachi",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    result_expires=3600,
    beat_schedule={
        # Real-time feeds — every 30 minutes
        "fetch-waqi-lahore":   {"task": "tasks.data_fetchers.fetch_waqi_lahore",   "schedule": 1800},
        "fetch-openaq-lahore": {"task": "tasks.data_fetchers.fetch_openaq_lahore", "schedule": 1800},
        "fetch-iqair-lahore":  {"task": "tasks.data_fetchers.fetch_iqair_lahore",  "schedule": 1800},
        "fetch-owm-lahore":    {"task": "tasks.data_fetchers.fetch_owm_lahore",    "schedule": 3600},
        # Satellite — daily 6 AM PKT
        "fetch-sentinel5p":    {"task": "tasks.data_fetchers.fetch_sentinel5p",    "schedule": crontab(hour=6, minute=0)},
        "fetch-nasa-firms":    {"task": "tasks.data_fetchers.fetch_nasa_firms",    "schedule": crontab(hour=6, minute=30)},
        # Retrain check — every 6 hours
        "check-retrain":       {"task": "tasks.data_fetchers.check_and_trigger_retraining", "schedule": crontab(hour="*/6")},
        # Alert check — every 15 minutes
        "check-alerts":        {"task": "tasks.data_fetchers.run_alert_checks",    "schedule": 900},
    },
)
