"""Tests for imb_shared.logging (S01 R4.1-R4.3, N5)."""

import io
import json
from collections.abc import Iterator
from typing import Any

import pytest
import structlog

from imb_shared.logging import configure_logging, get_logger

JWT = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.c2lnbmF0dXJlLXZhbHVl"


@pytest.fixture
def capture() -> Iterator[io.StringIO]:
    buf = io.StringIO()
    configure_logging(service="api", level="INFO", stream=buf)
    yield buf
    structlog.contextvars.clear_contextvars()


def records(buf: io.StringIO) -> list[dict[str, Any]]:
    return [json.loads(line) for line in buf.getvalue().splitlines() if line.strip()]


def test_one_json_object_per_line_with_required_fields(capture: io.StringIO) -> None:
    get_logger().info("request.done")
    record = records(capture)[-1]
    assert record["event"] == "request.done"
    assert record["service"] == "api"
    assert record["level"] == "info"
    assert "timestamp" in record


def test_request_id_comes_from_context(capture: io.StringIO) -> None:
    structlog.contextvars.bind_contextvars(request_id="req-123")
    get_logger().info("evt")
    assert records(capture)[-1]["request_id"] == "req-123"


def test_level_filter_drops_debug(capture: io.StringIO) -> None:
    get_logger().debug("hidden.event")
    assert all(r["event"] != "hidden.event" for r in records(capture))


@pytest.mark.parametrize(
    "key",
    [
        "authorization",
        "Authorization",
        "cookie",
        "set-cookie",
        "access_token",
        "refresh_token",
        "code",
        "code_verifier",
        "client_secret",
        "email",
        "spotify_token",
        "webhook_secret",
    ],
)
def test_sensitive_keys_are_redacted(capture: io.StringIO, key: str) -> None:
    get_logger().info("evt", **{key: "sensitive-value"})
    assert records(capture)[-1][key] == "[REDACTED]"
    assert "sensitive-value" not in capture.getvalue()


def test_nested_sensitive_values_are_redacted(capture: io.StringIO) -> None:
    get_logger().info(
        "evt",
        headers={"Authorization": "Bearer nested-secret"},
        items=[{"refresh_token": "list-secret"}],
    )
    raw = capture.getvalue()
    assert "nested-secret" not in raw
    assert "list-secret" not in raw


def test_token_shapes_in_strings_are_redacted(capture: io.StringIO) -> None:
    get_logger().info(
        f"calling upstream with Bearer abc.def-123 and {JWT}",
        note=f"token={JWT}",
        basic="Basic dXNlcjpwYXNzd29yZA==",
    )
    raw = capture.getvalue()
    assert "abc.def-123" not in raw
    assert JWT not in raw
    assert "dXNlcjpwYXNzd29yZA==" not in raw
    assert "[REDACTED]" in raw


def test_long_strings_are_truncated(capture: io.StringIO) -> None:
    get_logger().info("evt", blob="x" * 5000)
    blob = records(capture)[-1]["blob"]
    assert len(blob) <= 2000
    assert blob.endswith("[truncated]")


def test_line_is_capped_at_8kb_and_stays_valid_json(capture: io.StringIO) -> None:
    get_logger().info("evt", **{f"field_{i}": "y" * 1500 for i in range(20)})
    line = capture.getvalue().splitlines()[-1]
    assert len(line.encode("utf-8")) <= 8192
    record = json.loads(line)
    assert record["log_truncated"] is True
    assert record["event"] == "evt"
