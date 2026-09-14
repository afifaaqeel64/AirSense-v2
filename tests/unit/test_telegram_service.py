"""AirSense Pakistan - Telegram Service and Smog Early Warning Unit Tests."""

import os
import io
import time
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from apps.api.main import app
from services.notifications.telegram_service import (
    normalize_telegram_bot_token,
    normalize_telegram_chat_id,
    mask_secret,
    format_smog_alert_text,
    send_telegram_message,
    send_telegram_document,
    send_smog_alert,
    TelegramNotificationManager,
    get_telegram_manager
)
from scripts.generate_daily_backup_csv import (
    sanitize_csv_cell,
    generate_daily_backup
)

client = TestClient(app)


def test_telegram_token_normalization():
    """Verifies that various formats of Telegram bot tokens are cleanly normalized."""
    expected = "712345678:ABCDEF1234567890abcdef1234567890"

    samples = [
        "712345678:ABCDEF1234567890abcdef1234567890",
        "  712345678:ABCDEF1234567890abcdef1234567890  ",
        '"712345678:ABCDEF1234567890abcdef1234567890"',
        "'712345678:ABCDEF1234567890abcdef1234567890'",
        "bot712345678:ABCDEF1234567890abcdef1234567890",
        "https://api.telegram.org/bot712345678:ABCDEF1234567890abcdef1234567890",
        "https://api.telegram.org/bot712345678:ABCDEF1234567890abcdef1234567890/getMe",
        "https://api.telegram.org/bot712345678:ABCDEF1234567890abcdef1234567890/sendDocument",
        "api.telegram.org/bot712345678:ABCDEF1234567890abcdef1234567890/sendMessage"
    ]

    for s in samples:
        assert normalize_telegram_bot_token(s) == expected, f"Failed for token string: {s}"

    assert normalize_telegram_bot_token("") == ""
    assert normalize_telegram_bot_token(None) == ""


def test_telegram_chat_id_normalization():
    """Verifies chat ID normalization including channels and groups."""
    assert normalize_telegram_chat_id(" 123456789 ") == "123456789"
    assert normalize_telegram_chat_id('"-1001234567890"') == "-1001234567890"
    assert normalize_telegram_chat_id("@airsense_channel") == "@airsense_channel"
    assert normalize_telegram_chat_id("") == ""
    assert normalize_telegram_chat_id(None) == ""


def test_mask_secret():
    """Verifies secret masking helper."""
    assert mask_secret("1234567890abcdef") == "1234...cdef"
    assert mask_secret("short") == "****"
    assert mask_secret("") == "<empty>"


def test_format_smog_alert_text():
    """Verifies formatted alert text contains key station metrics and warning tiers."""
    msg = format_smog_alert_text(
        station_code="BIC-KHI-ROOF-01",
        campus_code="KARACHI",
        pm25=185.4,
        pm10=290.0,
        temp_c=28.5,
        hum_pct=65.0,
        aqi=235,
        severity="HAZARDOUS"
    )

    assert "AIRSENSE PAKISTAN — SMOG EARLY WARNING ALERT" in msg
    assert "BIC-KHI-ROOF-01" in msg
    assert "185.4 µg/m³" in msg
    assert "290.0 µg/m³" in msg
    assert "28.5°C" in msg
    assert "HAZARDOUS" in msg


def test_send_telegram_message_mock():
    """Verifies send_telegram_message with mocked HTTP responses."""
    fake_token = "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
    fake_chat = "987654321"

    with patch("httpx.post") as mock_post:
        # Success 200
        mock_post.return_value = MagicMock(status_code=200, text='{"ok":true}')
        success = send_telegram_message(fake_token, fake_chat, "Test message")
        assert success is True

        # Error 400
        mock_post.return_value = MagicMock(status_code=400, text='{"error":"chat not found"}')
        fail_400 = send_telegram_message(fake_token, fake_chat, "Test message")
        assert fail_400 is False

    # Empty token fails early
    assert send_telegram_message("", fake_chat, "Test") is False


