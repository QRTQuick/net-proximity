from __future__ import annotations

from datetime import datetime
from typing import Any

from backend.models import DeviceState, SessionState, is_same_subnet, utcnow
from backend.native_score import signal_penalty


def _age_seconds(now: datetime, device: DeviceState | None) -> float | None:
    if device is None:
        return None
    return max(0.0, (now - device.last_seen).total_seconds())


def _connected(age_seconds: float | None, timeout: int) -> bool:
    if age_seconds is None:
        return False
    return age_seconds <= timeout


def _band_from_score(score: int) -> str:
    if score >= 85:
        return "immediate"
    if score >= 65:
        return "near"
    if score >= 40:
        return "far"
    return "unknown"


def calculate_proximity(session: SessionState, offline_after_seconds: int) -> dict[str, Any]:
    now = utcnow()
    desktop = session.get_role("desktop")
    phone = session.get_role("phone")

    desktop_age = _age_seconds(now, desktop)
    phone_age = _age_seconds(now, phone)
    desktop_online = _connected(desktop_age, offline_after_seconds)
    phone_online = _connected(phone_age, offline_after_seconds)

    reasons: list[str] = []
    score = 0

    if desktop is None or phone is None:
        return {
            "status": "waiting_for_pair",
            "band": "unknown",
            "score": 0,
            "desktop_online": desktop_online,
            "phone_online": phone_online,
            "desktop_age_seconds": desktop_age,
            "phone_age_seconds": phone_age,
            "reasons": ["both devices must join the same session"],
            "updated_at": now.isoformat().replace("+00:00", "Z"),
        }

    if not desktop_online or not phone_online:
        offline_side = "desktop" if not desktop_online else "phone"
        return {
            "status": "disconnected",
            "band": "unknown",
            "score": 0,
            "desktop_online": desktop_online,
            "phone_online": phone_online,
            "desktop_age_seconds": desktop_age,
            "phone_age_seconds": phone_age,
            "reasons": [f"{offline_side} heartbeat is stale"],
            "updated_at": now.isoformat().replace("+00:00", "Z"),
        }

    score = 40
    reasons.append("both devices are actively sending heartbeats")

    if desktop.network.public_ip and desktop.network.public_ip == phone.network.public_ip:
        score += 25
        reasons.append("both devices share the same public IP")

    if desktop.network.wifi_bssid and desktop.network.wifi_bssid == phone.network.wifi_bssid:
        score += 25
        reasons.append("both devices are on the same access point")
    elif desktop.network.wifi_ssid and desktop.network.wifi_ssid == phone.network.wifi_ssid:
        score += 15
        reasons.append("both devices share the same Wi-Fi name")

    if is_same_subnet(desktop.network.local_ip, phone.network.local_ip):
        score += 10
        reasons.append("local addresses are in the same /24 subnet")

    penalty = signal_penalty(phone.latency_ms, phone.rssi_dbm)
    score -= min(30, penalty // 4)

    score = max(0, min(100, score))
    band = _band_from_score(score)

    if band == "immediate":
        status = "very_close"
    elif band == "near":
        status = "close"
    elif band == "far":
        status = "reachable"
    else:
        status = "uncertain"

    return {
        "status": status,
        "band": band,
        "score": score,
        "desktop_online": desktop_online,
        "phone_online": phone_online,
        "desktop_age_seconds": desktop_age,
        "phone_age_seconds": phone_age,
        "reasons": reasons,
        "updated_at": now.isoformat().replace("+00:00", "Z"),
    }

