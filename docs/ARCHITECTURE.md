# Architecture Documentation

Comprehensive architecture documentation for the Sensor Data Collector system.

---

## Table of Contents

- [System Overview](#system-overview)
- [Component Architecture](#component-architecture)
- [Data Flow](#data-flow)
- [Technology Stack](#technology-stack)
- [Design Patterns](#design-patterns)
- [Service Layer](#service-layer)
- [Data Models](#data-models)
- [Scheduling System](#scheduling-system)
- [Error Handling](#error-handling)
- [Security Considerations](#security-considerations)
- [Scalability](#scalability)
- [Future Enhancements](#future-enhancements)

---

## System Overview

The Sensor Data Collector is a **three-tier architecture** designed to bridge local network sensors with cloud-based data platforms:

### Architecture Layers

```
┌─────────────────────────────────────────────────────────────────┐
│                    PRESENTATION LAYER                            │
│                   (React Frontend - Planned)                     │
│                                                                  │
│  • Dashboard UI                                                  │
│  • Sensor management interface                                  │
│  • Real-time status monitoring                                  │
└──────────────────────────┬──────────────────────────────────────┘
                           │ HTTPS / REST API
                           │
┌──────────────────────────┴──────────────────────────────────────┐
│                    APPLICATION LAYER                             │
│                   (FastAPI Backend - Current)                    │
│                                                                  │
│  ┌────────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │   API Router   │  │   Services   │  │   Scheduler      │   │
│  │   (FastAPI)    │  │   (Async)    │  │   (APScheduler)  │   │
│  └────────────────┘  └──────────────┘  └──────────────────┘   │
│                                                                  │
└──────────────────────────┬──────────────────────────────────────┘
                           │ HTTP / UDP
                           │
┌──────────────────────────┴──────────────────────────────────────┐
│                    DATA SOURCE LAYER                             │
│                   (Physical Sensors)                             │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐     │
│  │ Purple Air   │  │   Tempest    │  │  Future Sensors  │     │
│  │   Sensors    │  │   Weather    │  │                  │     │
│  └──────────────┘  └──────────────┘  └──────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
```

### Network Topology

```
┌──────────────────────────────────────────────────────────────────┐
│                         INTERNET / CLOUD                          │
│                                                                   │
│  ┌────────────────┐                    ┌──────────────────────┐ │
│  │ React Frontend │                    │  External Endpoint   │ │
│  │   (Vercel)     │                    │  (Data Warehouse)    │ │
│  └────────┬───────┘                    └──────────▲───────────┘ │
│           │                                       │              │
└───────────┼───────────────────────────────────────┼──────────────┘
            │                                       │
            │ HTTPS                                 │ HTTPS POST
            │                                       │ (CSV Upload)
┌───────────▼───────────────────────────────────────┼──────────────┐
│           │         CLOUDFLARE TUNNEL             │              │
│           │         (Secure Bridge)               │              │
└───────────┼───────────────────────────────────────┼──────────────┘
            │                                       │
┌───────────▼───────────────────────────────────────┼──────────────┐
│       LOCAL NETWORK                               │              │
│                                                   │              │
│  ┌────────┴───────────────────────────────────────┴──────────┐  │
│  │            FastAPI Backend Server                          │  │
│  │            (Python Process)                                │  │
│  │                                                            │  │
│  │  • REST API (port 8000)                                   │  │
│  │  • Sensor Manager                                         │  │
│  │  • APScheduler (background jobs)                          │  │
│  │  • HTTPX Client (async HTTP)                              │  │
│  └────────┬───────────────────────────────┬──────────────────┘  │
│           │                               │                      │
│           │ HTTP                          │ HTTP/UDP             │
│           │                               │                      │
│  ┌────────▼─────────┐          ┌─────────▼──────────┐          │
│  │  Purple Air      │          │  Tempest Hub        │          │
│  │  192.168.1.100   │          │  192.168.1.150      │          │
│  │                  │          │                     │          │
│  │  Exposes JSON    │          │  UDP Broadcast      │          │
│  │  at /json        │          │  Port 50222         │          │
│  └──────────────────┘          └─────────────────────┘          │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## Component Architecture

### Backend Components

```
app/
├── main.py                    # Application entry point
│   ├── FastAPI app creation
│   ├── CORS middleware setup
│   ├── Router registration
│   └── Lifespan management
│
├── models/
│   └── sensor.py              # Data models & validation
│       ├── Pydantic models
│       ├── Enums (SensorType, SensorStatus)
│       ├── Request models
│       ├── Response models
│       └── CSV conversion logic
│
├── services/
│   ├── sensor_manager.py      # Central coordinator
│   │   ├── Sensor registry (in-memory dict)
│   │   ├── CRUD operations
│   │   ├── Scheduler management
│   │   └── Status tracking
│   │
│   ├── purple_air_service.py  # Purple Air pipeline
│   │   ├── HTTP client
│   │   ├── Data fetching
│   │   ├── JSON parsing
│   │   ├── CSV conversion
│   │   └── Upload to endpoint
│   │
│   └── tempest_service.py     # Tempest pipeline
│       ├── HTTP/UDP client
│       ├── Data fetching
│       ├── Array parsing
│       ├── CSV conversion
│       └── Upload to endpoint
│
└── routers/
    ├── sensors.py             # Main API endpoints
    │   ├── Sensor CRUD
    │   ├── Control endpoints (turn on/off)
    │   ├── Status endpoints
    │   └── Type-specific endpoints
    │
    └── test_upload.py         # Test endpoint for development
        └── Mock CSV upload
```

---

## Data Flow

### 1. Sensor Registration Flow

```
User/Frontend
    │
    │ POST /api/sensors/purple-air
    ▼
API Router (sensors.py)
    │
    │ Validate IP, check duplicates
    ▼
Sensor Manager
    │
    │ Generate UUID
    │ Create sensor record
    │ Store in memory
    ▼
Return SensorResponse
    │
    ▼
User/Frontend (receives sensor ID)
```

### 2. Data Collection Flow (Scheduled)

```
APScheduler
    │
    │ Every 60 seconds
    ▼
Polling Job (sensor_id)
    │
    ▼
Sensor Manager._poll_purple_air_sensor()
    │
    ▼
Purple Air Service.fetch_and_push()
    │
    ├─▶ fetch_sensor_data(ip_address)
    │       │
    │       │ HTTP GET http://192.168.1.100/json
    │       ▼
    │   Raw JSON response
    │
    ├─▶ parse_sensor_response(raw_data)
    │       │
    │       │ Extract fields, validate types
    │       ▼
    │   PurpleAirReading object
    │
    ├─▶ convert_to_csv(reading)
    │       │
    │       │ Format as CSV string
    │       ▼
    │   CSV string with header
    │
    └─▶ push_to_endpoint(csv_data, sensor_name)
            │
            │ HTTP POST multipart/form-data
            │ Authorization: Bearer <token>
            ▼
        External Endpoint
            │
            ▼
        Success/Error Response
            │
            ▼
Update sensor status in registry
    │
    ├─ Success → status: ACTIVE, last_active: now
    └─ Error   → status: ERROR, last_error: message
```

### 3. Manual Fetch Flow

```
User/Frontend
    │
    │ POST /api/sensors/{id}/fetch-now
    ▼
API Router
    │
    ▼
Sensor Manager.trigger_fetch_now(sensor_id)
    │
    │ Same as scheduled flow
    ▼
[Data Collection Flow]
    │
    ▼
Return full result with data
    │
    ▼
User/Frontend (receives reading data)
```

---

## Technology Stack

### Core Technologies

| Technology | Version | Purpose |
|------------|---------|---------|
| **Python** | 3.9+ | Programming language |
| **FastAPI** | 0.109.0 | Web framework |
| **Uvicorn** | 0.27.0 | ASGI server |
| **Pydantic** | 2.5.3 | Data validation |
| **HTTPX** | 0.26.0 | Async HTTP client |
| **APScheduler** | 3.10.4 | Background task scheduling |
| **python-dotenv** | 1.0.0 | Environment management |

### Why These Technologies?

**FastAPI:**
- High performance (on par with Node.js)
- Automatic API documentation (OpenAPI/Swagger)
- Type hints and validation via Pydantic
- Native async/await support
- Excellent developer experience

**HTTPX:**
- Modern async HTTP client
- Better API than `requests`
- Connection pooling for efficiency
- Timeout and retry support

**APScheduler:**
- Mature, reliable scheduling library
- Multiple trigger types (interval, cron)
- Persistent job store options
- Works well with asyncio

**Pydantic:**
- Runtime type validation
- Automatic JSON serialization
- IDE autocomplete support
- Clear error messages

---

## Design Patterns

### 1. Service Layer Pattern

Each sensor type has its own service class:

```python
class PurpleAirService:
    """
    Encapsulates all Purple Air-specific logic:
    - HTTP communication
    - Data parsing
    - CSV conversion
    - Error handling
    """
    
    def __init__(self, endpoint_url, token):
        self.http_client = httpx.AsyncClient()
    
    async def fetch_and_push(self, ip, name):
        # Complete pipeline in one method
        pass
```

**Benefits:**
- Separation of concerns
- Easy to test in isolation
- Simple to add new sensor types
- Reusable components

### 2. Dependency Injection

Services are injected via FastAPI's dependency system:

```python
def get_sensor_manager():
    """Dependency that provides sensor manager"""
    return _sensor_manager

@router.get("/api/sensors")
async def get_sensors(manager = Depends(get_sensor_manager)):
    return manager.get_all_sensors()
```

**Benefits:**
- Testable (can mock dependencies)
- Single source of truth
- Clean API

### 3. Repository Pattern (In-Memory)

SensorManager acts as an in-memory repository:

```python
class SensorManager:
    def __init__(self):
        self._sensors: dict[str, dict] = {}  # In-memory storage
    
    def add_sensor(self, data) -> SensorResponse:
        sensor_id = str(uuid.uuid4())
        self._sensors[sensor_id] = data
        return SensorResponse(**data)
```

**Future Enhancement:** Replace with database (SQLite, PostgreSQL)

### 4. Strategy Pattern

Each sensor service implements the same interface:

```python
# Common interface (implicit in Python)
async def fetch_and_push(ip_address, sensor_name) -> dict:
    """
    Returns:
        {
            "status": "success" | "error",
            "reading": {...},
            "upload_result": {...}
        }
    """
```

SensorManager delegates to appropriate service:

```python
if sensor["sensor_type"] == SensorType.PURPLE_AIR:
    result = await self.purple_air_service.fetch_and_push(...)
elif sensor["sensor_type"] == SensorType.TEMPEST:
    result = await self.tempest_service.fetch_and_push(...)
```

---

## Service Layer

### Sensor Manager (Orchestrator)

**Responsibilities:**
1. Maintain sensor registry
2. Create/delete sensors
3. Manage polling jobs
4. Track sensor status
5. Coordinate between services

**Key Methods:**
```python
# CRUD
add_purple_air_sensor(request) -> SensorResponse
add_tempest_sensor(request) -> SensorResponse
get_sensor(sensor_id) -> Optional[SensorResponse]
get_all_sensors(type_filter) -> list[SensorResponse]
delete_sensor(sensor_id) -> bool

# Control
async turn_on_sensor(sensor_id) -> Optional[SensorResponse]
turn_off_sensor(sensor_id) -> Optional[SensorResponse]
async trigger_fetch_now(sensor_id) -> dict

# Internal
_start_polling_job(sensor_id, callback)
_stop_polling_job(sensor_id)
async _poll_purple_air_sensor(sensor_id)
async _poll_tempest_sensor(sensor_id)
```

### Purple Air Service

**Responsibilities:**
1. Fetch JSON from Purple Air sensors
2. Parse raw sensor data
3. Convert to CSV format
4. Upload to external endpoint
5. Handle errors gracefully

**Key Methods:**
```python
async fetch_sensor_data(ip_address) -> dict
parse_sensor_response(raw_data) -> PurpleAirReading
convert_to_csv(reading, include_header) -> str
async push_to_endpoint(csv_data, sensor_name) -> dict
async fetch_and_push(ip_address, sensor_name) -> dict
```

### Tempest Service

Similar structure to Purple Air Service, adapted for Tempest API format.

---

## Data Models

### Core Models

**SensorType (Enum):**
```python
class SensorType(str, Enum):
    PURPLE_AIR = "purple_air"
    TEMPEST = "tempest"
    WATER_QUALITY = "water_quality"
    MAYFLY = "mayfly"
```

**SensorStatus (Enum):**
```python
class SensorStatus(str, Enum):
    ACTIVE = "active"      # Polling and uploading successfully
    INACTIVE = "inactive"  # Registered but not polling
    ERROR = "error"        # Last poll failed
    OFFLINE = "offline"    # Extended failure period
```

**SensorResponse (Main DTO):**
```python
class SensorResponse(BaseModel):
    id: str
    sensor_type: SensorType
    name: str
    location: str
    ip_address: Optional[str]
    device_id: Optional[str]
    status: SensorStatus
    is_active: bool
    last_active: Optional[datetime]
    last_error: Optional[str]
    created_at: datetime
```

### Reading Models

**PurpleAirReading:**
- Represents a single air quality reading
- Includes CSV conversion methods
- Validates data types

**TempestReading:**
- Represents a single weather reading
- Comprehensive weather data
- CSV conversion included

---

## Scheduling System

### APScheduler Configuration

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

scheduler = AsyncIOScheduler()
scheduler.start()

# Add job
scheduler.add_job(
    callback_function,
    trigger=IntervalTrigger(seconds=60),
    id=f"poll_{sensor_id}",
    args=[sensor_id],
    replace_existing=True
)

# Remove job
scheduler.remove_job(f"poll_{sensor_id}")
```

### Job Lifecycle

1. **User turns on sensor** → `_start_polling_job()` called
2. **Job created** with unique ID (`poll_{sensor_id}`)
3. **Runs every N seconds** (default 60)
4. **Callback executes** (e.g., `_poll_purple_air_sensor`)
5. **Status updated** based on result
6. **Job continues** until sensor turned off
7. **User turns off sensor** → `_stop_polling_job()` called
8. **Job removed** from scheduler

### Error Handling in Jobs

Jobs don't raise exceptions - they catch and log:

```python
async def _poll_purple_air_sensor(self, sensor_id: str):
    sensor = self._sensors.get(sensor_id)
    if not sensor:
        return  # Sensor deleted, job will be removed
    
    result = await self.purple_air_service.fetch_and_push(...)
    
    if result["status"] == "success":
        sensor["status"] = SensorStatus.ACTIVE
        sensor["last_active"] = datetime.now(timezone.utc)
        sensor["last_error"] = None
    else:
        sensor["status"] = SensorStatus.ERROR
        sensor["last_error"] = result["error_message"]
```

---

## Error Handling

### Error Handling Strategy

**Principles:**
1. **Fail gracefully** - don't crash the app
2. **Log errors** - capture details for debugging
3. **Update status** - inform user of issues
4. **Continue operation** - one sensor failure doesn't affect others

### Error Categories

**Network Errors:**
```python
try:
    response = await self.http_client.get(url)
except httpx.ConnectError:
    return {"status": "error", "error_message": "Cannot connect to sensor"}
except httpx.TimeoutException:
    return {"status": "error", "error_message": "Request timed out"}
```

**Data Parsing Errors:**
```python
try:
    reading = self.parse_sensor_response(raw_data)
except KeyError as e:
    return {"status": "error", "error_message": f"Missing field: {e}"}
except ValueError as e:
    return {"status": "error", "error_message": f"Invalid value: {e}"}
```

**Upload Errors:**
```python
try:
    response = await self.http_client.post(url, ...)
    response.raise_for_status()
except httpx.HTTPStatusError as e:
    return {"status": "error", "error_message": f"Upload failed: {e.response.status_code}"}
```

### HTTP Exception Handling

FastAPI provides automatic exception handling:

```python
@router.get("/api/sensors/{sensor_id}")
async def get_sensor(sensor_id: str):
    sensor = manager.get_sensor(sensor_id)
    if not sensor:
        raise HTTPException(status_code=404, detail="Sensor not found")
    return sensor
```

---

## Security Considerations

### Current Security

**Sensor Management:**
- ⚠️ No authentication required
- Suitable for internal networks
- Add authentication middleware for production

**External Endpoint:**
- ✅ Bearer token authentication
- ✅ Configured via environment variable
- ✅ Not hardcoded

**CORS:**
- ✅ Configured via `FRONTEND_URL` environment variable
- ✅ Default allows localhost only
- Add production frontend URLs as needed

### Recommended Enhancements

**1. API Authentication:**
```python
from fastapi.security import HTTPBearer

security = HTTPBearer()

@router.post("/api/sensors/purple-air")
async def add_sensor(
    request: AddSensorRequest,
    token: str = Depends(security)
):
    # Verify token
    if not verify_token(token):
        raise HTTPException(401, "Invalid token")
    # ...
```

**2. Input Validation:**
- ✅ Already implemented via Pydantic
- ✅ IP address format validation
- ✅ String length limits

**3. Rate Limiting:**
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.get("/api/sensors")
@limiter.limit("100/minute")
async def get_sensors():
    # ...
```

**4. HTTPS Only:**
- Configure Uvicorn with SSL certificates
- Or use reverse proxy (Nginx, Traefik)

---

## Scalability

### Current Limitations

1. **In-Memory Storage:**
   - Sensors lost on restart
   - Single instance only
   - No persistence

2. **Single Process:**
   - Limited by single machine
   - No horizontal scaling

3. **Synchronous Scheduling:**
   - All sensors polled from same process
   - Long-running polls block others

### Scaling Strategies

**Vertical Scaling (Easy):**
- Increase `POLLING_INTERVAL` for more sensors
- Run on more powerful machine
- Use connection pooling (already implemented via HTTPX)

**Database Integration (Medium):**
```python
# Replace in-memory dict with SQLAlchemy
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

engine = create_engine("postgresql://...")
Session = sessionmaker(bind=engine)

class SensorManager:
    def add_sensor(self, data):
        session = Session()
        sensor = SensorModel(**data)
        session.add(sensor)
        session.commit()
        return sensor
```

**Distributed Scheduling (Hard):**
- Use Celery with Redis/RabbitMQ
- Each sensor poll becomes a Celery task
- Multiple workers can process tasks in parallel

**Microservices (Advanced):**
- Split into separate services:
  - API Gateway
  - Sensor Management Service
  - Purple Air Collector Service
  - Tempest Collector Service
  - Upload Service
- Use message queue for communication

---

## Future Enhancements

### Short Term
- [ ] Add database persistence (SQLite)
- [ ] Add authentication middleware
- [ ] Add rate limiting
- [ ] Add logging to files
- [ ] Add health metrics endpoint

### Medium Term
- [ ] React dashboard implementation
- [ ] WebSocket support for real-time updates
- [ ] Historical data storage
- [ ] Sensor configuration UI
- [ ] Alert system for sensor failures

### Long Term
- [ ] Multi-tenant support
- [ ] User management
- [ ] Advanced analytics
- [ ] Machine learning anomaly detection
- [ ] Mobile app

---

## Appendix

### Key Files Reference

| File | Lines | Purpose |
|------|-------|---------|
| `main.py` | ~320 | Application entry, configuration |
| `sensor_manager.py` | ~540 | Core business logic |
| `purple_air_service.py` | ~380 | Purple Air integration |
| `tempest_service.py` | ~830 | Tempest integration |
| `sensors.py` | ~430 | API endpoints |
| `sensor.py` | ~360 | Data models |

### Performance Characteristics

**Request Latency:**
- GET endpoints: < 10ms
- POST endpoints: < 50ms
- Fetch endpoints: 1-5 seconds (depends on sensor)

**Memory Usage:**
- Base: ~50MB
- Per sensor: ~1KB
- 100 sensors: ~55MB

**Network:**
- Poll frequency: 60 seconds default
- Per sensor per poll: ~5KB upload
- 100 sensors: ~8MB/hour upload

---

**Last Updated:** January 2026

