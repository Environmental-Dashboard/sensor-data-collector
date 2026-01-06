# Sensor Data Collector

A system for collecting environmental sensor data from local network sensors and pushing it to an external endpoint.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CLOUD / HOSTED                                  │
│                                                                              │
│    ┌──────────────────────────────────────────────────────────────────┐     │
│    │                    React Frontend Dashboard                       │     │
│    │                   (Vercel, Netlify, etc.)                         │     │
│    │                                                                   │     │
│    │   • View sensor status      • Add/Delete sensors                 │     │
│    │   • Turn sensors on/off     • View last active time              │     │
│    │   • Manual data fetch       • Monitor connection                 │     │
│    └──────────────────────────────────────────────────────────────────┘     │
│                                    │                                         │
│                                    │ HTTPS                                   │
│                                    ▼                                         │
│    ┌──────────────────────────────────────────────────────────────────┐     │
│    │              Cloudflare Tunnel (Free)                             │     │
│    │        https://your-random-words.trycloudflare.com                │     │
│    └──────────────────────────────────────────────────────────────────┘     │
│                                    │                                         │
└────────────────────────────────────┼────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           LOCAL NETWORK                                      │
│                                                                              │
│    ┌──────────────────────────────────────────────────────────────────┐     │
│    │              Python Backend (FastAPI)                             │     │
│    │              Running on local computer                            │     │
│    │                                                                   │     │
│    │   • Manages sensor registry      • Scheduled polling (60s)       │     │
│    │   • Fetches data via local IP    • Converts JSON to CSV          │     │
│    │   • Pushes to external endpoint  • REST API for frontend         │     │
│    └──────────────────────────────────────────────────────────────────┘     │
│                          │              │                                    │
│              ┌───────────┘              └───────────┐                        │
│              ▼                                      ▼                        │
│    ┌──────────────────┐                   ┌──────────────────┐              │
│    │  Purple Air      │                   │  Tempest         │              │
│    │  Sensor          │                   │  Weather Station │              │
│    │  192.168.x.x     │                   │  192.168.x.x     │              │
│    │                  │                   │                  │              │
│    │  • PM2.5, PM10   │                   │  • Temperature   │              │
│    │  • Temperature   │                   │  • Humidity      │              │
│    │  • Humidity      │                   │  • Wind, Rain    │              │
│    │  • Pressure      │                   │  • UV, Lightning │              │
│    └──────────────────┘                   └──────────────────┘              │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     │ HTTPS POST (CSV data)
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                       EXTERNAL ENDPOINT                                      │
│         https://oberlin.communityhub.cloud/api/data-hub/upload/csv          │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Supported Sensors

| Sensor Type | Status | Data Collected |
|-------------|--------|----------------|
| **Purple Air** | ✅ Working | PM1.0, PM2.5, PM10, Temperature, Humidity, Dewpoint, Pressure, AQI |
| **Tempest Weather** | ✅ Working | Temperature, Humidity, Pressure, Wind Speed/Gust/Direction, Rain, UV, Solar Radiation, Lightning |
| **Water Quality** | 🚧 Placeholder | Coming soon |
| **Mayfly Datalogger** | 🚧 Placeholder | Coming soon |

## Project Structure

```
sensor-data-collector/
│
├── backend/                          # Python FastAPI Backend (COMPLETE)
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                   # Application entry point
│   │   │
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   └── sensor.py             # Pydantic models
│   │   │
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── purple_air_service.py # Purple Air data pipeline
│   │   │   ├── tempest_service.py    # Tempest data pipeline
│   │   │   └── sensor_manager.py     # Central sensor management
│   │   │
│   │   └── routers/
│   │       ├── __init__.py
│   │       ├── sensors.py            # Sensor API endpoints
│   │       └── test_upload.py        # Test upload endpoint (don't commit)
│   │
│   ├── requirements.txt
│   ├── env.example.txt
│   └── .gitignore
│
├── frontend/                          # React Dashboard (TO BE BUILT)
│   └── FRONTEND_REQUIREMENTS.md       # Detailed requirements for frontend dev
│
└── README.md
```

## Quick Start - Backend

### 1. Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate    # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp env.example.txt .env
```

Edit `.env`:
```
# For local testing (uses built-in test endpoint)
EXTERNAL_ENDPOINT_URL=http://localhost:8000/api/test/upload/csv
EXTERNAL_ENDPOINT_TOKEN=test-sensor-api-key-12345

# For production
# EXTERNAL_ENDPOINT_URL=https://oberlin.communityhub.cloud/api/data-hub/upload/csv
# EXTERNAL_ENDPOINT_TOKEN=your-real-token-here

POLLING_INTERVAL=60
FRONTEND_URL=http://localhost:5173
```

### 3. Run the Server

```bash
uvicorn app.main:app --reload --port 8000
```

Output:
```
============================================================
🚀 SENSOR DATA COLLECTOR - Starting Backend
============================================================
✅ Services initialized
   Polling interval: 60 seconds
   External endpoint: http://localhost:8000/api/test/upload/csv

📡 Supported Sensors:
   - Purple Air (air quality)
   - Tempest (weather)
   - Water Quality (coming soon)
   - Mayfly (coming soon)

