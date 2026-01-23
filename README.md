# Sensor Data Collector

A system for collecting environmental sensor data and uploading it to the cloud.

**Live Dashboard:** https://ed-sensor-dashboard.vercel.app

---

## Supported Sensors

| Sensor Type | Status | Description |
|-------------|--------|-------------|
| **Purple Air** | ✅ Ready | Air quality monitoring (PM2.5, temperature, humidity) |
| **Tempest** | ✅ Ready | Weather station (temp, wind, rain, UV, lightning) |
| **Water Quality** | ✅ Ready | Water quality monitoring via Ubidots |
| **DO Sensor** | 🚧 Coming Soon | Dissolved oxygen monitoring |

---

## How It Works

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         YOUR LOCAL COMPUTER                              │
│                                                                          │
│  ┌──────────────┐     ┌─────────────────────────────────────────────┐   │
│  │   Sensors    │     │              Backend (FastAPI)               │   │
│  │              │     │                                              │   │
│  │ Purple Air   │────▶│  • Purple Air: Polls every 60s              │   │
│  │ (Air Quality)│     │  • Tempest: Real-time via WebSocket         │   │
│  │              │     │  • Converts to CSV                          │   │
│  │              │     │  • Uploads to oberlin.communityhub.cloud    │   │
│  └──────────────┘     │                                              │   │
│                       │  Runs on: http://localhost:8000              │   │
│                       └──────────────────┬──────────────────────────┘   │
│                                          │                               │
│                                          │                               │
│  ┌──────────────┐                        │                               │
│  │ WeatherFlow  │◀───WebSocket───────────┤                               │
│  │ Cloud API    │   (Real-time data)     │                               │
│  │              │                        │                               │
│  │ Tempest      │                        │                               │
│  │ (Weather)    │                        │                               │
│  └──────────────┘                        │                               │
│                                          │                               │
│                       ┌──────────────────▼──────────────────┐           │
│                       │       Cloudflare Tunnel              │           │
│                       │  (Exposes localhost to internet)     │           │
│                       │                                      │           │
│                       │  Creates URL like:                   │           │
│                       │  https://xxx-xxx-xxx.trycloudflare.com│          │
│                       └──────────────────┬──────────────────┘           │
└──────────────────────────────────────────┼──────────────────────────────┘
                                           │
                                           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                              INTERNET                                    │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                    Frontend (Vercel)                             │    │
│  │                                                                  │    │
│  │  https://ed-sensor-dashboard.vercel.app                          │    │
│  │                                                                  │    │
│  │  - Shows sensor status                                           │    │
│  │  - Add/remove sensors                                            │    │
│  │  - Turn sensors on/off                                           │    │
│  │  - Manual data fetch (Purple Air only)                           │    │
│  │                                                                  │    │
│  │  Connects to backend via Cloudflare Tunnel URL                   │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │               oberlin.communityhub.cloud                         │    │
│  │                                                                  │    │
│  │  - Receives CSV data uploads                                     │    │
│  │  - Stores sensor readings                                        │    │
│  └─────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
```

### Summary
1. **Backend** runs on your local computer (where sensors are accessible)
2. **Cloudflare Tunnel** exposes the backend to the internet (no port forwarding needed)
3. **Frontend** is hosted on Vercel and connects to backend via the tunnel
4. **Data** is uploaded to `oberlin.communityhub.cloud`

---

## Adding Sensors

### Purple Air (Air Quality)

**What you need:**
- **IP Address**: Local network IP of your Purple Air sensor
- **Upload Token**: Get from `oberlin.communityhub.cloud`

**How it works:** Backend polls the sensor every 60 seconds via local network.

### Tempest (Weather Station)

**What you need:**
- **Device ID**: Find in WeatherFlow app under station settings (e.g., `205498`)
- **Location**: Where the station is physically located
- **Upload Token**: Get from `oberlin.communityhub.cloud`

**Note:** The WeatherFlow API token is configured in the backend (`TEMPEST_API_TOKEN` in `main.py`). One token works for ALL Tempest devices.

**How it works:** 
- Connects to WeatherFlow cloud via WebSocket
- Receives real-time data automatically when Tempest broadcasts
- Uploads immediately to Community Hub
- Shows battery voltage on dashboard

**API Documentation:** [weatherflow.github.io/Tempest/api/](https://weatherflow.github.io/Tempest/api/)

### Water Quality (Ubidots)

**What you need:**
- **Device ID**: 24-character hex ID from Ubidots
- **Ubidots Token**: Starts with `BBUS-`, get from Ubidots dashboard
- **Upload Token**: Get from `oberlin.communityhub.cloud`

---

## Quick Start

### 1. Start the Backend

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --port 8000 --reload
```

