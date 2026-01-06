# Development Guide

Complete guide for developing and contributing to the Sensor Data Collector project.

---

## Table of Contents

- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Project Structure](#project-structure)
- [Code Style & Standards](#code-style--standards)
- [Adding New Sensor Types](#adding-new-sensor-types)
- [Testing](#testing)
- [Debugging](#debugging)
- [Git Workflow](#git-workflow)
- [Contributing Guidelines](#contributing-guidelines)
- [Common Development Tasks](#common-development-tasks)
- [API Development](#api-development)
- [Performance Optimization](#performance-optimization)
- [Troubleshooting](#troubleshooting)

---

## Getting Started

### Prerequisites

**Required:**
- Python 3.9+
- Git
- Text editor or IDE (VS Code, PyCharm recommended)
- Basic knowledge of FastAPI and async Python

**Recommended:**
- Docker Desktop (for containerized testing)
- Postman or curl (for API testing)
- Access to test sensors or sensor simulators

---

## Development Setup

### 1. Fork and Clone

```bash
# Fork the repository on GitHub, then clone your fork
git clone https://github.com/YOUR-USERNAME/sensor-data-collector.git
cd sensor-data-collector
```

### 2. Create Virtual Environment

```bash
cd backend

# Create venv
python3 -m venv venv

# Activate (Unix/macOS)
source venv/bin/activate

# Activate (Windows)
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
# Install production dependencies
pip install -r requirements.txt

# Install development dependencies (optional)
pip install pytest pytest-asyncio pytest-cov black flake8 mypy
```

### 4. Configure Development Environment

```bash
# Copy example environment
cp env.example.txt .env

# Edit for development
nano .env
```

**Development `.env`:**

```env
# Use local test endpoint for development
EXTERNAL_ENDPOINT_URL=http://localhost:8000/api/test/upload/csv
EXTERNAL_ENDPOINT_TOKEN=test-sensor-api-key-12345

# Short interval for faster testing
POLLING_INTERVAL=30

# Development CORS
FRONTEND_URL=http://localhost:5173

# Server config
HOST=127.0.0.1
PORT=8000
```

### 5. Run Development Server

```bash
# Run with auto-reload
uvicorn app.main:app --reload --port 8000

# Visit API docs
open http://localhost:8000/docs
```

### 6. Verify Setup

```bash
# In another terminal
curl http://localhost:8000/health

# Add a test sensor
curl -X POST http://localhost:8000/api/sensors/purple-air \
  -H "Content-Type: application/json" \
  -d '{
    "ip_address": "192.168.1.100",
    "name": "Dev Test Sensor",
    "location": "Development Lab"
  }'
```

---

## Project Structure

```
sensor-data-collector/
│
├── README.md                         # Main documentation
├── docs/                             # Additional documentation
│   ├── API.md                        # API reference
│   ├── ARCHITECTURE.md               # Architecture details
│   ├── DEPLOYMENT.md                 # Deployment guide
│   └── DEVELOPMENT.md                # This file
│
├── frontend/                         # Frontend (to be built)
│   └── FRONTEND_REQUIREMENTS.md      # Frontend specs
│
└── backend/                          # Backend application
    ├── app/                          # Main application package
    │   ├── __init__.py
    │   ├── main.py                   # FastAPI app entry point
    │   │
    │   ├── models/                   # Data models
    │   │   ├── __init__.py
    │   │   └── sensor.py             # Pydantic models
    │   │
    │   ├── routers/                  # API routes
    │   │   ├── __init__.py
    │   │   ├── sensors.py            # Sensor endpoints
    │   │   └── test_upload.py        # Test endpoint
    │   │
    │   └── services/                 # Business logic
    │       ├── __init__.py
    │       ├── sensor_manager.py     # Sensor coordination
    │       ├── purple_air_service.py # Purple Air integration
    │       └── tempest_service.py    # Tempest integration
    │
    ├── requirements.txt              # Python dependencies
    ├── env.example.txt              # Environment template
    ├── .gitignore                    # Git ignore rules
    └── venv/                         # Virtual environment (not in git)
```

---

## Code Style & Standards

### Python Style Guide

**Follow PEP 8 with these guidelines:**

1. **Line Length:** 88 characters (Black default)
2. **Imports:** Organized in three groups (standard lib, third-party, local)
3. **Type Hints:** Use throughout
4. **Docstrings:** Google style for classes and public methods
5. **Naming:**
   - Classes: `PascalCase`
   - Functions/methods: `snake_case`
   - Constants: `UPPER_SNAKE_CASE`
   - Private: `_leading_underscore`

### Example Code Style

```python
"""
Module docstring: Brief description of module.

Detailed explanation if needed.
"""

import os
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.models import SensorResponse
from app.services import SensorManager


class MySensorService:
    """
    Service for managing My Sensor operations.
    
    This class handles data fetching, parsing, and uploading
    for My Sensor devices.
    
    Attributes:
        endpoint_url: URL for data upload
        token: Authentication token
    """
    
    def __init__(self, endpoint_url: str, token: str):
        """
        Initialize the service.
        
        Args:
            endpoint_url: External endpoint URL
            token: Bearer token for authentication
        """
        self.endpoint_url = endpoint_url
        self.token = token
    
    async def fetch_data(self, ip_address: str) -> dict:
        """
        Fetch data from sensor.
        
        Args:
            ip_address: Sensor IP address
            
        Returns:
            Raw sensor data as dictionary
            
        Raises:
            httpx.ConnectError: If sensor is unreachable
        """
        # Implementation
        pass
```

### Formatting Tools

```bash
# Format code with Black
black app/

# Check style with Flake8
flake8 app/

# Type checking with MyPy
mypy app/
```

### Pre-commit Setup (Recommended)

Create `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.3.0
    hooks:
      - id: black
        language_version: python3.11

  - repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
      - id: flake8

  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.4.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
```

```bash
# Install pre-commit
pip install pre-commit

# Install hooks
pre-commit install

# Run manually
pre-commit run --all-files
```

---

## Adding New Sensor Types

### Step-by-Step Guide

Let's add support for a hypothetical "AcmeWeather" sensor.

#### 1. Define Data Model

In `app/models/sensor.py`:

```python
# Add to SensorType enum
class SensorType(str, Enum):
    PURPLE_AIR = "purple_air"
    TEMPEST = "tempest"
    ACME_WEATHER = "acme_weather"  # New!
    # ...

# Add reading model
class AcmeWeatherReading(BaseModel):
    """Data model for AcmeWeather sensor reading."""
    
    timestamp: datetime = Field(..., description="Reading timestamp")
    temperature_c: float = Field(..., description="Temperature in Celsius")
    humidity_percent: float = Field(..., description="Relative humidity")
    pressure_kpa: float = Field(..., description="Pressure in kPa")
    
    def to_csv_row(self) -> str:
        """Convert to CSV row."""
        return (
            f"{self.timestamp.isoformat()},"
            f"{self.temperature_c},"
            f"{self.humidity_percent},"
            f"{self.pressure_kpa}"
        )
    
    @staticmethod
    def csv_header() -> str:
        """Return CSV header."""
        return "Timestamp,Temperature (°C),Humidity (%),Pressure (kPa)"

# Add request model
class AddAcmeWeatherSensorRequest(BaseModel):
    """Request to add AcmeWeather sensor."""
    
    ip_address: str = Field(..., description="Sensor IP address")
    name: str = Field(..., min_length=1, max_length=100)
    location: str = Field(..., min_length=1, max_length=200)
    api_key: str = Field(..., description="Sensor API key")
```

#### 2. Create Service

Create `app/services/acme_weather_service.py`:

```python
"""
AcmeWeather Sensor Service
==========================
Service for AcmeWeather sensor data collection.
"""

import httpx
import io
from datetime import datetime, timezone

from app.models import AcmeWeatherReading


class AcmeWeatherService:
    """
    Service for AcmeWeather sensor operations.
    
    Handles fetching, parsing, and uploading data from
    AcmeWeather sensors.
    """
    
    def __init__(
        self,
        external_endpoint_url: str,
        external_endpoint_token: str,
        request_timeout: float = 10.0
    ):
        """Initialize service."""
        self.external_endpoint_url = external_endpoint_url
        self.external_endpoint_token = external_endpoint_token
        self.http_client = httpx.AsyncClient(timeout=request_timeout)
    
    async def fetch_sensor_data(
        self, 
        ip_address: str, 
        api_key: str
    ) -> dict:
        """
        Fetch data from AcmeWeather sensor.
        
        Args:
            ip_address: Sensor IP
            api_key: Sensor API key
            
        Returns:
            Raw JSON response
        """
        url = f"http://{ip_address}/api/data"
        headers = {"X-API-Key": api_key}
        
        response = await self.http_client.get(url, headers=headers)
        response.raise_for_status()
        
        return response.json()
    
    def parse_sensor_response(self, raw_data: dict) -> AcmeWeatherReading:
        """Parse raw JSON into reading model."""
        return AcmeWeatherReading(
            timestamp=datetime.fromisoformat(raw_data["timestamp"]),
            temperature_c=float(raw_data["temp"]),
            humidity_percent=float(raw_data["humidity"]),
            pressure_kpa=float(raw_data["pressure"])
        )
    
    def convert_to_csv(
        self,
        reading: AcmeWeatherReading,
        include_header: bool = True
    ) -> str:
        """Convert reading to CSV format."""
        lines = []
        
        if include_header:
            lines.append(AcmeWeatherReading.csv_header())
        
        lines.append(reading.to_csv_row())
        
        return "\n".join(lines)
    
    async def push_to_endpoint(
        self,
        csv_data: str,
        sensor_name: str
    ) -> dict:
        """Upload CSV to external endpoint."""
        headers = {
            "Authorization": f"Bearer {self.external_endpoint_token}"
        }
        
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        clean_name = "".join(c if c.isalnum() else "_" for c in sensor_name)
        filename = f"{clean_name}_{timestamp}.csv"
        
        csv_bytes = csv_data.encode("utf-8")
        csv_file = io.BytesIO(csv_bytes)
        
        files = {"file": (filename, csv_file, "text/csv")}
        
        response = await self.http_client.post(
            self.external_endpoint_url,
            headers=headers,
            files=files
        )
        response.raise_for_status()
        
        return {
            "status": "success",
            "filename": filename,
            "uploaded_at": datetime.now(timezone.utc).isoformat()
        }
    
    async def fetch_and_push(
        self,
        ip_address: str,
        api_key: str,
        sensor_name: str
    ) -> dict:
        """
        Complete pipeline: fetch → parse → convert → upload.
        
        Returns:
            Result dict with status, reading, upload_result, or error
        """
        try:
            raw_data = await self.fetch_sensor_data(ip_address, api_key)
            reading = self.parse_sensor_response(raw_data)
            csv_data = self.convert_to_csv(reading, include_header=True)
            upload_result = await self.push_to_endpoint(csv_data, sensor_name)
            
            return {
                "status": "success",
                "sensor_name": sensor_name,
                "reading": reading.model_dump(),
                "upload_result": upload_result
            }
        
        except httpx.ConnectError as e:
            return {
                "status": "error",
                "sensor_name": sensor_name,
                "error_type": "connection_error",
                "error_message": f"Cannot connect: {str(e)}"
            }
        except Exception as e:
            return {
                "status": "error",
                "sensor_name": sensor_name,
                "error_type": "unknown_error",
                "error_message": str(e)
            }
    
    async def close(self):
        """Close HTTP client."""
        await self.http_client.aclose()
```

#### 3. Update Sensor Manager

In `app/services/sensor_manager.py`:

```python
# Import new service
from app.services.acme_weather_service import AcmeWeatherService

class SensorManager:
    def __init__(
        self,
        purple_air_service: PurpleAirService,
        tempest_service: TempestService,
        acme_weather_service: AcmeWeatherService,  # Add parameter
        polling_interval: int = 60
    ):
        self.purple_air_service = purple_air_service
        self.tempest_service = tempest_service
        self.acme_weather_service = acme_weather_service  # Store
        # ...
    
    # Add registration method
    def add_acme_weather_sensor(
        self,
        request: AddAcmeWeatherSensorRequest
    ) -> SensorResponse:
        """Register a new AcmeWeather sensor."""
        sensor_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        
        sensor_data = {
            "id": sensor_id,
            "sensor_type": SensorType.ACME_WEATHER,
            "name": request.name,
            "location": request.location,
            "ip_address": request.ip_address,
            "api_key": request.api_key,  # Store API key
            "status": SensorStatus.INACTIVE,
            "is_active": False,
            "last_active": None,
            "last_error": None,
            "created_at": now,
        }
        
        self._sensors[sensor_id] = sensor_data
        return SensorResponse(**sensor_data)
    
    # Update turn_on to handle new type
    async def turn_on_sensor(self, sensor_id: str):
        # ...
        if sensor["sensor_type"] == SensorType.ACME_WEATHER:
            self._start_polling_job(
                sensor_id=sensor_id,
                callback=self._poll_acme_weather_sensor
            )
        # ...
    
    # Add polling callback
    async def _poll_acme_weather_sensor(self, sensor_id: str):
        """Polling callback for AcmeWeather sensors."""
        sensor = self._sensors.get(sensor_id)
        if not sensor:
            return
        
        result = await self.acme_weather_service.fetch_and_push(
            sensor["ip_address"],
            sensor["api_key"],
            sensor["name"]
        )
        
        if result["status"] == "success":
            sensor["status"] = SensorStatus.ACTIVE
            sensor["last_active"] = datetime.now(timezone.utc)
            sensor["last_error"] = None
        else:
            sensor["status"] = SensorStatus.ERROR
            sensor["last_error"] = result.get("error_message")
    
    # Update trigger_fetch_now
    async def trigger_fetch_now(self, sensor_id: str) -> dict:
        # ...
        if sensor["sensor_type"] == SensorType.ACME_WEATHER:
            result = await self.acme_weather_service.fetch_and_push(
                sensor["ip_address"],
                sensor["api_key"],
                sensor["name"]
            )
        # ...
    
    # Update shutdown
    async def shutdown(self):
        await self.purple_air_service.close()
        await self.tempest_service.close()
        await self.acme_weather_service.close()  # Add
```

#### 4. Initialize Service in main.py

In `app/main.py`:

```python
from app.services import AcmeWeatherService

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ... existing services ...
    
    # Initialize AcmeWeather service
    acme_weather_service = AcmeWeatherService(
        external_endpoint_url=Config.EXTERNAL_ENDPOINT_URL,
        external_endpoint_token=Config.EXTERNAL_ENDPOINT_TOKEN
    )
    
    # Initialize sensor manager with new service
    sensor_manager = SensorManager(
        purple_air_service=purple_air_service,
        tempest_service=tempest_service,
        acme_weather_service=acme_weather_service,  # Add
        polling_interval=Config.POLLING_INTERVAL
    )
    
    # ...
```

#### 5. Add API Endpoints

In `app/routers/sensors.py`:

```python
from app.models import AddAcmeWeatherSensorRequest

@router.post(
    "/acme-weather",
    response_model=SensorResponse,
    summary="Add AcmeWeather Sensor"
)
async def add_acme_weather_sensor(
    request: AddAcmeWeatherSensorRequest,
    manager = Depends(get_sensor_manager)
):
    """Add a new AcmeWeather sensor."""
    # Validate IP
    parts = request.ip_address.split(".")
    if len(parts) != 4:
        raise HTTPException(400, "Invalid IP address")
    
    return manager.add_acme_weather_sensor(request)

@router.get(
    "/acme-weather",
    response_model=SensorListResponse,
    summary="List AcmeWeather Sensors"
)
async def get_all_acme_weather_sensors(
    manager = Depends(get_sensor_manager)
):
    """Get all AcmeWeather sensors."""
    sensors = manager.get_all_sensors(SensorType.ACME_WEATHER)
    return SensorListResponse(sensors=sensors, total=len(sensors))
```

#### 6. Test Your Implementation

```bash
# Start server
uvicorn app.main:app --reload

# Add sensor
curl -X POST http://localhost:8000/api/sensors/acme-weather \
  -H "Content-Type: application/json" \
  -d '{
    "ip_address": "192.168.1.200",
    "name": "Test AcmeWeather",
    "location": "Lab",
    "api_key": "test-key-123"
  }'

# Turn on
curl -X POST http://localhost:8000/api/sensors/{id}/turn-on

# Manual fetch
curl -X POST http://localhost:8000/api/sensors/{id}/fetch-now
```

---

## Testing

### Unit Testing

Create `tests/test_acme_weather_service.py`:

```python
import pytest
from unittest.mock import Mock, AsyncMock
from app.services.acme_weather_service import AcmeWeatherService


@pytest.mark.asyncio
async def test_fetch_sensor_data():
    """Test fetching data from sensor."""
    service = AcmeWeatherService(
        external_endpoint_url="http://test.com",
        external_endpoint_token="test-token"
    )
    
    # Mock HTTP client
    service.http_client.get = AsyncMock(
        return_value=Mock(
            json=lambda: {
                "timestamp": "2026-01-05T12:00:00Z",
                "temp": 20.5,
                "humidity": 60.0,
                "pressure": 101.3
            }
        )
    )
    
    # Test
    data = await service.fetch_sensor_data("192.168.1.100", "key-123")
    
    assert data["temp"] == 20.5
    assert data["humidity"] == 60.0


@pytest.mark.asyncio
async def test_parse_sensor_response():
    """Test parsing raw sensor data."""
    service = AcmeWeatherService("http://test.com", "test-token")
    
    raw_data = {
        "timestamp": "2026-01-05T12:00:00Z",
        "temp": 20.5,
        "humidity": 60.0,
        "pressure": 101.3
    }
    
    reading = service.parse_sensor_response(raw_data)
    
    assert reading.temperature_c == 20.5
    assert reading.humidity_percent == 60.0


def test_convert_to_csv():
    """Test CSV conversion."""
    from app.models import AcmeWeatherReading
    from datetime import datetime, timezone
    
    reading = AcmeWeatherReading(
        timestamp=datetime(2026, 1, 5, 12, 0, 0, tzinfo=timezone.utc),
        temperature_c=20.5,
        humidity_percent=60.0,
        pressure_kpa=101.3
    )
    
    service = AcmeWeatherService("http://test.com", "test-token")
    csv = service.convert_to_csv(reading)
    
    assert "Timestamp,Temperature" in csv
    assert "20.5,60.0,101.3" in csv
```

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio pytest-cov

# Run all tests
pytest

# Run with coverage
pytest --cov=app tests/

# Run specific test file
pytest tests/test_acme_weather_service.py

# Run specific test
pytest tests/test_acme_weather_service.py::test_fetch_sensor_data
```

---

## Debugging

### VS Code Debug Configuration

Create `.vscode/launch.json`:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "FastAPI",
      "type": "python",
      "request": "launch",
      "module": "uvicorn",
      "args": [
        "app.main:app",
        "--reload",
        "--port",
        "8000"
      ],
      "jinja": true,
      "justMyCode": false,
      "envFile": "${workspaceFolder}/backend/.env",
      "cwd": "${workspaceFolder}/backend"
    }
  ]
}
```

### Logging

Add logging to your code:

```python
import logging

logger = logging.getLogger(__name__)

# In your functions
logger.debug("Fetching data from sensor at %s", ip_address)
logger.info("Successfully uploaded data for sensor %s", sensor_name)
logger.error("Failed to connect to sensor: %s", str(e))
```

Configure in `main.py`:

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
```

---

## Git Workflow

### Branch Strategy

```bash
# Create feature branch
git checkout -b feature/add-acme-weather-sensor

# Make changes
git add .
git commit -m "Add support for AcmeWeather sensors"

# Push to your fork
git push origin feature/add-acme-weather-sensor

# Create pull request on GitHub
```

### Commit Message Guidelines

```
<type>: <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Formatting
- `refactor`: Code restructuring
- `test`: Adding tests
- `chore`: Maintenance

**Examples:**
```
feat: add support for AcmeWeather sensors

- Add AcmeWeatherReading model
- Create AcmeWeatherService
- Add API endpoints
- Update sensor manager

Closes #123
```

---

## Contributing Guidelines

1. **Fork the repository**
2. **Create a feature branch**
3. **Write code following style guide**
4. **Add tests for new functionality**
5. **Update documentation**
6. **Ensure all tests pass**
7. **Submit pull request**

### Pull Request Checklist

- [ ] Code follows style guide
- [ ] Tests added and passing
- [ ] Documentation updated
- [ ] Commit messages are clear
- [ ] No merge conflicts
- [ ] PR description explains changes

---

## Common Development Tasks

### Add New API Endpoint

1. Define route in `app/routers/sensors.py`
2. Add request/response models if needed
3. Update API documentation
4. Test endpoint

### Modify CSV Format

1. Update model's `to_csv_row()` method
2. Update `csv_header()` method
3. Test with external endpoint
4. Update documentation

### Change Polling Interval

```python
# In .env
POLLING_INTERVAL=30  # seconds

# Or programmatically in code
sensor_manager = SensorManager(
    ...,
    polling_interval=30
)
```

### Add New Environment Variable

1. Add to `env.example.txt`
2. Add to `Config` class in `main.py`
3. Use in code
4. Document in README

---

## Performance Optimization

### Profiling

```bash
# Install profiler
pip install py-spy

# Profile running application
py-spy top --pid <uvicorn-pid>

# Generate flame graph
py-spy record -o profile.svg --pid <uvicorn-pid>
```

### Optimization Tips

1. **Use async/await throughout**
2. **Connection pooling** (already via HTTPX)
3. **Cache sensor data** if appropriate
4. **Batch uploads** for multiple sensors
5. **Increase polling interval** for many sensors

---

## Troubleshooting

### Import Errors

```bash
# Ensure virtual environment is activated
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt

# Check Python path
python -c "import sys; print(sys.path)"
```

### Type Errors with MyPy

```bash
# Run mypy
mypy app/

# Ignore specific errors (if needed)
# type: ignore
```

### Tests Failing

```bash
# Run with verbose output
pytest -v

# Run with print statements
pytest -s

# Debug specific test
pytest -k test_name -v -s
```

---

**Last Updated:** January 2026

