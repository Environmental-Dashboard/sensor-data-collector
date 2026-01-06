# Sensor Data Collector

A comprehensive system for collecting environmental sensor data from local network devices and automatically pushing it to an external data hub. Built with FastAPI, this backend service manages multiple sensor types, schedules automatic polling, and provides a REST API for monitoring and control.

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Supported Sensors](#supported-sensors)
- [Quick Start](#quick-start)
- [API Documentation](#api-documentation)
- [Configuration](#configuration)
- [Deployment](#deployment)
- [Development](#development)
- [Documentation](#documentation)
- [License](#license)

---

## Overview

The Sensor Data Collector is designed to bridge the gap between local network sensors and cloud-based data platforms. It runs on a local machine with network access to your sensors, automatically collects data at regular intervals, and uploads it to an external endpoint.

**Key Use Case:** Monitor environmental conditions (air quality, weather) across a campus or facility, with all sensor data automatically aggregated to a central platform for analysis and visualization.

---

## Features

### ✅ Core Features
- **Multiple Sensor Support**: Purple Air (air quality) and Tempest (weather) sensors
- **Automatic Data Collection**: Scheduled polling every 60 seconds (configurable)
- **REST API**: Complete API for sensor management and monitoring
- **CSV Export**: Automatically converts sensor data to CSV format
- **Error Handling**: Robust error handling with status tracking
- **Remote Access**: Works with Cloudflare Tunnel for secure remote management

### 🚧 In Progress
- React dashboard for visual management
- Water quality sensors
- Mayfly datalogger support

### 🎯 Technical Highlights
- Built with FastAPI (high performance, auto-generated docs)
- Async/await for efficient I/O operations
- APScheduler for reliable background jobs
- Pydantic for data validation
- Type hints throughout codebase

---

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

---

## Supported Sensors

| Sensor Type | Status | Data Collected | Connection |
|-------------|--------|----------------|------------|
| **Purple Air** | ✅ Fully Supported | PM1.0, PM2.5, PM10, Temperature, Humidity, Dewpoint, Pressure, AQI | HTTP (local IP) |
| **Tempest Weather** | ✅ Fully Supported | Temperature, Humidity, Pressure, Wind Speed/Gust/Direction, Rain, UV, Solar Radiation, Lightning | HTTP/UDP (local IP) |
| **Water Quality** | 🚧 Planned | TBD | TBD |
| **Mayfly Datalogger** | 🚧 Planned | TBD | TBD |

### Purple Air Details
- **API Endpoint**: `http://<sensor-ip>/json`
- **Authentication**: None required for local network
- **Polling**: Every 60 seconds (configurable)
- **CSV Format**: 9 columns including particulate matter and environmental data

### Tempest Weather Details
- **API Options**: UDP broadcast (port 50222) or HTTP REST
- **Authentication**: None required for local network
- **Polling**: Every 60 seconds (configurable)
- **CSV Format**: 11 columns including comprehensive weather data

---

## Quick Start

### Prerequisites
- Python 3.9 or higher
- Network access to your sensors
- (Optional) Cloudflared for remote access

### 1. Installation

```bash
# Clone the repository
git clone <repository-url>
cd sensor-data-collector/backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

```bash
# Copy environment template
cp env.example.txt .env

# Edit with your settings
nano .env
```

**For Testing (Local Test Endpoint):**
```env
EXTERNAL_ENDPOINT_URL=http://localhost:8000/api/test/upload/csv
EXTERNAL_ENDPOINT_TOKEN=test-sensor-api-key-12345
POLLING_INTERVAL=60
FRONTEND_URL=http://localhost:5173
```

**For Production:**
```env
EXTERNAL_ENDPOINT_URL=https://oberlin.communityhub.cloud/api/data-hub/upload/csv
EXTERNAL_ENDPOINT_TOKEN=your-production-token-here
POLLING_INTERVAL=60
FRONTEND_URL=https://your-frontend-domain.com
```

### 3. Run the Server

```bash
uvicorn app.main:app --reload --port 8000
```

You should see:
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

### 4. Add Your First Sensor

```bash
# Add a Purple Air sensor
curl -X POST http://localhost:8000/api/sensors/purple-air \
  -H "Content-Type: application/json" \
  -d '{
    "ip_address": "192.168.1.100",
    "name": "Office Sensor",
    "location": "Main Office Building"
  }'

# Response will include sensor ID - use it to turn on the sensor
curl -X POST http://localhost:8000/api/sensors/{sensor-id}/turn-on
```

### 5. Monitor Your Sensors

Visit `http://localhost:8000/docs` for the interactive API documentation, or:

```bash
# List all sensors
curl http://localhost:8000/api/sensors

# Get sensor status
curl http://localhost:8000/api/sensors/{sensor-id}/status
```

---

## API Documentation

### Interactive Documentation
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

### Quick Reference

#### Sensor Management
```
GET    /api/sensors                    # List all sensors
GET    /api/sensors?sensor_type=...    # Filter by type
GET    /api/sensors/{id}               # Get specific sensor
DELETE /api/sensors/{id}               # Remove sensor
```

#### Sensor Control
```
POST   /api/sensors/{id}/turn-on       # Start data collection
POST   /api/sensors/{id}/turn-off      # Stop data collection
POST   /api/sensors/{id}/fetch-now     # Manual data fetch
GET    /api/sensors/{id}/status        # Get detailed status
```

#### Add Sensors
```
POST   /api/sensors/purple-air         # Add Purple Air sensor
POST   /api/sensors/tempest            # Add Tempest weather station
```

For complete API documentation with examples, see [API.md](docs/API.md).

---

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `EXTERNAL_ENDPOINT_URL` | Yes | Test endpoint | URL where CSV data is uploaded |
| `EXTERNAL_ENDPOINT_TOKEN` | Yes | Test token | Bearer token for authentication |
| `POLLING_INTERVAL` | No | 60 | Seconds between data polls |
| `FRONTEND_URL` | No | localhost:5173 | Frontend URL for CORS |
| `HOST` | No | 0.0.0.0 | Server host |
| `PORT` | No | 8000 | Server port |

### Polling Behavior

The system uses APScheduler to poll sensors at regular intervals:

1. **Sensor Added**: Registered but not polling
2. **Sensor Turned On**: Scheduler creates a job
3. **Every N Seconds**: Job fetches data, converts to CSV, uploads
4. **On Success**: Status updated to ACTIVE, last_active timestamp set
5. **On Failure**: Status updated to ERROR, error message saved
6. **Sensor Turned Off**: Scheduler removes job, status set to INACTIVE

---

## Deployment

### Local Deployment

Run directly on a computer with network access to your sensors:

```bash
# Production mode (without auto-reload)
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Remote Access with Cloudflare Tunnel

Allow a hosted frontend to communicate with your local backend:

```bash
# Install cloudflared
brew install cloudflared  # macOS
# or download from cloudflare.com

# Start tunnel
cloudflared tunnel --url http://localhost:8000
```

This provides a public URL like `https://random-words.trycloudflare.com`.

### Docker Deployment (Coming Soon)

```bash
docker build -t sensor-collector .
docker run -p 8000:8000 --env-file .env sensor-collector
```

### System Service (Linux)

Create `/etc/systemd/system/sensor-collector.service`:

```ini
[Unit]
Description=Sensor Data Collector
After=network.target

[Service]
Type=simple
User=<your-user>
WorkingDirectory=/path/to/sensor-data-collector/backend
Environment="PATH=/path/to/venv/bin"
ExecStart=/path/to/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable sensor-collector
sudo systemctl start sensor-collector
```

For more deployment options, see [DEPLOYMENT.md](docs/DEPLOYMENT.md).

---

## Development

### Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                   # FastAPI application entry point
│   ├── models/
│   │   ├── __init__.py
│   │   └── sensor.py             # Pydantic models for validation
│   ├── services/
│   │   ├── __init__.py
│   │   ├── sensor_manager.py     # Central sensor coordinator
│   │   ├── purple_air_service.py # Purple Air data pipeline
│   │   └── tempest_service.py    # Tempest data pipeline
│   └── routers/
│       ├── __init__.py
│       ├── sensors.py            # Sensor API endpoints
│       └── test_upload.py        # Test CSV upload endpoint
├── requirements.txt              # Python dependencies
├── env.example.txt              # Environment template
└── .gitignore
```

### Adding a New Sensor Type

1. **Define the data model** in `app/models/sensor.py`:
   ```python
   class MySensorReading(BaseModel):
       timestamp: datetime
       value: float
       # ... additional fields
   ```

2. **Create a service** in `app/services/my_sensor_service.py`:
   ```python
   class MySensorService:
       async def fetch_and_push(self, ip_address: str, sensor_name: str):
           # Fetch from sensor
           # Convert to CSV
           # Upload to endpoint
   ```

3. **Register in sensor_manager.py**:
   ```python
   # Add to SensorType enum
   # Add to add_sensor methods
   # Add to polling callbacks
   ```

4. **Add API endpoints** in `app/routers/sensors.py`:
   ```python
   @router.post("/my-sensor")
   async def add_my_sensor(request: AddMySensorRequest):
       # Handle sensor registration
   ```

For detailed development guide, see [DEVELOPMENT.md](docs/DEVELOPMENT.md).

---

## Documentation

- **[API.md](docs/API.md)** - Complete API reference with examples
- **[ARCHITECTURE.md](docs/ARCHITECTURE.md)** - Detailed architecture and design
- **[DEPLOYMENT.md](docs/DEPLOYMENT.md)** - Production deployment guide
- **[DEVELOPMENT.md](docs/DEVELOPMENT.md)** - Development and contribution guide
- **[FRONTEND_REQUIREMENTS.md](frontend/FRONTEND_REQUIREMENTS.md)** - Frontend implementation guide

---

## Testing

### Manual Testing with curl

```bash
# Health check
curl http://localhost:8000/health

# Add Purple Air sensor
curl -X POST http://localhost:8000/api/sensors/purple-air \
  -H "Content-Type: application/json" \
  -d '{"ip_address": "192.168.1.100", "name": "Test Sensor", "location": "Test Lab"}'

# List sensors
curl http://localhost:8000/api/sensors

# Turn on sensor
curl -X POST http://localhost:8000/api/sensors/{id}/turn-on

# Manual fetch
curl -X POST http://localhost:8000/api/sensors/{id}/fetch-now

# Turn off sensor
curl -X POST http://localhost:8000/api/sensors/{id}/turn-off

# Delete sensor
curl -X DELETE http://localhost:8000/api/sensors/{id}
```

### Test CSV Upload

```bash
# Create test CSV
echo "Timestamp,Value\n2026-01-05T12:00:00Z,42" > test.csv

# Upload
curl -X POST http://localhost:8000/api/test/upload/csv \
  -H "Authorization: Bearer test-sensor-api-key-12345" \
  -F "file=@test.csv"
```

---

## Troubleshooting

### Sensor Not Responding
- Verify sensor is on same network
- Check IP address is correct
- Ensure no firewall blocking access
- Test sensor API directly: `curl http://<sensor-ip>/json`

### Upload Failing
- Verify `EXTERNAL_ENDPOINT_TOKEN` is correct
- Check external endpoint is accessible
- Review logs for error messages
- Test with local test endpoint first

### Scheduler Issues
- Check logs for job execution
- Verify sensor status: `GET /api/sensors/{id}/status`
- Try manual fetch: `POST /api/sensors/{id}/fetch-now`

---

## Contributing

Contributions are welcome! Areas for contribution:

1. **New Sensor Types**: Add support for additional sensor hardware
2. **Frontend Dashboard**: Build the React dashboard (see FRONTEND_REQUIREMENTS.md)
3. **Testing**: Add unit and integration tests
4. **Documentation**: Improve docs and examples
5. **Bug Fixes**: Report and fix issues

Please see [DEVELOPMENT.md](docs/DEVELOPMENT.md) for contribution guidelines.

---

## License

MIT License - See LICENSE file for details

---

## Support

For questions, issues, or feature requests:
- Open an issue on GitHub
- Check existing documentation
- Review API docs at `/docs`

---

## Acknowledgments

- Built with [FastAPI](https://fastapi.tiangolo.com/)
- Scheduling by [APScheduler](https://apscheduler.readthedocs.io/)
- HTTP client by [HTTPX](https://www.python-httpx.org/)
- Purple Air and WeatherFlow for sensor hardware

---

**Version**: 1.0.0  
**Last Updated**: January 2026  
**Author**: Sensor Data Collector Team

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