The `--reload` flag enables auto-refresh when you edit Python files.

### 2. Start Cloudflare Tunnel

```powershell
cloudflared tunnel --url http://localhost:8000
```

This gives you a URL like `https://random-words.trycloudflare.com`

### 3. Update Frontend with Tunnel URL

Set the tunnel URL in Vercel environment variables (see "Deploying Frontend" below).

---

## Auto-Start on Boot

The system can start automatically when your computer boots:

### Setup Auto-Start

1. Press `Win + R`, type `shell:startup`, press Enter
2. Create a shortcut to `backend\start-hidden.vbs` in this folder
3. Done! Backend and tunnel will start hidden on boot

### What Happens on Boot

1. `start-hidden.vbs` runs silently
2. Starts the backend (waits 8 seconds)
3. Starts the Cloudflare tunnel
4. Captures the new tunnel URL
5. Updates Vercel's `VITE_API_URL` environment variable
6. Triggers a Vercel redeployment
7. Sets the `ed-sensor-dashboard.vercel.app` alias

### Manual Hidden Start

Double-click `backend/start-hidden.vbs` to run both backend and tunnel in the background.

**To stop:** Open Task Manager → End `python.exe` and `cloudflared.exe`

### Check Logs

If something isn't working, check these log files in the `backend/` folder:
- `startup.log` - When startup scripts ran
- `backend.log` - Backend server output
- `tunnel.log` - Tunnel and Vercel deployment logs

---

## Project Structure

```
sensor_data_collector/
├── backend/                    # Python FastAPI (runs locally)
│   ├── app/
│   │   ├── main.py            # App entry, CORS config
│   │   ├── models/            # Data models (sensor.py)
│   │   ├── routers/           # API endpoints (sensors.py)
│   │   └── services/          # Business logic
│   │       ├── sensor_manager.py      # Orchestrates all sensors
│   │       ├── purple_air_service.py  # Purple Air API
│   │       └── tempest_service.py     # Tempest API
│   ├── requirements.txt
│   ├── start-backend.ps1      # Start backend (with auto-reload)
│   ├── start-tunnel.ps1       # Start tunnel + update Vercel
│   └── start-hidden.vbs       # Start both hidden (for auto-start)
│
└── frontend/                   # React app (hosted on Vercel)
    ├── src/
    │   ├── App.tsx            # Main UI, tabs, sensor cards
    │   ├── api.ts             # API client functions
    │   ├── types.ts           # TypeScript interfaces
    │   └── index.css          # All styling
    ├── vercel.json            # Vercel config
    └── package.json
```

---

## Deploying Frontend to Vercel

### First Time Setup

1. Install Vercel CLI:
   ```powershell
   npm install -g vercel
   ```

2. Login to Vercel:
   ```powershell
   vercel login
   ```

3. Link the project (run from `frontend/` folder):
   ```powershell
   cd frontend
   vercel link
   ```

### Deploy Changes

After making changes to the frontend:

```powershell
cd frontend
npm run build          # Build locally first to check for errors
vercel --prod          # Deploy to production
vercel alias set <deployment-url> ed-sensor-dashboard.vercel.app
```

### Set Backend URL (Environment Variable)

The frontend needs to know where the backend is. Set this in Vercel:

