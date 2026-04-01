from __future__ import annotations

import os
from dataclasses import dataclass


def _read_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    offline_after_seconds: int
    session_max_hours: int
    api_key: str | None


def load_settings() -> Settings:
    return Settings(
        offline_after_seconds=_read_int("OFFLINE_AFTER_SECONDS", 45),
        session_max_hours=_read_int("SESSION_MAX_HOURS", 24),
        api_key=os.getenv("API_KEY"),
    )

