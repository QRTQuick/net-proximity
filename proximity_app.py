#!/usr/bin/env python3
from __future__ import annotations

import argparse
import socket
import time
import uuid
from typing import Any

import requests


def _safe_local_ip() -> str | None:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        return sock.getsockname()[0]
    except OSError:
        return None
    finally:
        sock.close()


def _guess_transport(local_ip: str | None) -> str | None:
    if not local_ip:
        return None
    if local_ip.startswith("192.168.") or local_ip.startswith("10."):
        return "wifi_or_hotspot"
    if local_ip.startswith("172."):
        return "wifi_or_hotspot"
    return "internet"


class ApiClient:
    def __init__(self, base_url: str, api_key: str | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        if api_key:
            self.session.headers["x-api-key"] = api_key

    def post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        response = self.session.post(f"{self.base_url}{path}", json=payload, timeout=8)
        response.raise_for_status()
        return response.json()

    def get(self, path: str) -> dict[str, Any]:
        response = self.session.get(f"{self.base_url}{path}", timeout=8)
        response.raise_for_status()
        return response.json()


def _default_device_id() -> str:
    return f"desktop-{uuid.getnode():x}"


def _print_status(status_payload: dict[str, Any]) -> None:
    proximity = status_payload.get("proximity", {})
    session = status_payload.get("session", {})
    print(
        f"[status] session={session.get('session_id')} "
        f"score={proximity.get('score')} "
        f"band={proximity.get('band')} "
        f"state={proximity.get('status')}"
    )


def run(args: argparse.Namespace) -> None:
    api = ApiClient(args.backend_url, args.api_key)

    if args.mode == "desktop":
        created = api.post(
            "/api/v1/sessions",
            {
                "device_id": args.device_id,
                "device_name": args.device_name,
                "role": "desktop",
            },
        )
        session = created["session"]
        session_id = session["session_id"]
        print(f"Session created. pair_code={session['pair_code']} session_id={session_id}")
    else:
        if not args.pair_code:
            raise SystemExit("--pair-code is required in phone mode")
        joined = api.post(
            "/api/v1/sessions/join",
            {
                "pair_code": args.pair_code,
                "device_id": args.device_id,
                "device_name": args.device_name,
                "role": "phone",
            },
        )
        session = joined["session"]
        session_id = session["session_id"]
        print(f"Joined session {session_id}")

    print("Sending heartbeats. Press Ctrl+C to stop.")

    tick = 0
    while True:
        tick += 1
        local_ip = _safe_local_ip()
        payload = {
            "session_id": session_id,
            "device_id": args.device_id,
            "device_name": args.device_name,
            "role": args.mode,
            "latency_ms": args.latency_ms,
            "rssi_dbm": args.rssi_dbm,
            "battery_pct": args.battery_pct,
            "network": {
                "local_ip": local_ip,
                "public_ip": args.public_ip,
                "wifi_ssid": args.wifi_ssid,
                "wifi_bssid": args.wifi_bssid,
                "transport": _guess_transport(local_ip),
            },
        }
        heartbeat = api.post("/api/v1/heartbeat", payload)
        proximity = heartbeat.get("proximity", {})
        print(
            f"[heartbeat] score={proximity.get('score')} "
            f"band={proximity.get('band')} "
            f"status={proximity.get('status')}"
        )

        if tick % 3 == 0:
            status = api.get(f"/api/v1/sessions/{session_id}/status")
            _print_status(status)

        time.sleep(args.interval)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Desktop/phone client for net proximity backend")
    parser.add_argument("--backend-url", required=True, help="Example: https://your-app.vercel.app")
    parser.add_argument("--mode", choices=["desktop", "phone"], default="desktop")
    parser.add_argument("--pair-code", help="Required when --mode phone")
    parser.add_argument("--device-id", default=_default_device_id())
    parser.add_argument("--device-name", default=socket.gethostname())
    parser.add_argument("--interval", type=int, default=5)
    parser.add_argument("--latency-ms", type=int, default=30)
    parser.add_argument("--rssi-dbm", type=int, default=-50)
    parser.add_argument("--battery-pct", type=int, default=80)
    parser.add_argument("--wifi-ssid", default=None)
    parser.add_argument("--wifi-bssid", default=None)
    parser.add_argument("--public-ip", default=None)
    parser.add_argument("--api-key", default=None)
    return parser.parse_args()


if __name__ == "__main__":
    try:
        run(parse_args())
    except KeyboardInterrupt:
        print("\nStopped.")
