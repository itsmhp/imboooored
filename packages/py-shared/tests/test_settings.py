"""Tests for imb_shared.settings (S01 R3.1-R3.6, R17.3)."""

import json
from collections.abc import Callable

import pytest

from imb_shared.settings import BaseServiceSettings, load_settings

SECRET = "s3cr3t-value-never-print"

VALID_DEV = {
    "APP_ENV": "dev",
    "SERVICE_NAME": "api",
    "DATABASE_URL": f"postgresql+psycopg://imb_api:{SECRET}@postgres:5432/imbooored",
    "REDIS_URL": f"redis://:{SECRET}@redis:6379/0",
    "ALLOWED_ORIGINS": "http://127.0.0.1:3000",
}

# Hosts that are valid in prod: not loopback, not a single-label Docker name.
PROD_OK = {
    "APP_ENV": "prod",
    "DATABASE_URL": f"postgresql+psycopg://imb_api:{SECRET}@db.internal.example.com:5432/imbooored",
    "REDIS_URL": f"rediss://:{SECRET}@cache.internal.example.com:6380/0",
    "ALLOWED_ORIGINS": "https://imbooored.example.com",
}

ALL_KEYS = [*VALID_DEV, "LOG_LEVEL"]

SetEnv = Callable[..., None]


@pytest.fixture
def set_env(monkeypatch: pytest.MonkeyPatch) -> SetEnv:
    def apply(**overrides: str | None) -> None:
        for key in ALL_KEYS:
            monkeypatch.delenv(key, raising=False)
        for key, value in {**VALID_DEV, **overrides}.items():
            if value is not None:
                monkeypatch.setenv(key, value)

    return apply


def _failed_fields(capsys: pytest.CaptureFixture[str]) -> tuple[list[str], str]:
    err = capsys.readouterr().err
    record = json.loads(err.strip().splitlines()[-1])
    return record["invalid_fields"], err


def test_valid_dev_settings_load(set_env: SetEnv) -> None:
    set_env()
    settings = load_settings(BaseServiceSettings)
    assert settings.APP_ENV == "dev"
    assert settings.SERVICE_NAME == "api"
    assert settings.LOG_LEVEL == "INFO"
    assert settings.ALLOWED_ORIGINS == ["http://127.0.0.1:3000"]


def test_origins_are_split_and_trimmed(set_env: SetEnv) -> None:
    set_env(ALLOWED_ORIGINS="http://127.0.0.1:3000, http://localhost:3000")
    settings = load_settings(BaseServiceSettings)
    assert settings.ALLOWED_ORIGINS == ["http://127.0.0.1:3000", "http://localhost:3000"]


def test_valid_prod_settings_load(set_env: SetEnv) -> None:
    set_env(**PROD_OK)
    settings = load_settings(BaseServiceSettings)
    assert settings.APP_ENV == "prod"


def test_debug_log_level_allowed_in_dev(set_env: SetEnv) -> None:
    set_env(LOG_LEVEL="DEBUG")
    assert load_settings(BaseServiceSettings).LOG_LEVEL == "DEBUG"


def test_secret_values_never_appear_in_repr_or_dump(set_env: SetEnv) -> None:
    set_env()
    settings = load_settings(BaseServiceSettings)
    assert SECRET not in repr(settings)
    assert SECRET not in str(settings.model_dump())


@pytest.mark.parametrize(
    "missing", ["APP_ENV", "SERVICE_NAME", "DATABASE_URL", "REDIS_URL", "ALLOWED_ORIGINS"]
)
def test_missing_required_setting_exits_78_naming_the_key(
    set_env: SetEnv, capsys: pytest.CaptureFixture[str], missing: str
) -> None:
    set_env(**{missing: None})
    with pytest.raises(SystemExit) as exc:
        load_settings(BaseServiceSettings)
    assert exc.value.code == 78
    fields, err = _failed_fields(capsys)
    assert missing in fields
    assert SECRET not in err


@pytest.mark.parametrize(
    ("overrides", "field"),
    [
        ({"APP_ENV": "production"}, "APP_ENV"),
        ({"ALLOWED_ORIGINS": "*"}, "ALLOWED_ORIGINS"),
        ({"ALLOWED_ORIGINS": "http://127.0.0.1:3000/path"}, "ALLOWED_ORIGINS"),
        ({"ALLOWED_ORIGINS": "127.0.0.1:3000"}, "ALLOWED_ORIGINS"),
        ({**PROD_OK, "ALLOWED_ORIGINS": "*"}, "ALLOWED_ORIGINS"),
        (
            {"APP_ENV": "staging", "ALLOWED_ORIGINS": "http://staging.example.com"},
            "ALLOWED_ORIGINS",
        ),
        ({"APP_ENV": "staging", "LOG_LEVEL": "DEBUG"}, "LOG_LEVEL"),
        ({"LOG_LEVEL": "VERBOSE"}, "LOG_LEVEL"),
        ({"REDIS_URL": "redis://redis:6379/0"}, "REDIS_URL"),
        (
            {**PROD_OK, "DATABASE_URL": f"postgresql+psycopg://u:{SECRET}@localhost:5432/db"},
            "DATABASE_URL",
        ),
        (
            {**PROD_OK, "DATABASE_URL": f"postgresql+psycopg://u:{SECRET}@postgres:5432/db"},
            "DATABASE_URL",
        ),
        ({**PROD_OK, "REDIS_URL": f"redis://:{SECRET}@127.0.0.1:6379/0"}, "REDIS_URL"),
    ],
)
def test_invalid_settings_exit_78_without_leaking_values(
    set_env: SetEnv,
    capsys: pytest.CaptureFixture[str],
    overrides: dict[str, str],
    field: str,
) -> None:
    set_env(**overrides)
    with pytest.raises(SystemExit) as exc:
        load_settings(BaseServiceSettings)
    assert exc.value.code == 78
    fields, err = _failed_fields(capsys)
    assert field in fields
    assert SECRET not in err
