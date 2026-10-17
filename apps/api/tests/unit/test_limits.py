"""Rate limits: sliding windows, and which IP we trust."""

import re
from pathlib import Path

from starlette.requests import Request

from aevion.agent.hero import HERO_QUESTIONS
from aevion.api.limits import RateLimiter, client_ip


class Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def test_minute_and_day_windows() -> None:
    clock = Clock()
    limiter = RateLimiter(((3, 60.0), (5, 86_400.0)), clock=clock)
    assert [limiter.hit("a") for _ in range(3)] == [None, None, None]
    wait = limiter.hit("a")
    assert wait is not None and 59 < wait <= 60
    assert limiter.hit("b") is None  # other visitors are unaffected
    clock.now += 61
    assert limiter.hit("a") is None and limiter.hit("a") is None  # 5 today
    clock.now += 61
    day_wait = limiter.hit("a")
    assert day_wait is not None and day_wait > 3600  # the daily window is the binding one


def _request(headers: dict[str, str], client: str = "10.0.0.1") -> Request:
    raw = [(k.lower().encode(), v.encode()) for k, v in headers.items()]
    return Request({"type": "http", "headers": raw, "client": (client, 1234)})


def test_forwarded_ip_is_trusted_only_with_the_secret() -> None:
    proxied = {"X-Aevion-Client-IP": "203.0.113.9", "X-Aevion-Proxy-Secret": "s3cret"}
    assert client_ip(_request(proxied), "s3cret") == "203.0.113.9"
    spoofed = {
        **proxied,
        "X-Aevion-Proxy-Secret": "guess",
        "X-Forwarded-For": "1.1.1.1, 198.51.100.7",
    }
    assert client_ip(_request(spoofed), "s3cret") == "198.51.100.7"  # the edge's entry, not theirs
    assert client_ip(_request(proxied), None) == "10.0.0.1"  # no secret configured: trust nothing


def test_hero_questions_match_the_web_app() -> None:
    web = Path(__file__).parents[3] / "web" / "lib" / "hero-questions.ts"
    questions = re.findall(r'question: "([^"]+)"', web.read_text())
    assert tuple(questions) == HERO_QUESTIONS
