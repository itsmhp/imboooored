"""Tests for imb_shared.clock (S01 R7.5)."""

import time

from imb_shared.clock import FakeClock, SystemClock


def test_system_clock_returns_current_epoch_ms() -> None:
    before = int(time.time() * 1000)
    now = SystemClock().now_ms()
    after = int(time.time() * 1000)
    assert isinstance(now, int)
    assert before <= now <= after


def test_fake_clock_starts_where_told_and_advances() -> None:
    clock = FakeClock(1_000)
    assert clock.now_ms() == 1_000
    clock.advance(500)
    assert clock.now_ms() == 1_500


def test_fake_clock_can_be_set() -> None:
    clock = FakeClock(0)
    clock.set(42_000)
    assert clock.now_ms() == 42_000
