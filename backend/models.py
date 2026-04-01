from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import ipaddress
from typing import Any


ALLOWED_ROLES = {"desktop", "phone"}


def utcnow() -> datetime:
    return datetime.now(tz=timezone.utc)


def isoformat(dt: datetime) -> str:
    return dt.isoformat().replace("+00:00", "Z")


def validate_role(role: str) -> str:
    value = (role or "").strip().lower()
    if value not in ALLOWED_ROLES:
        raise ValueError("role must be desktop or phone")
    return value


def normalize_mac(raw: str | None) -> str | None:
    if raw is None:
        return None
    value = "".join(ch for ch in raw.lower() if ch.isalnum())
    if len(value) != 12:
        return None
    return ":".join(value[i : i + 2] for i in range(0, 12, 2))


def is_same_subnet(ip_one: str | None, ip_two: str | None, prefix: int = 24) -> bool:
    if not ip_one or not ip_two:
        return False
    try:
        net_a = ipaddress.ip_network(f"{ip_one}/{prefix}", strict=False)
        net_b = ipaddress.ip_network(f"{ip_two}/{prefix}", strict=False)
    except ValueError:
        return False
    return net_a.network_address == net_b.network_address


@dataclass
class NetworkSnapshot:
    local_ip: str | None = None
    public_ip: str | None = None
    wifi_ssid: str | None = None
    wifi_bssid: str | None = None
    transport: str | None = None

    @classmethod
    def from_payload(cls, payload: dict[str, Any] | None) -> "NetworkSnapshot":
        data = payload or {}
        return cls(
            local_ip=data.get("local_ip"),
            public_ip=data.get("public_ip"),
            wifi_ssid=data.get("wifi_ssid"),
            wifi_bssid=normalize_mac(data.get("wifi_bssid")),
            transport=data.get("transport"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "local_ip": self.local_ip,
            "public_ip": self.public_ip,
            "wifi_ssid": self.wifi_ssid,
            "wifi_bssid": self.wifi_bssid,
            "transport": self.transport,
        }


@dataclass
class DeviceState:
    device_id: str
    role: str
    device_name: str | None = None
    joined_at: datetime = field(default_factory=utcnow)
    last_seen: datetime = field(default_factory=utcnow)
    heartbeat_count: int = 0
    latency_ms: int | None = None
    rssi_dbm: int | None = None
    battery_pct: int | None = None
    network: NetworkSnapshot = field(default_factory=NetworkSnapshot)

    def record_heartbeat(
        self,
        network: NetworkSnapshot,
        latency_ms: int | None,
        rssi_dbm: int | None,
        battery_pct: int | None,
    ) -> None:
        self.last_seen = utcnow()
        self.heartbeat_count += 1
        self.network = network
        self.latency_ms = latency_ms
        self.rssi_dbm = rssi_dbm
        self.battery_pct = battery_pct

    def to_dict(self) -> dict[str, Any]:
        return {
            "device_id": self.device_id,
            "role": self.role,
            "device_name": self.device_name,
            "joined_at": isoformat(self.joined_at),
            "last_seen": isoformat(self.last_seen),
            "heartbeat_count": self.heartbeat_count,
            "latency_ms": self.latency_ms,
            "rssi_dbm": self.rssi_dbm,
            "battery_pct": self.battery_pct,
            "network": self.network.to_dict(),
        }


@dataclass
class SessionState:
    session_id: str
    pair_code: str
    created_at: datetime = field(default_factory=utcnow)
    devices: dict[str, DeviceState] = field(default_factory=dict)

    def get_role(self, role: str) -> DeviceState | None:
        for device in self.devices.values():
            if device.role == role:
                return device
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "pair_code": self.pair_code,
            "created_at": isoformat(self.created_at),
            "devices": {device_id: state.to_dict() for device_id, state in self.devices.items()},
        }

