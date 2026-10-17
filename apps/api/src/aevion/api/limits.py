"""Per-visitor rate limits (SPEC `api`: 10 asks a minute and 100 a day per IP).

The public demo has no logins, so the IP is the visitor. Requests reach us through the
Next.js proxy on Vercel, so the connecting IP is Vercel's, the same for everyone. The proxy
forwards the visitor's IP in `X-Aevion-Client-IP` along with a shared secret; that header is
trusted only when the secret matches, so a visitor can't pick their own key. Without it we
fall back to the address Railway's edge saw.

One API instance serves the demo, so the windows live in memory: a restart resets them,
which is fine for a rate limit and keeps FalkorDB for the knowledge, not counters.
"""

import hmac
import threading
import time
from collections import deque
from collections.abc import Callable

from fastapi import HTTPException, Request

ASK_RULES = ((10, 60.0), (100, 86_400.0))  # (requests, per seconds)
TOOL_RULES = ((60, 60.0),)  # tool calls cost no LLM money; this only stops scraping


class RateLimiter:
    """Sliding windows per key. A request counts only if every window has room for it."""

    def __init__(
        self,
        rules: tuple[tuple[int, float], ...],
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.rules = rules
        self._clock = clock
        self._hits: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def hit(self, key: str) -> float | None:
        """Record a request; return None if allowed, else the seconds until it would be."""
        now = self._clock()
        longest = max(window for _, window in self.rules)
        with self._lock:
            hits = self._hits.setdefault(key, deque())
            while hits and now - hits[0] >= longest:
                hits.popleft()
            wait = 0.0
            for limit, window in self.rules:
                recent = [t for t in hits if now - t < window]
                if len(recent) >= limit:
                    wait = max(wait, window - (now - recent[-limit]))
            if wait > 0:
                return wait
            hits.append(now)
            return None


def client_ip(request: Request, proxy_secret: str | None) -> str:
    forwarded_by_us = request.headers.get("x-aevion-client-ip")
    secret = request.headers.get("x-aevion-proxy-secret")
    if forwarded_by_us and proxy_secret and secret and hmac.compare_digest(secret, proxy_secret):
        return forwarded_by_us
    # Railway's edge appends the address it saw; anything to its left came from the client.
    chain = [p.strip() for p in request.headers.get("x-forwarded-for", "").split(",") if p.strip()]
    if chain:
        return chain[-1]
    return request.client.host if request.client else "unknown"


def enforce(limiter: RateLimiter, request: Request, proxy_secret: str | None) -> None:
    wait = limiter.hit(client_ip(request, proxy_secret))
    if wait is not None:
        seconds = max(1, int(wait + 0.999))
        raise HTTPException(
            status_code=429,
            detail="Too many questions from this address. Try again shortly.",
            headers={"Retry-After": str(seconds)},
        )
