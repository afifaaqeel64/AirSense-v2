"""Unit and integration tests for AirSense Daily Telemetry Email Automation.

Verifies:
1. Recipient normalization and credential masking.
2. Responsive HTML and plain-text email rendering with KPI metrics and tier breakdown.
3. Standard SMTP and SMTP_SSL transmission with multipart MIME and attachments.
4. Robust error handling for SMTP authentication failures and network timeouts.
5. Dual dispatch integration (Telegram + Email) in generate_daily_backup_csv.py.
6. Telegram interactive router webhook and on-demand email trigger endpoints.
"""

import os
import io
import pytest
from pathlib import Path
from datetime import datetime, date, timezone
from unittest.mock import patch, MagicMock
from httpx import AsyncClient, ASGITransport
import smtplib

from apps.api.main import app
from services.notification.email_dispatcher import (
    parse_email_recipients,
    mask_email_secret,
    render_backup_email_text,
    render_backup_email_html,
    send_daily_backup_email
)
from scripts.generate_daily_backup_csv import (
    generate_daily_backup,
    async_generate_daily_backup
)


def test_parse_email_recipients():
    """Verifies normalization of single, comma-separated, semicolon-separated, and list inputs."""
    # 1. Single email string
    assert parse_email_recipients("lead@airsense.pk") == ["lead@airsense.pk"]

    # 2. Comma-separated string with whitespace and quotes
    raw_comma = ' "admin@airsense.pk" , user1@campus.edu.pk, user2@domain.com '
    assert parse_email_recipients(raw_comma) == [
        "admin@airsense.pk",
        "user1@campus.edu.pk",
        "user2@domain.com"
    ]

    # 3. Semicolon-separated string
    raw_semi = "alert1@test.com; alert2@test.com"
    assert parse_email_recipients(raw_semi) == ["alert1@test.com", "alert2@test.com"]

    # 4. List input
    assert parse_email_recipients(["a@b.com", "c@d.org"]) == ["a@b.com", "c@d.org"]

    # 5. Invalid, empty, or malformed entries filtered out
    assert parse_email_recipients("invalid-email, , good@domain.com, @bad.com") == ["good@domain.com"]
    assert parse_email_recipients("") == []
    assert parse_email_recipients(None) == []


def test_mask_email_secret():
    """Verifies credential masking preserves first/last characters while redacting sensitive secret bodies."""
    assert mask_email_secret("mypassword12345") == "myp...345"
    assert mask_email_secret("secret") == "****"
    assert mask_email_secret("") == "<empty>"
    assert mask_email_secret(None) == "<empty>"


def test_render_backup_email_text_and_html():
    """Verifies email template rendering contains all key KPI observations, tiers, and dashboard URLs."""
    summary_data = {
        "avg_pm25": 14.5,
        "min_pm25": 8.0,
        "max_pm25": 28.0,
        "avg_temp": 30.2,
        "avg_hum": 64.0,
        "total_records": 16528,
        "tier_counts": {
            "tier1": 16528,
            "tier2": 24,
            "tier3": 16528,
            "valid_tier3": 15890
        }
    }
    target_date = "2026-09-12"

    # Plain text check
    text = render_backup_email_text(summary_data, target_date)
    assert "2026-09-12" in text
    assert "16,528" in text
    assert "14.5" in text
    assert "30.2" in text
    assert "Tier 1" in text
    assert "Tier 2" in text
    assert "Tier 3" in text
    assert "tier3_ml_cumulative_validated_2026_09_12.csv" in text
    assert "https://airsense-team.vercel.app" in text

    # HTML check
    html = render_backup_email_html(summary_data, target_date)
    assert "2026-09-12 (PKT / UTC+5)" in html
    assert "14.5" in html
    assert "30.2°C" in html
    assert "64%" in html
    assert "16,528" in html
    assert "Tier 1" in html
    assert "Tier 2" in html
    assert "Tier 3 ★" in html
    assert "tier3_ml_cumulative_validated_2026_09_12.csv" in html
    assert "airsense_tiered_daily_2026_09_12.zip" in html
    assert "https://airsense-team.vercel.app" in html


