# Sensor Data Collector 🌡️

Collect environmental sensor data and upload it to the cloud. Simple as that!

## What's This For?

We have sensors around campus measuring air quality and weather. This system:
1. Connects to those sensors (they're on our local network)
2. Grabs the data every 60 seconds
3. Converts it to CSV
4. Uploads it to oberlin.communityhub.cloud

## The Big Picture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│    YOU (using the dashboard)                                                 │
│       │                                                                      │
│       │ "Add sensor 10.17.192.162"                                          │
│       │ "Turn it on"                                                        │
│       ▼                                                                      │
│    ┌─────────────────────────────────────────────────────────────────────┐  │
│    │              FRONTEND (React Dashboard)                              │  │
│    │              Hosted on Vercel/Netlify                                │  │
│    └─────────────────────────────────────────────────────────────────────┘  │
│       │                                                                      │
│       │ HTTP requests                                                       │
│       ▼                                                                      │
│    ┌─────────────────────────────────────────────────────────────────────┐  │
│    │              CLOUDFLARE TUNNEL                                       │  │
│    │              (Makes local server accessible online)                  │  │
│    └─────────────────────────────────────────────────────────────────────┘  │
│       │                                                                      │
│       ▼                                                                      │
└───────┼─────────────────────────────────────────────────────────────────────┘
        │
        ▼   YOUR LOCAL NETWORK
┌───────────────────────────────────────────────────────────────────────────────┐
│                                                                                │
│    ┌────────────────────────────────────────────────────────────────────────┐ │
│    │              BACKEND (Python FastAPI)                                   │ │
│    │              Running on your computer                                   │ │
│    │                                                                         │ │
│    │   Every 60 seconds:                                                    │ │
│    │   1. Fetch JSON from sensor                                            │ │
│    │   2. Parse the data                                                    │ │
│    │   3. Convert to CSV                                                    │ │
│    │   4. Upload to cloud                                                   │ │
│    └────────────────────────────────────────────────────────────────────────┘ │
│         │                                  │                                   │
│         ▼                                  ▼                                   │
│    ┌──────────────┐                 ┌──────────────┐                          │
│    │ Purple Air   │                 │ Tempest      │                          │
│    │ Sensor       │                 │ Weather      │                          │
│    │              │                 │ Station      │                          │
│    │ 10.17.192.x  │                 │ 192.168.x.x  │                          │
│    └──────────────┘                 └──────────────┘                          │
│                                                                                │
└────────────────────────────────────────────────────────────────────────────────┘
        │
        │ CSV uploads
        ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│              CLOUD                                                             │
│              oberlin.communityhub.cloud/api/data-hub/upload/csv               │
└───────────────────────────────────────────────────────────────────────────────┘
```

## Project Structure - What Each File Does

```
sensor-data-collector/
│
├── README.md                   ← You're reading this!
│
├── backend/                    ← The Python server (DONE ✅)
│   │
│   ├── requirements.txt        ← Python packages we need
│   │
│   ├── app/
│   │   ├── __init__.py        ← Just marks this as a Python package
│   │   │
│   │   ├── main.py            ← THE MAIN FILE
│   │   │                         Creates the server, starts everything up
│   │   │
│   │   ├── models/            ← DATA STRUCTURES
│   │   │   ├── __init__.py
│   │   │   └── sensor.py      ← Defines what a "sensor" looks like
│   │   │                         What fields it has, how to validate data
│   │   │
│   │   ├── services/          ← THE WORKERS (do the actual work)
│   │   │   ├── __init__.py
│   │   │   ├── purple_air_service.py  ← Talks to Purple Air sensors
│   │   │   │                             Fetches data, converts to CSV
│   │   │   ├── tempest_service.py     ← Talks to Tempest weather stations
│   │   │   └── sensor_manager.py      ← THE BOSS
│   │   │                                 Manages all sensors, schedules polling
│   │   │
│   │   └── routers/           ← API ENDPOINTS (the doors into our app)
│   │       ├── __init__.py
│   │       └── sensors.py     ← All the /api/sensors/* endpoints
│   │                            Add, delete, turn on/off, etc.
│   │
│   └── .gitignore             ← Files Git should ignore
│
└── frontend/                   ← The React dashboard (TO BE BUILT)
    └── FRONTEND_REQUIREMENTS.md  ← Instructions for building the frontend
```

## Supported Sensors

| Sensor | Status | What It Measures |
|--------|--------|------------------|
| **Purple Air** | ✅ Working | PM1.0, PM2.5, PM10, Temperature, Humidity, Pressure, AQI |
| **Tempest** | ✅ Working | Temperature, Humidity, Wind, Rain, UV, Solar Radiation, Lightning |
| **Water Quality** | 🚧 Coming | TBD |
| **Mayfly** | 🚧 Coming | TBD |

## Quick Start

### 1. Set Up the Backend

```bash
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install packages
pip install -r requirements.txt

# Run the server
uvicorn app.main:app --reload --port 8000
```

### 2. Add a Sensor

```bash
curl -X POST http://localhost:8000/api/sensors/purple-air \
  -H "Content-Type: application/json" \
  -d '{
    "ip_address": "10.17.192.162",
    "name": "Lab Sensor",
    "location": "Science Building",
    "upload_token": "your-token-from-oberlin-communityhub"
  }'
```

### 3. Turn It On

```bash
# Use the ID from the previous response
curl -X POST http://localhost:8000/api/sensors/{sensor-id}/turn-on
```

### 4. Watch the Data Flow! 🎉

The sensor will now fetch data every 60 seconds and upload it to the cloud.

## API Reference

| What You Want | How To Do It |
|--------------|--------------|
| Add Purple Air sensor | `POST /api/sensors/purple-air` |
| Add Tempest sensor | `POST /api/sensors/tempest` |
| List all sensors | `GET /api/sensors/` |
| Get one sensor | `GET /api/sensors/{id}` |
| Turn on (start collecting) | `POST /api/sensors/{id}/turn-on` |
| Turn off (stop collecting) | `POST /api/sensors/{id}/turn-off` |
| Manual fetch (test) | `POST /api/sensors/{id}/fetch-now` |
| Get status | `GET /api/sensors/{id}/status` |
| Delete sensor | `DELETE /api/sensors/{id}` |
| Health check | `GET /health` |

## Adding a Sensor - What You Need

### Purple Air
```json
{
  "ip_address": "10.17.192.162",
  "name": "Lab Sensor",
  "location": "Science Building Room 201",
  "upload_token": "your-token"
}
```

### Tempest
```json
{
  "ip_address": "192.168.1.150",
  "name": "Campus Weather",
  "location": "Rooftop",
  "device_id": "12345",
  "upload_token": "your-token"
}
```

## For Remote Access (Frontend on Another Server)

The frontend might be hosted on Vercel while the backend runs on campus. 
Use Cloudflare Tunnel to make the backend accessible:

```bash
# Install cloudflared
brew install cloudflared  # macOS

# Create a tunnel
cloudflared tunnel --url http://localhost:8000
```

This gives you a URL like `https://random-words.trycloudflare.com` that the frontend can use.

## Environment Variables

Create a `.env` file in the `backend/` folder:

```
POLLING_INTERVAL=60
FRONTEND_URL=https://your-frontend.vercel.app
```

## CSV Data Format

### Purple Air
```csv
Timestamp,Temperature (°F),Humidity (%),Dewpoint (°F),Pressure (hPa),PM1.0,PM2.5,PM10,AQI
2026-01-06T03:00:00+00:00,72,45,52,1013,5.2,12.4,18.7,52
```

### Tempest
```csv
Timestamp,Temperature (°F),Humidity (%),Pressure (mb),Wind Speed (mph),Wind Gust (mph),Wind Dir (°),Rain (in),UV,Solar (W/m²),Lightning
2026-01-06T03:00:00+00:00,72,45,1013,5.2,8.1,180,0.0,3.5,450,0
```

## Need Help?

1. **API Docs**: Open http://localhost:8000/docs after starting the server
2. **Check the code**: Every file has detailed comments explaining what it does
3. **Frontend instructions**: See `frontend/FRONTEND_REQUIREMENTS.md`

## Authors

- Frank Kusi Appiah
