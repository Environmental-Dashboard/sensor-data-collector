# Frontend playbook (human version)

Goal: ship a clean dashboard that calls the backend. Backend already works; your job is API calls + UI polish.

## What the UI should cover
- Tabs per sensor type. Air Quality opens by default; Weather, Water Quality, Mayfly are next tabs.
- For Purple Air and Tempest: list sensors, add, turn on/off, fetch now, delete.
- Show connection badge from `/health` (poll ~30s).
- Show active/total counts per tab and “last active” as relative time.
- Water Quality and Mayfly: just show “Coming soon” for now.

## How to talk to the backend
- Base URL (local): `http://localhost:8000`
- Put it in `VITE_API_URL` so you can swap in a tunnel URL later.
- Key endpoints:
  - `GET /health` — ping for the badge
  - `GET /api/sensors/` — list all
  - `POST /api/sensors/purple-air` — add Purple Air
  - `POST /api/sensors/tempest` — add Tempest
  - `POST /api/sensors/{id}/turn-on` — start polling/uploads
  - `POST /api/sensors/{id}/turn-off` — stop polling
  - `POST /api/sensors/{id}/fetch-now` — one-shot pull + upload
  - `GET /api/sensors/{id}/status` — current state
  - `DELETE /api/sensors/{id}` — remove (confirm first)

## Payloads you’ll send
Purple Air add:
```json
{
  "ip_address": "10.17.192.162",
  "name": "Lab Sensor",
  "location": "Science Building Room 201",
  "upload_token": "user-cloud-token"
}
```
Tempest add (includes device_id):
```json
{
  "ip_address": "192.168.1.150",
  "name": "Campus Weather",
  "location": "Rooftop",
  "device_id": "12345",
  "upload_token": "user-cloud-token"
}
```

## Types (mirror the backend)
```typescript
type SensorType = 'purple_air' | 'tempest' | 'water_quality' | 'mayfly';
type SensorStatus = 'active' | 'inactive' | 'error' | 'offline';

interface Sensor {
  id: string;
  sensor_type: SensorType;
  name: string;
  location: string;
  ip_address: string | null;
  device_id: string | null; // Tempest only
  status: SensorStatus;
  is_active: boolean;
  last_active: string | null;
  last_error: string | null;
  created_at: string;
}

interface SensorListResponse {
  sensors: Sensor[];
  total: number;
}

interface AddPurpleAirRequest {
  ip_address: string;
  name: string;
  location: string;
  upload_token: string;
}

interface AddTempestRequest extends AddPurpleAirRequest {
  device_id: string;
}
```

## UX expectations
- Show loading states for all calls; disable buttons while waiting.
- Confirm before delete.
- Surface backend error messages directly.
- Format times as “2m ago” instead of raw ISO.
- Don’t display upload tokens after creation.
- Non-implemented tabs stay in “Coming soon.”

## Local dev loop
1) Start backend
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
2) Start frontend
```bash
cd frontend
npm install
npm run dev
```
3) In the UI: add a Purple Air sensor (use the sample IP), turn it on, hit Fetch Now, check status, then delete it.

## Remote access note
If the backend stays on a local network but the UI is hosted, expose it with Cloudflare Tunnel and point `VITE_API_URL` to the tunnel URL.

## Where the key frontend code lives
- `src/App.tsx` — tabs and dashboard
- `src/api.ts` — API client
- `src/types.ts` — shared types
- `src/index.css` — white/light theme

That’s the playbook. Keep it straightforward and friendly. If anything feels off, hit `http://localhost:8000/docs` to see the live request/response shapes.