def test_send_daily_backup_email_standard_smtp(tmp_path):
    """Verifies full MIME email message creation, attachment encoding, and SMTP transmission."""
    csv_file = tmp_path / "tier3_test.csv"
    csv_file.write_text("pm1,pm2_5,temperature_c\n10,15,31\n", encoding="utf-8")

    zip_file = tmp_path / "backup_test.zip"
    zip_file.write_bytes(b"PK\x03\x04fake_zip_binary_data")

    summary_data = {
        "avg_pm25": 15.0,
        "min_pm25": 10.0,
        "max_pm25": 20.0,
        "avg_temp": 31.0,
        "avg_hum": 60.0,
        "total_records": 100
    }

    with patch("smtplib.SMTP") as mock_smtp_cls:
        mock_server = MagicMock()
        mock_smtp_cls.return_value = mock_server

        sent = send_daily_backup_email(
            target_date="2026-09-12",
            summary_data=summary_data,
            attachments=[csv_file, zip_file],
            to_emails="recipient@airsense.pk, team@airsense.pk",
            smtp_host="smtp.gmail.com",
            smtp_port=587,
            smtp_user="airsense.pakistan@gmail.com",
            smtp_password="abcd-efgh-ijkl-mnop",
            use_tls=True
        )

        assert sent is True
        mock_smtp_cls.assert_called_once_with("smtp.gmail.com", 587, timeout=30.0)
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with("airsense.pakistan@gmail.com", "abcd-efgh-ijkl-mnop")
        mock_server.send_message.assert_called_once()
        mock_server.quit.assert_called_once()

        # Inspect sent EmailMessage
        msg = mock_server.send_message.call_args[0][0]
        assert "2026-09-12 (PKT)" in msg["Subject"]
        assert "airsense.pakistan@gmail.com" in msg["From"]
        assert "recipient@airsense.pk, team@airsense.pk" in msg["To"]

        # Verify attachments were added
        att_filenames = [part.get_filename() for part in msg.iter_attachments()]
        assert "tier3_test.csv" in att_filenames
        assert "backup_test.zip" in att_filenames


def test_send_daily_backup_email_port_465_ssl(tmp_path):
    """Verifies that port 465 engages smtplib.SMTP_SSL directly."""
    summary_data = {"avg_pm25": 12.0, "avg_temp": 29.0, "avg_hum": 55.0, "total_records": 50}

    with patch("smtplib.SMTP_SSL") as mock_ssl_cls:
        mock_server = MagicMock()
        mock_ssl_cls.return_value = mock_server

        sent = send_daily_backup_email(
            target_date="2026-09-12",
            summary_data=summary_data,
            to_emails="user@example.com",
            smtp_host="smtp.gmail.com",
            smtp_port=465,
            smtp_user="test@gmail.com",
            smtp_password="password123"
        )

        assert sent is True
        mock_ssl_cls.assert_called_once_with("smtp.gmail.com", 465, timeout=30.0)
        mock_server.login.assert_called_once_with("test@gmail.com", "password123")
        mock_server.send_message.assert_called_once()


def test_send_daily_backup_email_auth_failure_handled_gracefully():
    """Verifies that an SMTP authentication error is caught and returns False without raising exceptions."""
    summary_data = {"avg_pm25": 12.0, "total_records": 50}

    with patch("smtplib.SMTP") as mock_smtp_cls:
        mock_server = MagicMock()
        mock_server.login.side_effect = smtplib.SMTPAuthenticationError(535, b"Bad credentials")
        mock_smtp_cls.return_value = mock_server

        sent = send_daily_backup_email(
            target_date="2026-09-12",
            summary_data=summary_data,
            to_emails="user@example.com",
            smtp_user="test@gmail.com",
            smtp_password="wrong_password"
        )

        assert sent is False


def test_send_daily_backup_email_missing_credentials_skipped():
    """Verifies that missing credentials or recipients return False and skip dispatch gracefully."""
    # No credentials
    with patch.dict(os.environ, {}, clear=True):
        assert send_daily_backup_email(
            target_date="2026-09-12",
            summary_data={},
            to_emails="user@example.com",
            smtp_user="",
            smtp_password=""
        ) is False

        # Credentials present but no recipient
        assert send_daily_backup_email(
            target_date="2026-09-12",
            summary_data={},
            to_emails="",
            smtp_user="user@gmail.com",
            smtp_password="password"
        ) is False


