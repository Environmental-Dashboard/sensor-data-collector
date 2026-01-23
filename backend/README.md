# Backend - Sensor Data Collector

FastAPI backend that collects data from environmental sensors and uploads to Community Hub.

## Quick Start

```powershell
# Create virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Run with auto-reload
uvicorn app.main:app --port 8000 --reload
```

## Architecture

```
app/
├── main.py                 # FastAPI app, CORS, startup/shutdown
├── models/
│   └── sensor.py           # Pydantic models for sensors & readings
├── routers/
│   └── sensors.py          # API endpoints
└── services/
    ├── sensor_manager.py   # Orchestrates all sensors, scheduling
    ├── purple_air_service.py   # Purple Air sensor API
    ├── tempest_service.py      # Tempest weather station API
    └── water_quality_service.py # Water quality via Ubidots
```

## Key Components

### SensorManager (`services/sensor_manager.py`)

Central orchestrator that:
- Manages sensor lifecycle (add/remove/toggle)
- Schedules polling jobs via APScheduler
- Persists sensor config to `sensors_db.json`
- Handles power saving mode for Purple Air sensors

### Services

Each sensor type has its own service:

| Service | Sensor | Data Source |
|---------|--------|-------------|
| `PurpleAirService` | Purple Air | Local network HTTP |
| `TempestService` | WeatherFlow Tempest | WeatherFlow Cloud API |
| `WaterQualityService` | Water Quality | Ubidots API |

### Error Handling

The system classifies errors by source:

| Error Type | Status | Description |
|------------|--------|-------------|
| `battery_low` | `offline` | Battery drained, sensor powered off (expected state) |
| `wifi_error` | `error` | Can't reach sensor on network |
| `cloud_error` | `error` | Community Hub unavailable (retried once) |
| `auth_error` | `error` | Invalid upload token |
| `connection_error` | `error` | Network connectivity issue |

## API Endpoints

### Health & Diagnostics
- `GET /health` - System health check
- `GET /api/sensors/health/upload-test` - Test upload to Community Hub

### Sensor Management
- `GET /api/sensors/` - List all sensors
- `GET /api/sensors/{type}` - List sensors by type
- `POST /api/sensors/{type}` - Add sensor
- `GET /api/sensors/{id}` - Get sensor details
- `DELETE /api/sensors/{id}` - Remove sensor
- `PATCH /api/sensors/{id}` - Update sensor

### Sensor Control
- `POST /api/sensors/{id}/turn-on` - Start polling
- `POST /api/sensors/{id}/turn-off` - Stop polling
- `POST /api/sensors/{id}/fetch-now` - Manual fetch
- `POST /api/sensors/{id}/frequency` - Change polling interval

### Diagnostics
- `GET /api/sensors/{id}/diagnostics` - Detailed status & last error
- `GET /api/sensors/{id}/last-data` - Last sent CSV sample

## Data Flow

```
1. Sensor (Purple Air, Tempest, etc.)
   ↓ (fetch data)
2. Service (parse, validate)
   ↓ (convert to CSV)
3. Upload to Community Hub
   ↓ (on success)
4. Update sensor status
   ↓ (persist)
5. sensors_db.json
```

## CSV Format

See `CSV_FORMAT.md` for detailed CSV format specifications for each sensor type.

**Key points:**
- UTF-8 encoding
- Raw body upload (not multipart)
- Headers match Community Hub data source columns
- Timestamp format: `YYYY-MM-DD HH:MM:SS EST` (or your timezone)

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `TEMPEST_API_TOKEN` | WeatherFlow API token | (set in main.py) |
| `CORS_ORIGINS` | Allowed CORS origins | localhost, vercel |

### Persistence

Sensor configuration is stored in `sensors_db.json`:
- Loaded on startup
- Saved after any change
- Atomic writes prevent corruption

## Development

### Running Tests

```powershell
# Run from backend directory
python -m pytest tests/
```

### Adding a New Sensor Type

1. Add enum value to `models/sensor.py` → `SensorType`
2. Create Pydantic models for request/reading
3. Create service in `services/`
4. Add endpoints in `routers/sensors.py`
5. Update `sensor_manager.py` to handle the type

### Logging

Logs include:
- CSV content previews (first 500 chars)
- HTTP request/response details
- Error messages with context

Adjust log level in `main.py`:
```python
logging.basicConfig(level=logging.DEBUG)  # or INFO, WARNING
```

## Files

| File | Purpose |
|------|---------|
| `sensors_db.json` | Persisted sensor config |
| `backend.log` | Backend output (when run via scripts) |
| `requirements.txt` | Python dependencies |
| `start-backend.ps1` | Start script (with auto-reload) |
| `start-hidden.vbs` | Start both backend & tunnel hidden |
