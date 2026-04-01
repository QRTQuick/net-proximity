# Net Proximity (Flask + Vercel + Kivy Starter)

This project now includes:

- Flask backend API (Vercel-ready)
- Desktop heartbeat client (`proximity_app.py`)
- Kivy mobile starter app (`mobile/kivy_phone_app.py`)
- Optional native accelerator (C + Assembly) for signal scoring (`native/`)

## 1) Backend Setup (Local)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 -m flask --app backend.app:create_app run --debug
```

Health check:

```bash
curl http://127.0.0.1:5000/api/health
```

## 2) Backend API Flow

1. Desktop creates a session:

```bash
curl -X POST http://127.0.0.1:5000/api/v1/sessions \
  -H "Content-Type: application/json" \
  -d '{"device_id":"desktop-1","device_name":"My PC","role":"desktop"}'
```

2. Phone joins session with `pair_code`:

```bash
curl -X POST http://127.0.0.1:5000/api/v1/sessions/join \
  -H "Content-Type: application/json" \
  -d '{"pair_code":"123456","device_id":"phone-1","device_name":"My Phone","role":"phone"}'
```

3. Send heartbeat:

```bash
curl -X POST http://127.0.0.1:5000/api/v1/heartbeat \
  -H "Content-Type: application/json" \
  -d '{"session_id":"<session_id>","device_id":"desktop-1","role":"desktop","network":{"local_ip":"192.168.1.22","wifi_ssid":"HomeNet","wifi_bssid":"AA:BB:CC:DD:EE:FF"}}'
```

4. Read computed proximity:

```bash
curl http://127.0.0.1:5000/api/v1/sessions/<session_id>/status
```

## 3) Desktop Client

Create session from desktop:

```bash
python3 proximity_app.py --backend-url http://127.0.0.1:5000 --mode desktop --device-id desktop-1
```

Join from phone mode (CLI):

```bash
python3 proximity_app.py --backend-url http://127.0.0.1:5000 --mode phone --pair-code <pair_code> --device-id phone-1
```

## 4) Kivy Mobile App

```bash
pip install -r requirements-mobile.txt
python3 mobile/kivy_phone_app.py
```

## 5) Optional Native C + Assembly Build

```bash
./native/build.sh
```

This builds `native/libproxmath.so`. The backend will automatically use it if present; otherwise it falls back to Python logic.

## 6) Deploy to Vercel

`vercel.json` is included and routes all traffic to `api/index.py`.

Set optional environment variables:

- `API_KEY` (if you want authenticated API calls)
- `OFFLINE_AFTER_SECONDS` (default `45`)
- `SESSION_MAX_HOURS` (default `24`)

## Notes

- Proximity is a network heuristic. On Wi-Fi/hotspot/internet it is approximate, not true meter-level distance.
- For production persistence on Vercel, add an external datastore (Redis/Postgres). Current store is in-memory.