def test_backup_script_dual_dispatch_telegram_and_email(tmp_path):
    """Verifies that generate_daily_backup triggers both Telegram and Email dispatches concurrently."""
    target_date = date(2026, 9, 10)

    with patch("scripts.generate_daily_backup_csv.send_telegram_document", return_value=True) as mock_tg:
        with patch("scripts.generate_daily_backup_csv.send_daily_backup_email", return_value=True) as mock_email:
            with patch.dict(os.environ, {
                "TELEGRAM_BOT_TOKEN": "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11",
                "TELEGRAM_CHAT_ID": "987654321",
                "SMTP_USER": "test@gmail.com",
                "SMTP_PASSWORD": "app_password",
                "EMAIL_TO": "lead@airsense.pk"
            }):
                res = generate_daily_backup(
                    target_date=target_date,
                    output_dir=tmp_path,
                    send_telegram=True,
                    send_email=True
                )

                assert res["status"] == "success"
                assert res["telegram_sent"] is True
                assert res["email_sent"] is True
                assert res["email_recipients"] == ["lead@airsense.pk"]
                mock_tg.assert_called_once()
                mock_email.assert_called_once()


def test_backup_script_no_email_flag_skips_dispatch(tmp_path):
    """Verifies that passing send_email=False suppresses email transmission."""
    target_date = date(2026, 9, 10)

    with patch("scripts.generate_daily_backup_csv.send_daily_backup_email") as mock_email:
        res = generate_daily_backup(
            target_date=target_date,
            output_dir=tmp_path,
            send_telegram=False,
            send_email=False,
            email_to="recipient@test.com"
        )

        assert res["status"] == "success"
        assert res["email_sent"] is False
        mock_email.assert_not_called()


@pytest.mark.asyncio
async def test_telegram_send_email_now_api_endpoint():
    """Verifies POST /api/v1/telegram/send-email-now triggers generation and returns email status."""
    with patch("scripts.generate_daily_backup_csv.send_daily_backup_email", return_value=True):
        with patch("scripts.generate_daily_backup_csv.send_telegram_document", return_value=True):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                res = await client.post(
                    "/api/v1/telegram/send-email-now",
                    json={
                        "date_str": "2026-09-12",
                        "email_to": "team@airsense.pk",
                        "send_telegram": False
                    }
                )

                assert res.status_code == 200
                data = res.json()
                assert data["status"] == "success"
                assert data["target_date"] == "2026-09-12"
                assert data["email_sent"] is True
                assert data["email_recipients"] == ["team@airsense.pk"]


@pytest.mark.asyncio
async def test_telegram_webhook_commands():
    """Verifies that /start, /status, and /email commands sent to Telegram webhook return 200 OK."""
    with patch("apps.api.routers.telegram_router.send_telegram_text", return_value=True) as mock_send:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # 1. /start command
            payload_start = {
                "update_id": 10001,
                "message": {
                    "message_id": 1,
                    "chat": {"id": 123456789},
                    "text": "/start"
                }
            }
            res1 = await client.post("/api/v1/telegram/webhook", json=payload_start)
            assert res1.status_code == 200
            assert res1.json()["ok"] is True
            assert mock_send.call_count >= 1

            # 2. /status command
            payload_status = {
                "update_id": 10002,
                "message": {
                    "message_id": 2,
                    "chat": {"id": 123456789},
                    "text": "/status"
                }
            }
            res2 = await client.post("/api/v1/telegram/webhook", json=payload_status)
            assert res2.status_code == 200
            assert res2.json()["ok"] is True

            # 3. /email command with date parameter
            payload_email = {
                "update_id": 10003,
                "message": {
                    "message_id": 3,
                    "chat": {"id": 123456789},
                    "text": "/email 2026-09-12"
                }
            }
            res3 = await client.post("/api/v1/telegram/webhook", json=payload_email)
            assert res3.status_code == 200
            assert res3.json()["ok"] is True
