# Sensor Data Collector (plain-English guide)

Short version: this box talks to local sensors, turns their JSON into CSV, and ships it to `oberlin.communityhub.cloud` every minute. The React dashboard sits on top and just calls the API.

## What this project does
- Polls sensors on the local network (Purple Air + Tempest today; Water Quality + Mayfly later)
- Converts each reading to a clean CSV
- Pushes CSVs straight to the cloud endpoint (no local storage)
- Lets you add, turn on/off, fetch-now, and delete sensors through an API and dashboard

## How it fits together
- Frontend: React dashboard (tabs per sensor type, Air Quality opens first)
- Access path: Frontend → Cloudflare Tunnel URL → FastAPI backend on your machine
- Backend: FastAPI + APScheduler (polls every 60s) + httpx (sensor calls) + Pydantic (validation)
- Uploads: CSV to `https://oberlin.communityhub.cloud/api/data-hub/upload/csv` using the per-sensor token you supply

## The flow (in plain words)
- You host the React dashboard (Vercel/Netlify/etc.). It only calls the backend URL you give it.
- You run the FastAPI backend on a local machine that can reach the sensors by LAN IP.
- You expose that local backend to the hosted frontend with a Cloudflare Tunnel URL.
- When you add a sensor in the UI, the backend stores its config (IP, name, location, upload token).
- When you turn a sensor on, the backend schedules a 60s job: fetch JSON from the sensor’s local IP, turn it into CSV, then POST it to `oberlin.communityhub.cloud/api/data-hub/upload/csv` with the token you provided for that sensor.
- “Fetch now” runs the same pipeline immediately (one-off) so you can test connectivity and uploads.

## Repo map (human edition)
```
backend/                    Python FastAPI app
  app/
    main.py                 Starts the API and scheduler
    models/sensor.py        Pydantic models for sensors and readings
    services/
      sensor_manager.py     In-memory sensor registry + polling jobs
      purple_air_service.py Fetch/CSV/upload for Purple Air
      tempest_service.py    Fetch/CSV/upload for Tempest
    routers/sensors.py      All API routes for sensors
  requirements.txt          Python deps

frontend/                   React dashboard (already built)
  src/App.tsx               UI with tabs (Air/Weather/Water/Mayfly)
  src/api.ts                API client
  src/types.ts              Shared types
  src/index.css             White/light theme
  FRONTEND_REQUIREMENTS.md  Friendly handoff for the frontend dev
```

## Supported sensors
- Purple Air: working (poll + upload)
- Tempest: working (poll + upload)
- Water Quality: coming soon
- Mayfly: coming soon

## Setup in 5 minutes (backend)
```bash
cd backend
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
Check it: open http://localhost:8000/docs

## Add a sensor (examples)
Purple Air:
```bash
curl -X POST http://localhost:8000/api/sensors/purple-air \
  -H "Content-Type: application/json" \
  -d '{
    "ip_address": "10.17.192.162",
    "name": "Lab Sensor",
    "location": "Science Building",
    "upload_token": "your-cloud-token"
  }'
```
Tempest:
```bash
curl -X POST http://localhost:8000/api/sensors/tempest \
  -H "Content-Type: application/json" \
  -d '{
    "ip_address": "192.168.1.150",
    "name": "Campus Weather",
    "location": "Rooftop",
    "device_id": "12345",
    "upload_token": "your-cloud-token"
  }'
```

## Daily use
- Turn on: `POST /api/sensors/{id}/turn-on` (starts 60s polling + uploads)
- Turn off: `POST /api/sensors/{id}/turn-off` (stops polling)
- Fetch now: `POST /api/sensors/{id}/fetch-now` (one-shot pull + upload, good for testing)
- Status: `GET /api/sensors/{id}/status`
- List: `GET /api/sensors/`
- Delete: `DELETE /api/sensors/{id}`
- Health: `GET /health`

## CSV shape (what we upload)
Purple Air (example):
```
Timestamp,Temperature (F),Humidity (%),Dewpoint (F),Pressure (hPa),PM1.0,PM2.5,PM10,AQI
2026-01-06T03:00:00Z,72,45,52,1013,5.2,12.4,18.7,52
```
Tempest (example):
```
Timestamp,Temperature (F),Humidity (%),Pressure (mb),Wind Speed (mph),Wind Gust (mph),Wind Dir (deg),Rain (in),UV,Solar (W/m2),Lightning
2026-01-06T03:00:00Z,72,45,1013,5.2,8.1,180,0.0,3.5,450,0
```

## Environment
Create `backend/.env` (keys shown with sensible defaults):
```
POLLING_INTERVAL=60
FRONTEND_URL=https://your-frontend.vercel.app
```

## If the frontend is remote
- Run backend locally as usual.
- Expose it with Cloudflare Tunnel:
  ```bash
  cloudflared tunnel --url http://localhost:8000
  ```
- Use the tunnel URL in the frontend `VITE_API_URL`.

## Troubleshooting (fast checks)
- Backend up? `curl http://localhost:8000/health`
- Sensor reachable? `curl http://<sensor-ip>/json`
- Upload token correct? If uploads fail, confirm the token in the sensor config.
- Interval stuck? Turn off then on: `POST /api/sensors/{id}/turn-off` then `turn-on`.

## Where to look in code
- API layer: `backend/app/routers/sensors.py`
- Orchestration + scheduler: `backend/app/services/sensor_manager.py`
- Device-specific logic: `backend/app/services/purple_air_service.py`, `.../tempest_service.py`
- Models: `backend/app/models/sensor.py`

## Frontend handoff
See `frontend/FRONTEND_REQUIREMENTS.md` for the friendly playbook (API calls, expected UI, and testing checklist).

## Credits
- Frank Kusi Appiah
