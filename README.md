# Sensor Data Collector

A system for collecting environmental sensor data and uploading it to the cloud.

**Live Dashboard:** https://ed-sensor-dashboard.vercel.app

---

## How It Works

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         YOUR LOCAL COMPUTER                              │
│                                                                          │
│  ┌──────────────┐     ┌─────────────────────────────────────────────┐   │
│  │   Sensors    │     │              Backend (FastAPI)               │   │
│  │              │     │                                              │   │
│  │ Purple Air   │────▶│  1. Fetches data from sensors every 60s     │   │
│  │ (Air Quality)│     │  2. Converts to CSV                         │   │
│  │              │     │  3. Uploads to oberlin.communityhub.cloud   │   │
│  │ Tempest      │────▶│                                              │   │
│  │ (Weather)    │     │  Runs on: http://localhost:8000              │   │
│  └──────────────┘     └──────────────────┬──────────────────────────┘   │
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
│  │  https://ed-sensors-dashboard.vercel.app                         │    │
│  │                                                                  │    │
│  │  - Shows sensor status                                           │    │
│  │  - Add/remove sensors                                            │    │
│  │  - Turn sensors on/off                                           │    │
│  │  - Manual data fetch                                             │    │
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

## Quick Start

### 1. Start the Backend

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --port 8000
```

### 2. Start Cloudflare Tunnel

```powershell
cloudflared tunnel --url http://localhost:8000
```

This gives you a URL like `https://random-words.trycloudflare.com`

### 3. Update Frontend with Tunnel URL

Set the tunnel URL in Vercel environment variables (see "Deploying Frontend" below).

---

## Running Without Terminal Windows

Double-click `backend/start-hidden.vbs` to run both backend and tunnel in the background.

**To stop:** Open Task Manager → End `python.exe` and `cloudflared.exe`

---

## Project Structure

```
sensor_data_collector/
├── backend/                    # Python FastAPI (runs locally)
│   ├── app/
│   │   ├── main.py            # App entry, CORS config
│   │   ├── models/            # Data models
│   │   ├── routers/           # API endpoints
│   │   └── services/          # Business logic
│   ├── requirements.txt
│   ├── start-backend.ps1      # Start backend
│   ├── start-tunnel.ps1       # Start tunnel
│   └── start-hidden.vbs       # Start both hidden
│
└── frontend/                   # React app (hosted on Vercel)
    ├── src/
    │   ├── App.tsx            # Main UI
    │   ├── api.ts             # API client
    │   ├── types.ts           # TypeScript types
    │   └── index.css          # Styles
    └── vercel.json
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
```

### Set Backend URL (Environment Variable)

The frontend needs to know where the backend is. Set this in Vercel:

**Option 1: Via Vercel Dashboard**
1. Go to https://vercel.com → Your Project → Settings → Environment Variables
2. Add: `VITE_API_URL` = `https://your-tunnel-url.trycloudflare.com`
3. Redeploy

**Option 2: Via CLI**
```powershell
vercel env add VITE_API_URL production
# Enter your tunnel URL when prompted
vercel --prod  # Redeploy
```

### Custom Domain Alias

To use a custom subdomain like `ed-sensors-dashboard.vercel.app`:

```powershell
vercel alias set <deployment-url> ed-sensors-dashboard.vercel.app
```

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
   ```

**Key files:**
| File | Purpose |
|------|---------|
| `App.tsx` | Main UI component, tabs, modals |
| `api.ts` | API calls to backend |
| `index.css` | All styling (light/dark mode) |
| `types.ts` | TypeScript interfaces |

### Backend Changes

1. Edit files in `backend/app/`
2. Restart uvicorn (auto-reloads if using `--reload`)

**Key files:**
| File | Purpose |
|------|---------|
| `main.py` | CORS config, startup |
| `routers/sensors.py` | API endpoints |
| `services/sensor_manager.py` | Sensor orchestration |
| `services/purple_air_service.py` | Purple Air logic |
| `services/tempest_service.py` | Tempest logic |

---

## Troubleshooting

### Dashboard shows "Disconnected"

1. **Is backend running?**
   ```powershell
   curl http://localhost:8000/health
   ```

2. **Is tunnel running?**
   - Check if `cloudflared` process is active
   - Try the tunnel URL in browser

3. **Is `VITE_API_URL` correct?**
   - Check Vercel environment variables
   - Must match your current tunnel URL
   - Redeploy after changing

### Sensor shows "Error"

- Can backend reach sensor? `curl http://<sensor-ip>/json`
- Is sensor on same network as backend computer?

### Changes not showing on dashboard

- Did you run `vercel --prod`?
- Clear browser cache
- Check Vercel deployment logs

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

Full API docs: `http://localhost:8000/docs`

---

## Credits

- Frank Kusi Appiah
