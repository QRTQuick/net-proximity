from __future__ import annotations

import socket
import threading
import time
import uuid

import requests
from kivy.app import App
from kivy.clock import Clock
from kivy.lang import Builder
from kivy.properties import StringProperty
from kivy.uix.boxlayout import BoxLayout


KV = """
<RootLayout>:
    orientation: "vertical"
    padding: "16dp"
    spacing: "10dp"

    TextInput:
        id: backend_url
        hint_text: "Backend URL"
        text: root.backend_url
        multiline: False
    TextInput:
        id: pair_code
        hint_text: "Pair Code"
        text: root.pair_code
        multiline: False
    TextInput:
        id: device_name
        hint_text: "Phone Name"
        text: root.device_name
        multiline: False
    Label:
        text: root.status_text
        size_hint_y: None
        height: "60dp"
    BoxLayout:
        size_hint_y: None
        height: "48dp"
        spacing: "8dp"
        Button:
            text: "Join"
            on_release: root.join_session()
        Button:
            text: "Start"
            on_release: root.start_tracking()
        Button:
            text: "Stop"
            on_release: root.stop_tracking()
"""


class RootLayout(BoxLayout):
    backend_url = StringProperty("http://127.0.0.1:5000")
    pair_code = StringProperty("")
    device_name = StringProperty(socket.gethostname())
    status_text = StringProperty("Idle")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.session_id: str | None = None
        self.device_id = f"phone-{uuid.getnode():x}"
        self._runner: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._http = requests.Session()

    def join_session(self) -> None:
        base = self.ids.backend_url.text.strip().rstrip("/")
        pair_code = self.ids.pair_code.text.strip()
        if not base or not pair_code:
            self._set_status("Backend URL and Pair Code required")
            return

        payload = {
            "pair_code": pair_code,
            "device_id": self.device_id,
            "device_name": self.ids.device_name.text.strip() or self.device_name,
            "role": "phone",
        }
        try:
            response = self._http.post(f"{base}/api/v1/sessions/join", json=payload, timeout=8)
            response.raise_for_status()
            session = response.json()["session"]
            self.session_id = session["session_id"]
            self._set_status(f"Joined: {self.session_id}")
        except requests.RequestException as exc:
            self._set_status(f"Join failed: {exc}")

    def start_tracking(self) -> None:
        if not self.session_id:
            self._set_status("Join a session first")
            return
        if self._runner and self._runner.is_alive():
            self._set_status("Tracking already running")
            return
        self._stop_event.clear()
        self._runner = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self._runner.start()
        self._set_status("Tracking started")

    def stop_tracking(self) -> None:
        self._stop_event.set()
        self._set_status("Tracking stopped")

    def _safe_local_ip(self) -> str | None:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.connect(("8.8.8.8", 80))
            return sock.getsockname()[0]
        except OSError:
            return None
        finally:
            sock.close()

    def _heartbeat_loop(self) -> None:
        base = self.ids.backend_url.text.strip().rstrip("/")
        while not self._stop_event.is_set():
            payload = {
                "session_id": self.session_id,
                "device_id": self.device_id,
                "device_name": self.ids.device_name.text.strip() or self.device_name,
                "role": "phone",
                "latency_ms": 35,
                "rssi_dbm": -55,
                "battery_pct": None,
                "network": {
                    "local_ip": self._safe_local_ip(),
                    "public_ip": None,
                    "wifi_ssid": None,
                    "wifi_bssid": None,
                    "transport": "wifi_or_hotspot",
                },
            }
            try:
                response = self._http.post(f"{base}/api/v1/heartbeat", json=payload, timeout=8)
                response.raise_for_status()
                prox = response.json().get("proximity", {})
                self._set_status(f"{prox.get('status')} | score={prox.get('score')}")
            except requests.RequestException as exc:
                self._set_status(f"Heartbeat failed: {exc}")
            time.sleep(5)

    def _set_status(self, text: str) -> None:
        Clock.schedule_once(lambda *_: setattr(self, "status_text", text), 0)


class PhoneProximityApp(App):
    def build(self):
        Builder.load_string(KV)
        return RootLayout()


if __name__ == "__main__":
    PhoneProximityApp().run()