📖 API Documentation: http://localhost:8000/docs
============================================================
```

### 4. Expose via Cloudflare Tunnel (for remote access)

```bash
# Install cloudflared
brew install cloudflared  # macOS
# Or download from: https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/

# Start tunnel
cloudflared tunnel --url http://localhost:8000
```

This gives you a URL like `https://random-words.trycloudflare.com` that the hosted frontend can use.

## API Endpoints

### Sensor Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/sensors` | List all sensors |
| `GET` | `/api/sensors?sensor_type=purple_air` | List by type |
| `GET` | `/api/sensors/{id}` | Get single sensor |
| `DELETE` | `/api/sensors/{id}` | Delete sensor |
| `GET` | `/api/sensors/{id}/status` | Get status details |
| `POST` | `/api/sensors/{id}/turn-on` | Start data collection |
| `POST` | `/api/sensors/{id}/turn-off` | Stop data collection |
| `POST` | `/api/sensors/{id}/fetch-now` | Manual fetch |

### Add Sensors

| Method | Endpoint | Required Fields |
|--------|----------|-----------------|
| `POST` | `/api/sensors/purple-air` | `ip_address`, `name`, `location` |
| `POST` | `/api/sensors/tempest` | `ip_address`, `name`, `location`, `device_id` |
| `POST` | `/api/sensors/water-quality` | Not implemented yet |
| `POST` | `/api/sensors/mayfly` | Not implemented yet |

### Test Endpoint

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/test/upload/csv` | Test CSV upload (requires Bearer token) |
| `GET` | `/api/test/health` | Get test API key |

## Testing with curl

```bash
# Check health
curl http://localhost:8000/health

# Add a Purple Air sensor
curl -X POST http://localhost:8000/api/sensors/purple-air \
  -H "Content-Type: application/json" \
  -d '{
    "ip_address": "192.168.1.100",
    "name": "Lab Sensor",
    "location": "Science Building"
  }'

# Add a Tempest sensor
curl -X POST http://localhost:8000/api/sensors/tempest \
  -H "Content-Type: application/json" \
  -d '{
    "ip_address": "192.168.1.150",
    "name": "Campus Weather",
    "location": "Rooftop",
    "device_id": "12345"
  }'

# List all sensors
curl http://localhost:8000/api/sensors

# Turn on a sensor (replace ID)
curl -X POST http://localhost:8000/api/sensors/{id}/turn-on

# Trigger manual fetch
curl -X POST http://localhost:8000/api/sensors/{id}/fetch-now

# Turn off
curl -X POST http://localhost:8000/api/sensors/{id}/turn-off

# Delete
curl -X DELETE http://localhost:8000/api/sensors/{id}

# Test upload endpoint
curl -X POST http://localhost:8000/api/test/upload/csv \
  -H "Authorization: Bearer test-sensor-api-key-12345" \
  -F "file=@test.csv"
```

## Frontend Development

See `frontend/FRONTEND_REQUIREMENTS.md` for:
- Complete API documentation
- TypeScript interfaces
- UI/UX recommendations
- Testing instructions

## CSV Data Formats

### Purple Air CSV Columns
```
Timestamp,Temperature (°F),Humidity (%),Dewpoint (°F),Pressure (hPa),PM1.0 :cf_1( µg/m³),PM2.5 :cf_1( µg/m³),PM10.0 :cf_1( µg/m³),PM2.5 AQI
2026-01-05T22:26:50+00:00,40,62,28,985.09,15.82,26.49,33.05,82
```

### Tempest CSV Columns
```
Timestamp,Temperature (°F),Humidity (%),Pressure (mb),Wind Speed (mph),Wind Gust (mph),Wind Direction (°),Rain (in),UV Index,Solar Radiation (W/m²),Lightning Count
2026-01-05T22:26:50+00:00,72.5,45.2,1013.25,5.2,8.1,180,0.0,3.5,450,0
```

## Technical Details

### How Purple Air Local API Works

Purple Air sensors expose their data at `http://<sensor_ip>/json`. No authentication required on local network. The backend fetches this JSON, extracts the key fields, converts to CSV, and uploads.

### How Tempest Local API Works

Tempest Hub broadcasts on UDP port 50222 and may expose a REST endpoint at `http://<hub_ip>/v1/obs`. The backend queries the hub, parses the observation array, converts to CSV, and uploads.

### Polling Flow

1. User adds sensor (registers in memory)
2. User turns on sensor
3. APScheduler creates a job running every 60 seconds
4. Each poll:
   - HTTP GET to sensor IP
   - Parse JSON response
   - Convert to CSV string
   - HTTP POST to external endpoint with Bearer token
5. Status updated (success → active, failure → error)

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `EXTERNAL_ENDPOINT_URL` | Test endpoint | Where to push CSV data |
| `EXTERNAL_ENDPOINT_TOKEN` | Test key | Bearer token for auth |
| `POLLING_INTERVAL` | 60 | Seconds between polls |
| `FRONTEND_URL` | localhost:5173 | CORS allowed origin |

## Contributing

1. Backend is complete - add new sensor types in `services/`
2. Frontend needs to be built - see requirements doc
3. Don't commit `test_upload.py` to production

## License

MIT
