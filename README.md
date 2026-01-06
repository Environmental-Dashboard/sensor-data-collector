# Sensor Data Collector

A system for collecting environmental sensor data and uploading it to the cloud.

**Live Dashboard:** https://ed-sensor-dashboard.vercel.app

---

## Supported Sensors

| Sensor Type | Status | Description |
|-------------|--------|-------------|
| **Purple Air** | Ready | Air quality monitoring (PM2.5, temperature, humidity) |
| **Tempest** | Ready | Weather station (temp, wind, rain, UV, lightning) |
| **Water Quality** | Coming Soon | Water quality monitoring |
| **DO Sensor** | Coming Soon | Dissolved oxygen monitoring |

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

Set the tunnel URL in Vercel environment variables.

---

## Auto-Start on Boot

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

**To stop:** Open Task Manager and End `python.exe` and `cloudflared.exe`

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
    └── vercel.json            # Vercel config
```

---

## Deploying Frontend to Vercel

### Deploy Changes

```powershell
cd frontend
npm run build          # Build locally first to check for errors
vercel --prod          # Deploy to production
vercel alias set <deployment-url> ed-sensor-dashboard.vercel.app
```

### Set Backend URL

```powershell
cd frontend
vercel env rm VITE_API_URL production -y
echo "https://your-tunnel-url.trycloudflare.com" | vercel env add VITE_API_URL production
vercel --prod
```

Note: The auto-start scripts handle this automatically!

---

## Troubleshooting

### Dashboard shows Disconnected

1. Is backend running? `curl http://localhost:8000/health`
2. Is tunnel running? Check Task Manager for `cloudflared`
3. Is `VITE_API_URL` correct? Check Vercel env vars
4. Clear browser cache: `Ctrl + Shift + R`

### Sensor shows Error

- Can backend reach sensor? `curl http://<sensor-ip>/json`
- Is sensor on same network as backend computer?

---

## API Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/api/sensors/` | GET | List all sensors |
| `/api/sensors/purple-air` | POST | Add Purple Air sensor |
| `/api/sensors/tempest` | POST | Add Tempest sensor |
| `/api/sensors/{id}` | DELETE | Delete sensor |
| `/api/sensors/{id}/turn-on` | POST | Start polling |
| `/api/sensors/{id}/turn-off` | POST | Stop polling |
| `/api/sensors/{id}/fetch-now` | POST | Manual fetch |

**Full API docs:** http://localhost:8000/docs

---

## Credits

- Frank Kusi Appiah
- Environmental Dashboard Project