**Option 1: Via Vercel Dashboard**
1. Go to https://vercel.com → Your Project → Settings → Environment Variables
2. Add: `VITE_API_URL` = `https://your-tunnel-url.trycloudflare.com`
3. Redeploy

**Option 2: Via CLI**
```powershell
cd frontend
vercel env rm VITE_API_URL production -y
echo "https://your-tunnel-url.trycloudflare.com" | vercel env add VITE_API_URL production
vercel --prod  # Redeploy
```

> **Note:** The auto-start scripts handle this automatically when the tunnel URL changes!

---

## Making Changes

### Frontend Changes

1. Edit files in `frontend/src/`
2. Test locally:
   ```powershell
   cd frontend
   npm run dev
   ```
3. Deploy:
   ```powershell
   npm run build
   vercel --prod
   vercel alias set <deployment-url> ed-sensor-dashboard.vercel.app
   ```

**Key files:**
| File | Purpose |
|------|---------|
| `App.tsx` | Main UI component, tabs, sensor cards, modals |
| `api.ts` | API calls to backend |
| `index.css` | All styling |
| `types.ts` | TypeScript interfaces |

### Backend Changes

1. Edit files in `backend/app/`
2. Backend auto-reloads when using `--reload` flag (default in startup scripts)

**Key files:**
| File | Purpose |
|------|---------|
| `main.py` | CORS config, app startup |
| `routers/sensors.py` | API endpoints |
| `services/sensor_manager.py` | Sensor orchestration, scheduling |
| `services/purple_air_service.py` | Purple Air data fetching |
| `services/tempest_service.py` | Tempest data fetching |
| `models/sensor.py` | Data models and types |

---

## Troubleshooting

### Dashboard shows "Disconnected"

1. **Is backend running?**
   ```powershell
   curl http://localhost:8000/health
   ```
   Should return: `{"status":"healthy","polling_interval":60}`

2. **Is tunnel running?**
   - Check if `cloudflared` process is active in Task Manager
   - Try the tunnel URL directly in browser

3. **Is `VITE_API_URL` correct?**
   - Check Vercel environment variables
   - Must match your current tunnel URL
   - Redeploy after changing

4. **Browser cache?**
   - Hard refresh: `Ctrl + Shift + R`
   - Or try incognito window

### Sensor shows "Error"

- Can backend reach sensor? Try: `curl http://<sensor-ip>/json`
- Is sensor on same network as backend computer?
- Check `backend.log` for error details

### Sensor shows "Low Battery" (Yellow Warning)

This is **not an error** - it's an expected state when the battery voltage drops below the cutoff threshold:
- The voltage meter automatically powered off the sensor to protect the battery
- Sensor will resume when battery recovers above the reconnect threshold
- Check battery voltage on the sensor card

### Sensor shows "Cloud Issue" (Purple Badge)

Community Hub may be temporarily unavailable:
- The system automatically retries uploads once before reporting this error
- Data collection from the sensor is still working
- Uploads will resume automatically when Community Hub is back online
- This is not your sensor's fault - just a temporary cloud service issue

### Backend won't start (port in use)

The startup scripts automatically kill existing processes, but if needed:
```powershell
# Find process using port 8000
Get-NetTCPConnection -LocalPort 8000 | Select-Object OwningProcess
# Kill it
Stop-Process -Id <PID> -Force
```

### Changes not showing on dashboard

1. Did you run `vercel --prod`?
2. Did you set the alias? `vercel alias set <url> ed-sensor-dashboard.vercel.app`
3. Clear browser cache
4. Check Vercel deployment logs

### Data not uploading to Community Hub

**Symptoms:** Sensors show as "active" but no data appears in Community Hub data sources.

1. **Test upload endpoint connectivity:**
   ```powershell
   curl "http://localhost:8000/api/sensors/health/upload-test?upload_token=YOUR_TOKEN"
   ```
   This tests if the backend can reach Community Hub and if your token is valid.

