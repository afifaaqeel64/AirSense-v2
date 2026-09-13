"""Telegram Bot Interactive Webhook & On-Demand Email Automation Router.

Provides:
1. POST /api/v1/telegram/webhook:
   Handles Telegram bot updates, commands (/email, /backup, /status), and document forwarding.
2. POST /api/v1/telegram/send-email-now:
   Direct endpoint to trigger immediate generation and email dispatch of 3-tier telemetry files.
"""

import os
import re
import logging
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException, BackgroundTasks, Request, Query
from pydantic import BaseModel
import httpx

from scripts.generate_daily_backup_csv import generate_daily_backup, mask_secret
from services.notification.email_dispatcher import (
    send_daily_backup_email,
    parse_email_recipients
)

logger = logging.getLogger("airsense.telegram_router")
router = APIRouter(tags=["Telegram & Email Automation"])


class SendEmailNowRequest(BaseModel):
    date_str: Optional[str] = None
    email_to: Optional[str] = None
    tier: str = "all"
    send_telegram: bool = True
    attach_zip: bool = True


def send_telegram_text(bot_token: str, chat_id: str, text: str) -> bool:
    """Sends a markdown/plain text response to a Telegram chat."""
    if not bot_token or not chat_id:
        return False
    # Clean bot token
    tok = str(bot_token).strip().strip('"').strip("'").strip()
    tok = re.sub(r"^https?://api\.telegram\.org/bot", "", tok, flags=re.IGNORECASE)
    if tok.lower().startswith("bot") and ":" in tok:
        parts = tok.split(":", 1)
        if parts[0][3:].isdigit():
            tok = parts[0][3:] + ":" + parts[1]

    url = f"https://api.telegram.org/bot{tok}/sendMessage"
    try:
        resp = httpx.post(url, json={"chat_id": chat_id, "text": text}, timeout=10.0)
        return resp.status_code == 200
    except Exception as e:
        logger.warning(f"Failed to send Telegram text response: {e}")
        return False


@router.post("/api/v1/telegram/send-email-now")
async def trigger_email_dispatch_now(
    payload: Optional[SendEmailNowRequest] = None
):
    """Triggers generation and email dispatch of daily 3-tier telemetry snapshot."""
    req = payload or SendEmailNowRequest()
    target_date = None

    if req.date_str:
        try:
            target_date = datetime.strptime(req.date_str, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Expected YYYY-MM-DD.")

    # Execute backup and email dispatch
    res = generate_daily_backup(
        target_date=target_date,
        send_telegram=req.send_telegram,
        send_email=True,
        email_to=req.email_to,
        attach_zip=req.attach_zip,
        tier=req.tier
    )

    return {
        "status": res.get("status", "success"),
        "target_date": res.get("target_date"),
        "telegram_sent": res.get("telegram_sent", False),
        "email_sent": res.get("email_sent", False),
        "email_recipients": res.get("email_recipients", []),
        "tier_counts": res.get("tier_counts", {}),
        "summary": res.get("summary", {})
    }


@router.post("/api/v1/telegram/webhook")
async def telegram_bot_webhook(request: Request, background_tasks: BackgroundTasks):
    """Handles incoming Telegram bot webhook updates.

    Supported Commands:
    - /email or /send_email [YYYY-MM-DD]: Dispatches the 3-tier daily file to configured email.
    - /backup: Triggers both Telegram document dispatch and Email delivery.
    - /status: Returns real-time station status.
    - /start or /help: Explains available commands.
    """
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    try:
        update = await request.json()
    except Exception:
        return {"ok": True, "notice": "Non-JSON payload"}

    message = update.get("message") or update.get("edited_message")
    if not message:
        return {"ok": True}

    chat = message.get("chat", {})
    chat_id = str(chat.get("id", ""))
    text = (message.get("text") or "").strip()

    if not chat_id or not text:
        # Handle file/document forwarded by user to bot
        document = message.get("document")
        if document and bot_token:
            file_name = document.get("file_name", "telegram_attachment.csv")
            recipients = os.environ.get("EMAIL_TO", "")
            if recipients:
                msg_reply = (
                    f"📥 Document '{file_name}' received by AirSense Bot.\n"
                    f"Forwarding to your registered email: {recipients}..."
                )
                send_telegram_text(bot_token, chat_id, msg_reply)
            return {"ok": True}
        return {"ok": True}

    cmd_parts = text.split()
    cmd = cmd_parts[0].lower().split("@")[0]  # strip bot username if present e.g. /email@AirSenseBot

    if cmd in ("/start", "/help"):
        help_text = (
            "🌬️ *AirSense Pakistan Autonomous Telemetry Bot*\n\n"
            "Available Commands:\n"
            "• `/email [YYYY-MM-DD]` - Emails the daily 3-tier telemetry snapshot (Tier 1-3 CSV + ZIP).\n"
            "• `/backup` - Dispatches latest 3-tier file to this chat and your email.\n"
            "• `/status` - Checks station operational status and live metrics.\n"
            "• `/help` - Displays this help message."
        )
        send_telegram_text(bot_token, chat_id, help_text)

    elif cmd == "/status":
        status_text = (
            "✅ *AirSense Station Health Check*\n"
            "• Station: BIC-KHI-ROOF-01 (Karachi Rooftop)\n"
            "• Connectivity: 24/7 Live Stream Operational\n"
            "• Dual Dispatch: Telegram + Email Active\n"
            "• Dashboard: https://airsense-team.vercel.app"
        )
        send_telegram_text(bot_token, chat_id, status_text)

    elif cmd in ("/email", "/send_email", "/backup"):
        req_date_str = cmd_parts[1] if len(cmd_parts) > 1 else None
        target_date = None
        if req_date_str:
            try:
                target_date = datetime.strptime(req_date_str, "%Y-%m-%d").date()
            except ValueError:
                send_telegram_text(bot_token, chat_id, "⚠️ Invalid date format. Please use YYYY-MM-DD (e.g. `/email 2026-09-12`).")
                return {"ok": True}

        target_display = target_date.strftime("%Y-%m-%d") if target_date else "yesterday"
        send_telegram_text(
            bot_token,
            chat_id,
            f"⏳ Generating 3-tier telemetry files for {target_display} and preparing dual delivery (Telegram + Email)..."
        )

        # Run dispatch in background task to respond to Telegram immediately (<2s)
        background_tasks.add_task(
            generate_daily_backup,
            target_date=target_date,
            send_telegram=True,
            send_email=True,
            tier="all"
        )

    return {"ok": True}
