from __future__ import annotations

from typing import Any

from flask import Flask, jsonify, request

from backend.config import Settings, load_settings
from backend.models import NetworkSnapshot, isoformat, validate_role
from backend.proximity import calculate_proximity
from backend.storage import InMemorySessionStore


STORE = InMemorySessionStore()


def _json_error(message: str, status: int) -> tuple[Any, int]:
    return jsonify({"error": message}), status


def create_app(settings: Settings | None = None) -> Flask:
    app = Flask(__name__)
    app.config["SETTINGS"] = settings or load_settings()
    app.config["STORE"] = STORE

    @app.before_request
    def _auth_guard() -> tuple[Any, int] | None:
        cfg: Settings = app.config["SETTINGS"]
        if not cfg.api_key:
            return None
        if request.path == "/api/health":
            return None
        provided = request.headers.get("x-api-key")
        if provided != cfg.api_key:
            return _json_error("unauthorized", 401)
        return None

    @app.get("/")
    def root() -> Any:
        return jsonify({"service": "net-proximity-backend", "ok": True})

    @app.get("/api/health")
    def health() -> Any:
        cfg: Settings = app.config["SETTINGS"]
        return jsonify(
            {
                "ok": True,
                "offline_after_seconds": cfg.offline_after_seconds,
                "session_max_hours": cfg.session_max_hours,
            }
        )

    @app.post("/api/v1/sessions")
    def create_session() -> Any:
        body = request.get_json(silent=True) or {}
        device_id = (body.get("device_id") or "").strip()
        device_name = (body.get("device_name") or "").strip() or None
        role = validate_role((body.get("role") or "desktop").strip().lower())

        store: InMemorySessionStore = app.config["STORE"]
        session = store.create_session(device_id=device_id, device_name=device_name, role=role)
        return jsonify({"session": session.to_dict()}), 201

    @app.post("/api/v1/sessions/join")
    def join_session() -> Any:
        body = request.get_json(silent=True) or {}
        pair_code = (body.get("pair_code") or "").strip()
        device_id = (body.get("device_id") or "").strip()
        device_name = (body.get("device_name") or "").strip() or None
        role = validate_role((body.get("role") or "phone").strip().lower())

        store: InMemorySessionStore = app.config["STORE"]
        session = store.join_session(
            pair_code=pair_code,
            device_id=device_id,
            device_name=device_name,
            role=role,
        )
        return jsonify({"session": session.to_dict()}), 200

    @app.post("/api/v1/heartbeat")
    def heartbeat() -> Any:
        body = request.get_json(silent=True) or {}
        session_id = (body.get("session_id") or "").strip()
        device_id = (body.get("device_id") or "").strip()
        role = validate_role((body.get("role") or "").strip().lower())
        device_name = (body.get("device_name") or "").strip() or None
        network = NetworkSnapshot.from_payload(body.get("network"))
        if not network.public_ip:
            forwarded = request.headers.get("x-forwarded-for", "")
            network.public_ip = forwarded.split(",")[0].strip() if forwarded else request.remote_addr
        latency_ms = body.get("latency_ms")
        rssi_dbm = body.get("rssi_dbm")
        battery_pct = body.get("battery_pct")

        if latency_ms is not None:
            latency_ms = int(latency_ms)
        if rssi_dbm is not None:
            rssi_dbm = int(rssi_dbm)
        if battery_pct is not None:
            battery_pct = int(battery_pct)

        store: InMemorySessionStore = app.config["STORE"]
        device = store.upsert_device(
            session_id=session_id,
            device_id=device_id,
            role=role,
            device_name=device_name,
        )
        device.record_heartbeat(
            network=network,
            latency_ms=latency_ms,
            rssi_dbm=rssi_dbm,
            battery_pct=battery_pct,
        )

        session = store.get_session(session_id)
        if session is None:
            return _json_error("session_id not found", 404)

        cfg: Settings = app.config["SETTINGS"]
        proximity = calculate_proximity(session, offline_after_seconds=cfg.offline_after_seconds)
        return jsonify({"ok": True, "last_seen": isoformat(device.last_seen), "proximity": proximity}), 200

    @app.get("/api/v1/sessions/<session_id>/status")
    def session_status(session_id: str) -> Any:
        store: InMemorySessionStore = app.config["STORE"]
        session = store.get_session(session_id)
        if session is None:
            return _json_error("session_id not found", 404)
        cfg: Settings = app.config["SETTINGS"]
        proximity = calculate_proximity(session, offline_after_seconds=cfg.offline_after_seconds)
        return jsonify({"session": session.to_dict(), "proximity": proximity}), 200

    @app.post("/api/v1/sessions/prune")
    def prune_sessions() -> Any:
        cfg: Settings = app.config["SETTINGS"]
        store: InMemorySessionStore = app.config["STORE"]
        removed = store.prune_old_sessions(max_hours=cfg.session_max_hours)
        return jsonify({"removed": removed}), 200

    @app.errorhandler(KeyError)
    def handle_key_error(error: KeyError) -> tuple[Any, int]:
        return _json_error(str(error).strip("'"), 404)

    @app.errorhandler(ValueError)
    def handle_value_error(error: ValueError) -> tuple[Any, int]:
        return _json_error(str(error), 400)

    @app.errorhandler(Exception)
    def handle_exception(error: Exception) -> tuple[Any, int]:
        return _json_error(f"internal_error: {error.__class__.__name__}", 500)

    return app