2. **Check sensor diagnostics:**
   ```powershell
   curl "http://localhost:8000/api/sensors/{sensor_id}/diagnostics"
   ```
   Returns:
   - Last upload attempt timestamp
   - Last error details (HTTP status, error response)
   - Last CSV sample sent
   - Connectivity status (for Purple Air)

3. **Check backend logs:**
   - Look for `[SensorName] Uploading CSV` messages
   - Check for HTTP error responses
   - Verify CSV format matches Community Hub expectations

4. **Common issues:**
   - **Invalid token**: Token may have expired or been revoked
   - **CSV format mismatch**: Headers must match exactly what Community Hub expects
   - **Network connectivity**: Backend cannot reach `oberlin.communityhub.cloud`
   - **Empty CSV**: Sensor returned no data (check sensor connectivity)

5. **Verify CSV format:**
   - Each sensor type has a specific CSV format
   - Headers must match exactly (case-sensitive)
   - Timestamp must be ISO 8601 UTC format
   - See `backend/CSV_FORMAT.md` for details

### Viewing Logs

**Backend logs:**
- Check `backend/backend.log` for detailed error messages
- Logs include CSV previews, HTTP responses, and error details
- Log level can be adjusted in `main.py`

**Tunnel logs:**
- Check `backend/tunnel.log` for Cloudflare Tunnel issues
- Shows connection status and URL changes

### Manual Upload Test

Test uploading a CSV file directly:
```powershell
# Create a test CSV file
$csv = "Timestamp,Temperature (°F),Humidity (%)\n2026-01-01T00:00:00+00:00,72.0,45.0"
$csv | Out-File -FilePath test.csv -Encoding utf8

# Upload it
curl -X POST "https://oberlin.communityhub.cloud/api/data-hub/upload/csv" `
  -H "user-token: YOUR_TOKEN" `
  -F "file=@test.csv"
```

### Token Management

**Getting tokens:**
- Contact Community Hub team (Gaurav/Pratush) for upload tokens
- Tokens are used to authenticate CSV uploads
- Each sensor needs a unique token (or tokens can be reused)

**Token format:**
- Tokens look like: `8GJKOVeWT6aOXdWGv4udVP8uGIFOCi`
- Sent in `user-token` header (not `Authorization: Bearer`)

**Testing token validity:**
- Use `/api/sensors/health/upload-test?upload_token=YOUR_TOKEN`
- Returns success if token is valid and endpoint is reachable

---

## API Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/api/sensors/` | GET | List all sensors |
| `/api/sensors/purple-air` | GET | List Purple Air sensors |
| `/api/sensors/purple-air` | POST | Add Purple Air sensor |
| `/api/sensors/tempest` | GET | List Tempest sensors |
| `/api/sensors/tempest` | POST | Add Tempest sensor |
| `/api/sensors/water-quality` | GET | List Water Quality sensors |
| `/api/sensors/do-sensor` | GET | List DO sensors |
| `/api/sensors/{id}` | GET | Get single sensor |
| `/api/sensors/{id}` | DELETE | Delete sensor |
| `/api/sensors/{id}/turn-on` | POST | Start polling |
| `/api/sensors/{id}/turn-off` | POST | Stop polling |
| `/api/sensors/{id}/fetch-now` | POST | Manual fetch |
| `/api/sensors/{id}/diagnostics` | GET | Get sensor diagnostics |
| `/api/sensors/health/upload-test` | GET | Test upload endpoint |

**Full API docs:** http://localhost:8000/docs (when backend is running)

---

## Adding a New Sensor Type

To add support for a new sensor type:

1. **Backend:**
   - Add enum value in `models/sensor.py` → `SensorType`
   - Create request model `AddXxxSensorRequest`
   - Create service in `services/xxx_service.py`
   - Add endpoints in `routers/sensors.py`
   - Update `sensor_manager.py` to handle the new type

2. **Frontend:**
   - Add type to `types.ts` → `SensorType`
   - Add tab in `App.tsx` → `tabs` array
   - Add API function in `api.ts`
   - Update `isImplemented` check in `App.tsx`

---

## Credits

- Frank Kusi Appiah
- Menard Simoya
