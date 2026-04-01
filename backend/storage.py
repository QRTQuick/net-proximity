from __future__ import annotations

from datetime import timedelta
import secrets
import threading
import uuid

from backend.models import DeviceState, SessionState, utcnow, validate_role


class InMemorySessionStore:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._sessions: dict[str, SessionState] = {}
        self._pair_index: dict[str, str] = {}

    def _new_session_id(self) -> str:
        return uuid.uuid4().hex

    def _new_pair_code(self) -> str:
        while True:
            code = f"{secrets.randbelow(1_000_000):06d}"
            if code not in self._pair_index:
                return code

    def create_session(self, device_id: str, device_name: str | None, role: str = "desktop") -> SessionState:
        if not device_id:
            raise ValueError("device_id is required")

        role = validate_role(role)

        with self._lock:
            session_id = self._new_session_id()
            pair_code = self._new_pair_code()
            session = SessionState(session_id=session_id, pair_code=pair_code)
            session.devices[device_id] = DeviceState(device_id=device_id, role=role, device_name=device_name)
            self._sessions[session_id] = session
            self._pair_index[pair_code] = session_id
            return session

    def join_session(self, pair_code: str, device_id: str, device_name: str | None, role: str) -> SessionState:
        if not pair_code:
            raise ValueError("pair_code is required")
        if not device_id:
            raise ValueError("device_id is required")
        role = validate_role(role)

        with self._lock:
            session_id = self._pair_index.get(pair_code)
            if not session_id:
                raise KeyError("pair_code not found")

            session = self._sessions[session_id]
            existing = session.devices.get(device_id)
            if existing:
                existing.role = role
                existing.device_name = device_name or existing.device_name
            else:
                session.devices[device_id] = DeviceState(
                    device_id=device_id,
                    role=role,
                    device_name=device_name,
                )
            return session

    def get_session(self, session_id: str) -> SessionState | None:
        with self._lock:
            return self._sessions.get(session_id)

    def get_by_pair_code(self, pair_code: str) -> SessionState | None:
        with self._lock:
            session_id = self._pair_index.get(pair_code)
            if not session_id:
                return None
            return self._sessions.get(session_id)

    def upsert_device(self, session_id: str, device_id: str, role: str, device_name: str | None) -> DeviceState:
        if not session_id:
            raise ValueError("session_id is required")
        if not device_id:
            raise ValueError("device_id is required")
        role = validate_role(role)

        with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                raise KeyError("session_id not found")
            device = session.devices.get(device_id)
            if device:
                device.role = role
                if device_name:
                    device.device_name = device_name
                return device
            device = DeviceState(device_id=device_id, role=role, device_name=device_name)
            session.devices[device_id] = device
            return device

    def prune_old_sessions(self, max_hours: int) -> int:
        now = utcnow()
        max_age = timedelta(hours=max_hours)

        removed = 0
        with self._lock:
            for session_id, session in list(self._sessions.items()):
                if now - session.created_at > max_age:
                    removed += 1
                    self._sessions.pop(session_id, None)
                    self._pair_index.pop(session.pair_code, None)
        return removed
