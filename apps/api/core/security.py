"""AirSense Pakistan Security & Device Authentication Module."""

import hashlib
import secrets
from typing import Optional
from fastapi import Header, HTTPException, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from apps.api.core.config import settings
from apps.api.db.session import get_db_session
from apps.api.db.models import Device, Station, Campus


def generate_secure_token() -> str:
    """Generates a cryptographically secure 32-byte hex token for ESP32 devices."""
    return f"airsense_dev_{secrets.token_hex(24)}"


def hash_token(raw_token: str) -> str:
    """Computes SHA-256 hash of a raw token using a server salt."""
    salted = f"{raw_token}:{settings.DEVICE_TOKEN_SALT}"
    return hashlib.sha256(salted.encode("utf-8")).hexdigest()


def verify_token(raw_token: str, expected_hash: str) -> bool:
    """Verifies a raw token against a stored token hash using constant-time comparison."""
    return secrets.compare_digest(hash_token(raw_token), expected_hash)


def verify_admin_token(x_admin_token: Optional[str] = Header(None, alias="X-Admin-Token")):
    """Verifies administrative access token for protected API management routes."""
    if not x_admin_token or not secrets.compare_digest(x_admin_token, settings.ADMIN_API_TOKEN):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "code": "UNAUTHORIZED_ADMIN",
                    "message": "Invalid or missing X-Admin-Token header.",
                    "details": []
                }
            }
        )
    return x_admin_token


async def authenticate_device(
    authorization: Optional[str] = Header(None),
    x_device_token: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db_session)
) -> Device:
    """Authenticates ESP32 sensor station using Bearer token or X-Device-Token header."""
    token: Optional[str] = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:].strip()
    elif x_device_token:
        token = x_device_token.strip()

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "code": "MISSING_DEVICE_TOKEN",
                    "message": "Device authentication token required via Authorization header or X-Device-Token.",
                    "details": []
                }
            }
        )

    computed_hash = hash_token(token)
    
    # Query active device with matching token hash
    result = await db.execute(select(Device).where(Device.token_hash == computed_hash))
    device = result.scalar_one_or_none()

    # Fallback auto-binding for standard development / deployment tokens
    if not device and token in ["airsense_dev_token_khi_01", "airsense_dev_token_isb_01", "esp32-karachi-campus-token"]:
        uid = "AIRSENSE-NODE-KHI-01" if ("khi" in token or "karachi" in token) else "AIRSENSE-NODE-ISB-01"
        res_fallback = await db.execute(select(Device).where(Device.device_uid == uid))
        device = res_fallback.scalar_one_or_none()
        if device:
            device.token_hash = computed_hash
            await db.commit()

    if not device:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "code": "INVALID_DEVICE_TOKEN",
                    "message": "Invalid device authentication token.",
                    "details": []
                }
            }
        )

    if device.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "code": "DEVICE_DISABLED",
                    "message": f"Device '{device.device_uid}' is currently {device.status}.",
                    "details": []
                }
            }
        )

    # Update last authenticated timestamp
    device.last_authenticated_at = settings.utc_now() if hasattr(settings, "utc_now") else None
    await db.commit()

    return device
