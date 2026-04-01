#include <stdint.h>

extern int abs_int_diff(int a, int b);

int proximity_penalty(int latency_ms, int rssi_dbm) {
    if (latency_ms < 0) {
        latency_ms = 0;
    }

    int latency_penalty = latency_ms / 5;
    int rssi_penalty = abs_int_diff(rssi_dbm, -45);
    return latency_penalty + rssi_penalty;
}
