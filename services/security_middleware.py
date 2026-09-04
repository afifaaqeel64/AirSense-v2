"""AirSense Pakistan Production Security, Rate Limiting & Access Control Layer."""

import time
import logging
from collections import defaultdict
from typing import Dict, List, Tuple
from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware

from apps.api.core.config import settings

logger = logging.getLogger("airsense.security")


class SlidingWindowRateLimiter:
    """Sliding-window in-memory request rate limiter with automatic IP tracking."""

    def __init__(self):
        # Map of key -> list of timestamp floats
        self._requests: Dict[str, List[float]] = defaultdict(list)

    def is_allowed(self, key: str, max_requests: int, window_seconds: int = 60) -> Tuple[bool, int]:
        """Checks if a request under `key` is allowed within `window_seconds`.
        
        Returns (is_allowed, remaining_requests).
        """
        now = time.time()
        cutoff = now - window_seconds
        
        # Clean older timestamps
        self._requests[key] = [t for t in self._requests[key] if t > cutoff]
        current_count = len(self._requests[key])

        if current_count >= max_requests:
            return False, 0

        self._requests[key].append(now)
        return True, max(0, max_requests - (current_count + 1))


rate_limiter = SlidingWindowRateLimiter()


class ProductionSecurityMiddleware(BaseHTTPMiddleware):
    """Applies OWASP-compliant security headers and request metrics to all HTTP responses."""

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        client_ip = request.client.host if request.client else "unknown"

        # Rate Limiting on sensitive endpoints
        path = request.url.path
        if settings.RATE_LIMIT_ENABLED:
            if path == "/api/v1/copilot/chat" and request.method == "POST":
                allowed, remaining = rate_limiter.is_allowed(
                    key=f"copilot:{client_ip}",
                    max_requests=settings.COPILOT_RATE_LIMIT_RPM,
                    window_seconds=60
                )
                if not allowed:
                    logger.warning(f"Rate limit exceeded for {client_ip} on {path}")
                    return Response(
                        content='{"detail":"Rate limit exceeded for copilot. Maximum 30 requests per minute."}',
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        media_type="application/json",
                        headers={"Retry-After": "60"}
                    )

            elif path.startswith("/api/v1/ingest/") and request.method == "POST":
                allowed, remaining = rate_limiter.is_allowed(
                    key=f"ingest:{client_ip}",
                    max_requests=settings.INGEST_RATE_LIMIT_RPM,
                    window_seconds=60
                )
                if not allowed:
                    logger.warning(f"Rate limit exceeded for {client_ip} on {path}")
                    return Response(
                        content='{"detail":"Ingest rate limit exceeded. Maximum 120 requests per minute."}',
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        media_type="application/json",
                        headers={"Retry-After": "60"}
                    )

        # Process request
        response = await call_next(request)

        # Compute execution time
        process_time_ms = (time.time() - start_time) * 1000.0

        # Inject Production Security & Telemetry Headers
        response.headers["X-Process-Time-Ms"] = f"{process_time_ms:.2f}"
        if settings.SECURITY_HEADERS_ENABLED:
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "SAMEORIGIN"
            response.headers["X-XSS-Protection"] = "1; mode=block"
            response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
            response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
            if settings.AIR_SENSE_ENV == "production":
                response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"

        return response
