# Sensor Data Collector

A system for collecting environmental sensor data and uploading it to the cloud.

**Live Dashboard:** https://ed-sensors-dashboard.vercel.app

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

```bash
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1   # Windows
pip install -r requirements.txt
uvicorn app.main:app --port 8000
```

### 2. Start Cloudflare Tunnel

```bash
cloudflared tunnel --url http://localhost:8000
```

This gives you a URL like `https://random-words.trycloudflare.com`

### 3. Update Frontend Environment

Set the tunnel URL in Vercel:
1. Go to [Vercel Dashboard](https://vercel.com) → Your Project → Settings → Environment Variables
2. Set `VITE_API_URL` to your tunnel URL
3. Redeploy

---

## Running Without Terminal Windows (Hidden Mode)

Double-click `backend/start-hidden.vbs` to run both backend and tunnel in the background.

To stop: Open Task Manager → End `python.exe` and `cloudflared.exe`

---

## Project Structure

```
sensor_data_collector/
├── backend/                    # Python FastAPI (runs locally)
│   ├── app/
│   │   ├── main.py            # App entry point, CORS config
│   │   ├── models/            # Data models (Pydantic)
│   │   ├── routers/           # API endpoints
│   │   └── services/          # Business logic
│   │       ├── sensor_manager.py      # Manages all sensors
│   │       ├── purple_air_service.py  # Purple Air logic
│   │       └── tempest_service.py     # Tempest logic
│   ├── requirements.txt
│   ├── start-backend.ps1      # Start backend
│   ├── start-tunnel.ps1       # Start tunnel
│   └── start-hidden.vbs       # Start both hidden
│
└── frontend/                   # React app (hosted on Vercel)
    ├── src/
    │   ├── App.tsx            # Main UI component
    │   ├── api.ts             # API client
    │   ├── types.ts           # TypeScript types
    │   └── index.css          # Styles
    ├── vercel.json            # Vercel config
    └── package.json
```

---

## Making Changes

### Frontend Changes

1. Edit files in `frontend/src/`
2. Test locally: `cd frontend && npm run dev`
3. Deploy: `cd frontend && npx vercel --prod`

**Key files:**
- `App.tsx` - UI components and logic
- `api.ts` - API calls to backend
- `index.css` - Styling (supports light/dark mode)
- `types.ts` - TypeScript interfaces

### Backend Changes

1. Edit files in `backend/app/`
2. Restart uvicorn (auto-reloads with `--reload` flag)

**Key files:**
- `main.py` - CORS origins, startup
- `routers/sensors.py` - API endpoints
- `services/sensor_manager.py` - Sensor logic
- `services/purple_air_service.py` - Purple Air specific

### Adding a New Sensor Type

1. Create `backend/app/services/new_sensor_service.py`
2. Add models in `backend/app/models/sensor.py`
3. Add routes in `backend/app/routers/sensors.py`
4. Update `sensor_manager.py` to handle the new type
5. Update frontend `App.tsx` modal form

---

## Troubleshooting

### Dashboard shows "Disconnected"
- Is the backend running? Check `http://localhost:8000/health`
- Is the tunnel running? Check if the tunnel URL works
- Is `VITE_API_URL` set correctly in Vercel?

### Sensor shows "Error"
- Can the backend reach the sensor? Try `curl http://<sensor-ip>/json`
- Is the sensor on the same network as the computer running the backend?

### Data not uploading
- Check the upload token is correct
- Check `oberlin.communityhub.cloud` is accessible

### Frontend won't load
- Clear browser cache
- Check browser console for errors
- Verify Vercel deployment succeeded

---

## API Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/api/sensors/` | GET | List all sensors |
| `/api/sensors/purple-air` | POST | Add Purple Air sensor |
| `/api/sensors/tempest` | POST | Add Tempest sensor |
| `/api/sensors/{id}` | GET | Get sensor details |
| `/api/sensors/{id}` | DELETE | Delete sensor |
| `/api/sensors/{id}/turn-on` | POST | Start polling |
| `/api/sensors/{id}/turn-off` | POST | Stop polling |
| `/api/sensors/{id}/fetch-now` | POST | Manual fetch |

Full docs at: `http://localhost:8000/docs`

---

## Credits

- Frank Kusi Appiah
