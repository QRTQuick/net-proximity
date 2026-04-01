from __future__ import annotations

import ctypes
from pathlib import Path


_LIB = None


def _load_library() -> ctypes.CDLL | None:
    global _LIB
    if _LIB is not None:
        return _LIB

    lib_path = Path(__file__).resolve().parent.parent / "native" / "libproxmath.so"
    if not lib_path.exists():
        _LIB = None
        return None

    try:
        loaded = ctypes.CDLL(str(lib_path))
        loaded.proximity_penalty.argtypes = [ctypes.c_int, ctypes.c_int]
        loaded.proximity_penalty.restype = ctypes.c_int
        _LIB = loaded
        return loaded
    except OSError:
        _LIB = None
        return None


def _python_penalty(latency_ms: int | None, rssi_dbm: int | None) -> int:
    latency = max(0, int(latency_ms or 0))
    rssi = int(rssi_dbm if rssi_dbm is not None else -60)
    rssi_target = -45
    rssi_penalty = abs(rssi - rssi_target)
    latency_penalty = latency // 5
    return latency_penalty + rssi_penalty


def signal_penalty(latency_ms: int | None, rssi_dbm: int | None) -> int:
    lib = _load_library()
    if lib is None:
        return _python_penalty(latency_ms, rssi_dbm)
    return int(lib.proximity_penalty(int(latency_ms or 0), int(rssi_dbm if rssi_dbm is not None else -60)))

