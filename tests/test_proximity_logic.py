import unittest

from backend.models import DeviceState, NetworkSnapshot, SessionState
from backend.proximity import calculate_proximity


class ProximityLogicTests(unittest.TestCase):
    def test_waiting_for_pair(self):
        session = SessionState(session_id="s1", pair_code="111111")
        session.devices["desktop-1"] = DeviceState(device_id="desktop-1", role="desktop")
        prox = calculate_proximity(session, offline_after_seconds=45)
        self.assertEqual(prox["status"], "waiting_for_pair")

    def test_close_when_same_wifi(self):
        session = SessionState(session_id="s2", pair_code="222222")
        desktop = DeviceState(device_id="desktop-1", role="desktop")
        phone = DeviceState(device_id="phone-1", role="phone")
        desktop.record_heartbeat(
            network=NetworkSnapshot(
                local_ip="192.168.1.10",
                public_ip="1.1.1.1",
                wifi_ssid="Office",
                wifi_bssid="aa:bb:cc:dd:ee:ff",
                transport="wifi",
            ),
            latency_ms=10,
            rssi_dbm=-45,
            battery_pct=90,
        )
        phone.record_heartbeat(
            network=NetworkSnapshot(
                local_ip="192.168.1.20",
                public_ip="1.1.1.1",
                wifi_ssid="Office",
                wifi_bssid="aa:bb:cc:dd:ee:ff",
                transport="wifi",
            ),
            latency_ms=10,
            rssi_dbm=-45,
            battery_pct=60,
        )
        session.devices["desktop-1"] = desktop
        session.devices["phone-1"] = phone

        prox = calculate_proximity(session, offline_after_seconds=45)
        self.assertIn(prox["status"], {"very_close", "close"})
        self.assertGreaterEqual(prox["score"], 70)


if __name__ == "__main__":
    unittest.main()
