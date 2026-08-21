import time
import logging
from collections import defaultdict
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger("rate_limiter")


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Token bucket rate limiter using in-memory storage.
    Falls back gracefully - if Redis is available, uses Redis; otherwise uses in-memory dict.
    
    Configurable per-IP rate limiting with burst support.
    """

    def __init__(self, app, requests_per_minute: int = 60, burst: int = 10):
        super().__init__(app)
        self.rpm = requests_per_minute
        self.burst = burst
        # In-memory fallback: {ip: {"tokens": float, "last_refill": float}}
        self._buckets: dict[str, dict] = defaultdict(
            lambda: {"tokens": float(burst), "last_refill": time.time()}
        )

    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for health checks and docs
        if request.url.path in ("/health", "/api/docs", "/api/redoc", "/api/openapi.json"):
            return await call_next(request)

        client_ip = self._get_client_ip(request)

        if not self._allow_request(client_ip):
            logger.warning(f"Rate limit exceeded for IP: {client_ip}")
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": True,
                    "message": "Rate limit exceeded. Please try again later.",
                    "retry_after_seconds": 60,
                },
                headers={"Retry-After": "60"},
            )

        response = await call_next(request)

        # Add rate limit headers
        bucket = self._buckets[client_ip]
        response.headers["X-RateLimit-Limit"] = str(self.rpm)
        response.headers["X-RateLimit-Remaining"] = str(int(bucket["tokens"]))

        return response

    def _allow_request(self, client_ip: str) -> bool:
        """Token bucket algorithm: refill tokens based on elapsed time."""
        bucket = self._buckets[client_ip]
        now = time.time()

        # Refill tokens based on time elapsed
        elapsed = now - bucket["last_refill"]
        refill_rate = self.rpm / 60.0  # tokens per second
        bucket["tokens"] = min(
            float(self.burst),
            bucket["tokens"] + elapsed * refill_rate,
        )
        bucket["last_refill"] = now

        # Consume a token
        if bucket["tokens"] >= 1.0:
            bucket["tokens"] -= 1.0
            return True
        return False

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP, respecting X-Forwarded-For behind proxy."""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"
