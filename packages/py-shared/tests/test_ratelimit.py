"""Unit tests for imb_shared.ratelimit (S01 R7.1-R7.5, ADR-022).

Behavior against a real Redis is covered by integration tests in task 3.
"""

import re
from typing import Any

import pytest
import redis

from imb_shared.clock import FakeClock
from imb_shared.ratelimit import (
    RateLimiter,
    RateLimitUnavailable,
    Rule,
    rate_key,
    retry_after_s,
    subject_part,
    window_index,
)

RULE = Rule(name="search", limit=3, window_s=60)


class FakeScript:
    """Stands in for a registered Redis Lua script: counts hits per key."""

    def __init__(self) -> None:
        self.counts: dict[str, int] = {}
        self.calls: list[tuple[list[str], list[Any]]] = []

    def __call__(self, keys: list[str], args: list[Any]) -> int:
        self.calls.append((keys, args))
        self.counts[keys[0]] = self.counts.get(keys[0], 0) + 1
        return self.counts[keys[0]]


class FakeRedis:
    def __init__(self) -> None:
        self.lua = ""
        self.script = FakeScript()

    def register_script(self, lua: str) -> FakeScript:
        self.lua = lua
        return self.script


class BrokenRedis:
    def register_script(self, lua: str) -> Any:
        def fail(keys: list[str], args: list[Any]) -> int:
            raise redis.exceptions.ConnectionError("redis is down")

        return fail


def test_subject_part_keeps_safe_subjects() -> None:
    assert subject_part("user_123-AB") == "user_123-AB"


@pytest.mark.parametrize("subject", ["ab:cd", "a" * 65, "", "名前", "1.2.3.4"])
def test_subject_part_hashes_unsafe_or_long_subjects(subject: str) -> None:
    part = subject_part(subject)
    assert re.fullmatch(r"[0-9a-f]{32}", part)


def test_subject_part_is_deterministic() -> None:
    assert subject_part("ab:cd") == subject_part("ab:cd")
    assert subject_part("ab:cd") != subject_part("ab:ce")


def test_window_index() -> None:
    assert window_index(0, 60) == 0
    assert window_index(59_999, 60) == 0
    assert window_index(60_000, 60) == 1


def test_rate_key_format() -> None:
    assert rate_key(RULE, "u1", 61_000) == "imb:rl:search:u1:1"


def test_retry_after_is_at_least_one_second() -> None:
    assert retry_after_s(0, 60) == 60
    assert retry_after_s(30_500, 60) == 30
    assert retry_after_s(59_999, 60) == 1


def test_lua_script_is_atomic_incr_with_expiry() -> None:
    fake = FakeRedis()
    RateLimiter(fake, FakeClock(0))
    assert "INCR" in fake.lua
    assert "PEXPIRE" in fake.lua


def test_allows_until_limit_then_blocks() -> None:
    limiter = RateLimiter(FakeRedis(), FakeClock(1_000))
    decisions = [limiter.hit(RULE, "u1") for _ in range(4)]
    assert [d.allowed for d in decisions] == [True, True, True, False]
    assert decisions[0].remaining == 2
    assert decisions[3].remaining == 0
    assert decisions[3].retry_after_s >= 1


def test_new_window_resets_the_count() -> None:
    clock = FakeClock(1_000)
    limiter = RateLimiter(FakeRedis(), clock)
    for _ in range(3):
        limiter.hit(RULE, "u1")
    assert limiter.hit(RULE, "u1").allowed is False
    clock.advance(60_000)
    assert limiter.hit(RULE, "u1").allowed is True


def test_subjects_are_counted_independently() -> None:
    limiter = RateLimiter(FakeRedis(), FakeClock(1_000))
    for _ in range(3):
        limiter.hit(RULE, "u1")
    assert limiter.hit(RULE, "u2").allowed is True


def test_key_ttl_covers_the_window_plus_slack() -> None:
    fake = FakeRedis()
    RateLimiter(fake, FakeClock(1_000)).hit(RULE, "u1")
    keys, args = fake.script.calls[-1]
    assert keys == ["imb:rl:search:u1:0"]
    assert int(args[0]) == 61_000


def test_redis_errors_raise_rate_limit_unavailable() -> None:
    limiter = RateLimiter(BrokenRedis(), FakeClock(0))
    with pytest.raises(RateLimitUnavailable):
        limiter.hit(RULE, "u1")


@pytest.mark.parametrize(
    "kwargs",
    [
        {"name": "bad name!", "limit": 1, "window_s": 1},
        {"name": "ok", "limit": 0, "window_s": 1},
        {"name": "ok", "limit": 1, "window_s": 0},
        {"name": "ok", "limit": 1, "window_s": 1, "fail_mode": "maybe"},
    ],
)
def test_invalid_rules_are_rejected(kwargs: dict[str, Any]) -> None:
    with pytest.raises(ValueError):
        Rule(**kwargs)


def test_rule_defaults_to_fail_closed() -> None:
    assert Rule(name="ok", limit=1, window_s=1).fail_mode == "closed"
