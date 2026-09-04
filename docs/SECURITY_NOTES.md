# AirSense Pakistan Security Notes

This document outlines security practices, token management, credential hygiene, and secret scanning procedures for AirSense Pakistan.

## 1. Non-Negotiable Security Rules

1. **Secrets & Environment Variables**: No production password, secret token, or private key must ever be hardcoded or committed to version control. All `.env` files must be ignored via `.gitignore`.
2. **Device Authentication**: ESP32 sensor stations authenticate using a SHA-256 hashed device token sent via HTTP headers (`X-Device-Token`). Raw tokens are never stored plain-text in the database.
3. **Secret Redaction**: Error logs, system health responses, and diagnostic CLI commands must redact credential values (`***REDACTED***`).
4. **CORS Restrictions**: Frontend CORS origins are strictly matched against configured URLs in `CORS_ORIGINS`. Wildcards (`*`) are disallowed in production mode.

## 2. Token Hashing Procedure

```python
import hashlib

def hash_device_token(raw_token: str, salt: str) -> str:
    return hashlib.sha256((raw_token + salt).encode("utf-8")).hexdigest()
```

## 3. Recommended Secret Scanning Pre-Commit Check

```bash
# Verify no .env or sensitive token exists in committed files
git diff --cached --name-only | grep -E "\.env|credentials|secret"
```

## 4. API Key Hygiene

- Third-party API keys (OpenAQ, OpenWeather, WAQI) must be loaded dynamically from environment variables.
- Tier 1 provider Open-Meteo requires no API key, minimizing credential risk during pilot deployment.
