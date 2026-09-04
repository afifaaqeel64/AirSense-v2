"""Unit tests for AirSense configuration loading and validation."""

import pytest
from apps.api.core.config import settings


def test_config_defaults():
    assert settings.APP_NAME == "AirSense Pakistan"
    assert settings.AIR_SENSE_TIMEZONE == "Asia/Karachi"
    assert settings.ISLAMABAD_CONTACT_NAME == "Muhammad M. Qureshi"
    assert settings.KARACHI_CONTACT_NAME == "Areesha"


def test_missing_coordinates_trigger_unconfigured():
    assert settings.is_islamabad_configured() is False
    assert settings.is_karachi_configured() is False


def test_cors_origins_parsing():
    origins = settings.get_cors_origins_list()
    assert "http://localhost:3000" in origins
    assert "http://127.0.0.1:3000" in origins