def test_send_telegram_document_mock(tmp_path):
    """Verifies send_telegram_document uploads file with caption."""
    fake_token = "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
    fake_chat = "987654321"
    test_csv = tmp_path / "test_backup.csv"
    test_csv.write_text("seq,pm25\n1,25.4\n", encoding="utf-8")

    with patch("httpx.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=200, text='{"ok":true}')
        success = send_telegram_document(fake_token, fake_chat, test_csv, "Daily Backup")
        assert success is True


def test_telegram_notification_manager_cooldown_and_threshold():
    """Verifies manager evaluates PM2.5 threshold and enforces 15-minute cooldown."""
    mgr = TelegramNotificationManager(cooldown_seconds=60)
    fake_token = "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
    fake_chat = "987654321"

    payload_normal = {"station_code": "ST-01", "pm2_5": 35.0}
    payload_hazardous = {"station_code": "ST-01", "pm2_5": 185.0}

    with patch("services.notifications.telegram_service.send_telegram_message", return_value=True):
        # 1. Under threshold -> not triggered
        r1 = mgr.evaluate_and_dispatch_smog_alert(payload_normal, bot_token=fake_token, chat_id=fake_chat, threshold_pm25=150.0)
        assert r1["triggered"] is False
        assert r1["dispatched"] is False

        # 2. Over threshold -> triggered & dispatched
        r2 = mgr.evaluate_and_dispatch_smog_alert(payload_hazardous, bot_token=fake_token, chat_id=fake_chat, threshold_pm25=150.0)
        assert r2["triggered"] is True
        assert r2["dispatched"] is True

        # 3. Immediately again -> suppressed by cooldown
        r3 = mgr.evaluate_and_dispatch_smog_alert(payload_hazardous, bot_token=fake_token, chat_id=fake_chat, threshold_pm25=150.0)
        assert r3["triggered"] is True
        assert r3["dispatched"] is False
        assert "cooldown" in r3["reason"]

        # 4. Forced dispatch bypasses cooldown
        r4 = mgr.evaluate_and_dispatch_smog_alert(payload_hazardous, bot_token=fake_token, chat_id=fake_chat, threshold_pm25=150.0, force=True)
        assert r4["triggered"] is True
        assert r4["dispatched"] is True


def test_fastapi_telegram_status_endpoint():
    """Verifies GET /api/v1/hardware/notifications/telegram/status."""
    res = client.get("/api/v1/hardware/notifications/telegram/status")
    assert res.status_code == 200
    data = res.json()
    assert "configured" in data
    assert "masked_token" in data
    assert "cooldown_seconds" in data


def test_fastapi_telegram_test_alert_endpoint():
    """Verifies POST /api/v1/hardware/notifications/telegram/test-alert with mocked Telegram API."""
    with patch("services.notifications.telegram_service.send_telegram_message", return_value=True):
        res = client.post(
            "/api/v1/hardware/notifications/telegram/test-alert",
            json={
                "bot_token": "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11",
                "chat_id": "987654321",
                "pm2_5": 195.0,
                "severity": "HAZARDOUS SMOG WARNING"
            }
        )
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "success"
        assert "Telegram test alert delivered successfully" in data["message"]


def test_daily_backup_csv_generation_and_telegram(tmp_path):
    """Verifies generate_daily_backup CSV export logic with mocked Telegram dispatch."""
    fake_token = "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
    fake_chat = "987654321"

    with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": fake_token, "TELEGRAM_CHAT_ID": fake_chat}), \
         patch("services.notifications.telegram_service.send_telegram_document", return_value=True):
        res = generate_daily_backup(output_dir=tmp_path, send_telegram=True)
        assert res["status"] == "success"
        assert "csv_path" in res
        csv_file = Path(res["csv_path"])
        assert csv_file.exists()
        content = csv_file.read_text(encoding="utf-8")
        assert "reading_id" in content
        assert "pm2_5" in content
