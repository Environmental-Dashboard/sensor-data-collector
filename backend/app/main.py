"""
Sensor Data Collector - Backend API
====================================
FastAPI application for managing environmental sensor data collection.

ARCHITECTURE:
    This backend runs on a LOCAL machine on the same network as the sensors.
    It is exposed to the internet via Cloudflare Tunnel so that a hosted
    frontend can communicate with it.

    [Hosted Frontend] --HTTPS--> [Cloudflare Tunnel] ---> [This Backend]
                                                                |
                                                                v
                                                    [Sensors on Local Network]
                                                                |
                                                                v
                                                    [External CSV Endpoint]

SUPPORTED SENSORS:
    1. Purple Air - Air quality sensors (PM2.5, temperature, humidity, pressure)
    2. Tempest - WeatherFlow weather stations (temp, humidity, wind, rain, UV)
    3. Water Quality - Water quality sensors (not yet implemented)
    4. Mayfly - Mayfly dataloggers (not yet implemented)

HOW TO RUN:
    # Install dependencies
    cd backend
    python -m venv venv
    source venv/bin/activate  # Windows: venv\\Scripts\\activate
    pip install -r requirements.txt
    
    # Copy environment config
    cp env.example.txt .env
    # Edit .env with your settings
    
    # Run the server
    uvicorn app.main:app --reload --port 8000
    
    # Expose via Cloudflare Tunnel (in another terminal)
    cloudflared tunnel --url http://localhost:8000

API DOCUMENTATION:
    After starting the server, visit:
    - Swagger UI: http://localhost:8000/docs
    - ReDoc: http://localhost:8000/redoc
    - OpenAPI JSON: http://localhost:8000/openapi.json

Author: Sensor Data Collector Team
"""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from app.routers import sensors_router, test_upload_router, set_sensor_manager
from app.services import PurpleAirService, TempestService, SensorManager


# Load environment variables from .env file
load_dotenv()


# =============================================================================
# CONFIGURATION
# =============================================================================

class Config:
    """
    Application configuration loaded from environment variables.
    
    Environment Variables:
        EXTERNAL_ENDPOINT_URL: URL to push CSV data to
        EXTERNAL_ENDPOINT_TOKEN: Auth token for external endpoint
        POLLING_INTERVAL: Seconds between sensor polls (default: 60)
        FRONTEND_URL: URL of the frontend for CORS
    
    Defaults are set for local development with the test endpoint.
    """
    
    # External endpoint for CSV upload
    # Default: Use local test endpoint
    EXTERNAL_ENDPOINT_URL = os.getenv(
        "EXTERNAL_ENDPOINT_URL",
        "http://localhost:8000/api/test/upload/csv"
    )
    
    # Auth token for external endpoint
    # Default: Test API key (matches test_upload.py)
    EXTERNAL_ENDPOINT_TOKEN = os.getenv(
        "EXTERNAL_ENDPOINT_TOKEN",
        "test-sensor-api-key-12345"
    )
    
    # Polling interval in seconds
    POLLING_INTERVAL = int(os.getenv("POLLING_INTERVAL", "60"))
    
    # Frontend URL for CORS
    FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
    
    # Allowed CORS origins
    # Add your frontend URLs here
    CORS_ORIGINS = [
        FRONTEND_URL,
        "http://localhost:5173",    # Vite dev server
        "http://localhost:3000",    # Create React App
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
        # Add your production frontend URL here
    ]


# =============================================================================
# APPLICATION LIFESPAN
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.
    
    STARTUP:
        1. Initialize sensor services (PurpleAir, Tempest)
        2. Initialize SensorManager with services
        3. Inject manager into routers
        4. Print startup information
    
    SHUTDOWN:
        1. Stop all polling jobs
        2. Close HTTP clients
        3. Cleanup resources
    """
    # ========== STARTUP ==========
    print("=" * 60)
    print("🚀 SENSOR DATA COLLECTOR - Starting Backend")
    print("=" * 60)
    
    # Initialize Purple Air service
    purple_air_service = PurpleAirService(
        external_endpoint_url=Config.EXTERNAL_ENDPOINT_URL,
        external_endpoint_token=Config.EXTERNAL_ENDPOINT_TOKEN
    )
    
    # Initialize Tempest service
    tempest_service = TempestService(
        external_endpoint_url=Config.EXTERNAL_ENDPOINT_URL,
        external_endpoint_token=Config.EXTERNAL_ENDPOINT_TOKEN
    )
    
    # Initialize sensor manager
    sensor_manager = SensorManager(
        purple_air_service=purple_air_service,
        tempest_service=tempest_service,
        polling_interval=Config.POLLING_INTERVAL
    )
    
    # Inject into routers
    set_sensor_manager(sensor_manager)
    
    # Print configuration
    print(f"✅ Services initialized")
    print(f"   Polling interval: {Config.POLLING_INTERVAL} seconds")
    print(f"   External endpoint: {Config.EXTERNAL_ENDPOINT_URL}")
    print(f"   CORS origins: {len(Config.CORS_ORIGINS)} configured")
    print()
    print("📡 Supported Sensors:")
    print("   - Purple Air (air quality)")
    print("   - Tempest (weather)")
    print("   - Water Quality (coming soon)")
    print("   - Mayfly (coming soon)")
    print()
    print("📖 API Documentation: http://localhost:8000/docs")
    print("=" * 60)
    
    yield  # Application runs here
    
    # ========== SHUTDOWN ==========
    print()
    print("🛑 Shutting down...")
    await sensor_manager.shutdown()
    print("✅ Shutdown complete")


# =============================================================================
# CREATE FASTAPI APPLICATION
# =============================================================================

app = FastAPI(
    title="Sensor Data Collector API",
    description="""
## Overview

Backend API for collecting data from environmental sensors on a local network
and pushing it to an external endpoint.

## How It Works

1. **Add a sensor** - Register a sensor with its local IP address
2. **Turn it on** - Start automatic data collection
3. **Data flows** - Every 60 seconds:
   - Backend fetches JSON from sensor via local IP
   - Converts to CSV format
   - Pushes to external endpoint

## Supported Sensor Types

| Type | Status | Data Collected |
|------|--------|----------------|
| **Purple Air** | ✅ Ready | PM2.5, PM10, Temperature, Humidity, Pressure |
| **Tempest** | ✅ Ready | Temperature, Humidity, Wind, Rain, UV, Lightning |
| **Water Quality** | 🚧 Coming | TBD |
| **Mayfly** | 🚧 Coming | TBD |

## Authentication

- Sensor management endpoints are open (add auth as needed)
- The test upload endpoint requires: `Authorization: Bearer test-sensor-api-key-12345`

## Frontend Integration

This backend is designed to be accessed via Cloudflare Tunnel by a hosted frontend.
Set the `FRONTEND_URL` environment variable to enable CORS.
    """,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)


# =============================================================================
# CORS MIDDLEWARE
# =============================================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=Config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# INCLUDE ROUTERS
# =============================================================================

# Sensor management endpoints
app.include_router(sensors_router)

# Test upload endpoint (for local testing)
app.include_router(test_upload_router)


# =============================================================================
# ROOT ENDPOINTS
# =============================================================================

@app.get(
    "/",
    summary="API Information",
    description="Get basic API information and available endpoints."
)
async def root():
    """
    Root endpoint with API overview.
    
    Returns links to all available endpoints.
    """
    return {
        "name": "Sensor Data Collector API",
        "version": "1.0.0",
        "documentation": {
            "swagger": "/docs",
            "redoc": "/redoc",
            "openapi": "/openapi.json"
        },
        "endpoints": {
            "all_sensors": "GET /api/sensors",
            "purple_air": {
                "list": "GET /api/sensors/purple-air",
                "add": "POST /api/sensors/purple-air"
            },
            "tempest": {
                "list": "GET /api/sensors/tempest",
                "add": "POST /api/sensors/tempest"
            },
            "water_quality": {
                "list": "GET /api/sensors/water-quality",
                "add": "POST /api/sensors/water-quality (not implemented)"
            },
            "mayfly": {
                "list": "GET /api/sensors/mayfly",
                "add": "POST /api/sensors/mayfly (not implemented)"
            },
            "sensor_actions": {
                "get": "GET /api/sensors/{id}",
                "delete": "DELETE /api/sensors/{id}",
                "status": "GET /api/sensors/{id}/status",
                "turn_on": "POST /api/sensors/{id}/turn-on",
                "turn_off": "POST /api/sensors/{id}/turn-off",
                "fetch_now": "POST /api/sensors/{id}/fetch-now"
            },
            "test_upload": "POST /api/test/upload/csv"
        }
    }


@app.get(
    "/health",
    summary="Health Check",
    description="Check if the backend is running."
)
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "polling_interval": Config.POLLING_INTERVAL,
        "external_endpoint": Config.EXTERNAL_ENDPOINT_URL
    }

====================================
FastAPI application for managing environmental sensor data collection.

ARCHITECTURE:
    This backend runs on a LOCAL machine on the same network as the sensors.
    It is exposed to the internet via Cloudflare Tunnel so that a hosted
    frontend can communicate with it.

    [Hosted Frontend] --HTTPS--> [Cloudflare Tunnel] ---> [This Backend]
                                                                |
                                                                v
                                                    [Sensors on Local Network]
                                                                |
                                                                v
                                                    [External CSV Endpoint]

SUPPORTED SENSORS:
    1. Purple Air - Air quality sensors (PM2.5, temperature, humidity, pressure)
    2. Tempest - WeatherFlow weather stations (temp, humidity, wind, rain, UV)
    3. Water Quality - Water quality sensors (not yet implemented)
    4. Mayfly - Mayfly dataloggers (not yet implemented)

HOW TO RUN:
    # Install dependencies
    cd backend
    python -m venv venv
    source venv/bin/activate  # Windows: venv\\Scripts\\activate
    pip install -r requirements.txt
    
    # Copy environment config
    cp env.example.txt .env
    # Edit .env with your settings
    
    # Run the server
    uvicorn app.main:app --reload --port 8000
    
    # Expose via Cloudflare Tunnel (in another terminal)
    cloudflared tunnel --url http://localhost:8000

API DOCUMENTATION:
    After starting the server, visit:
    - Swagger UI: http://localhost:8000/docs
    - ReDoc: http://localhost:8000/redoc
    - OpenAPI JSON: http://localhost:8000/openapi.json

Author: Sensor Data Collector Team
"""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from app.routers import sensors_router, test_upload_router, set_sensor_manager
from app.services import PurpleAirService, TempestService, SensorManager


# Load environment variables from .env file
load_dotenv()


# =============================================================================
# CONFIGURATION
# =============================================================================

class Config:
    """
    Application configuration loaded from environment variables.
    
    Environment Variables:
        EXTERNAL_ENDPOINT_URL: URL to push CSV data to
        EXTERNAL_ENDPOINT_TOKEN: Auth token for external endpoint
        POLLING_INTERVAL: Seconds between sensor polls (default: 60)
        FRONTEND_URL: URL of the frontend for CORS
    
    Defaults are set for local development with the test endpoint.
    """
    
    # External endpoint for CSV upload
    # Default: Use local test endpoint
    EXTERNAL_ENDPOINT_URL = os.getenv(
        "EXTERNAL_ENDPOINT_URL",
        "http://localhost:8000/api/test/upload/csv"
    )
    
    # Auth token for external endpoint
    # Default: Test API key (matches test_upload.py)
    EXTERNAL_ENDPOINT_TOKEN = os.getenv(
        "EXTERNAL_ENDPOINT_TOKEN",
        "test-sensor-api-key-12345"
    )
    
    # Polling interval in seconds
    POLLING_INTERVAL = int(os.getenv("POLLING_INTERVAL", "60"))
    
    # Frontend URL for CORS
    FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
    
    # Allowed CORS origins
    # Add your frontend URLs here
    CORS_ORIGINS = [
        FRONTEND_URL,
        "http://localhost:5173",    # Vite dev server
        "http://localhost:3000",    # Create React App
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
        # Add your production frontend URL here
    ]


# =============================================================================
# APPLICATION LIFESPAN
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.
    
    STARTUP:
        1. Initialize sensor services (PurpleAir, Tempest)
        2. Initialize SensorManager with services
        3. Inject manager into routers
        4. Print startup information
    
    SHUTDOWN:
        1. Stop all polling jobs
        2. Close HTTP clients
        3. Cleanup resources
    """
    # ========== STARTUP ==========
    print("=" * 60)
    print("🚀 SENSOR DATA COLLECTOR - Starting Backend")
    print("=" * 60)
    
    # Initialize Purple Air service
    purple_air_service = PurpleAirService(
        external_endpoint_url=Config.EXTERNAL_ENDPOINT_URL,
        external_endpoint_token=Config.EXTERNAL_ENDPOINT_TOKEN
    )
    
    # Initialize Tempest service
    tempest_service = TempestService(
        external_endpoint_url=Config.EXTERNAL_ENDPOINT_URL,
        external_endpoint_token=Config.EXTERNAL_ENDPOINT_TOKEN
    )
    
    # Initialize sensor manager
    sensor_manager = SensorManager(
        purple_air_service=purple_air_service,
        tempest_service=tempest_service,
        polling_interval=Config.POLLING_INTERVAL
    )
    
    # Inject into routers
    set_sensor_manager(sensor_manager)
    
    # Print configuration
    print(f"✅ Services initialized")
    print(f"   Polling interval: {Config.POLLING_INTERVAL} seconds")
    print(f"   External endpoint: {Config.EXTERNAL_ENDPOINT_URL}")
    print(f"   CORS origins: {len(Config.CORS_ORIGINS)} configured")
    print()
    print("📡 Supported Sensors:")
    print("   - Purple Air (air quality)")
    print("   - Tempest (weather)")
    print("   - Water Quality (coming soon)")
    print("   - Mayfly (coming soon)")
    print()
    print("📖 API Documentation: http://localhost:8000/docs")
    print("=" * 60)
    
    yield  # Application runs here
    
    # ========== SHUTDOWN ==========
    print()
    print("🛑 Shutting down...")
    await sensor_manager.shutdown()
    print("✅ Shutdown complete")


# =============================================================================
# CREATE FASTAPI APPLICATION
# =============================================================================

app = FastAPI(
    title="Sensor Data Collector API",
    description="""
## Overview

Backend API for collecting data from environmental sensors on a local network
and pushing it to an external endpoint.

## How It Works

1. **Add a sensor** - Register a sensor with its local IP address
2. **Turn it on** - Start automatic data collection
3. **Data flows** - Every 60 seconds:
   - Backend fetches JSON from sensor via local IP
   - Converts to CSV format
   - Pushes to external endpoint

## Supported Sensor Types

| Type | Status | Data Collected |
|------|--------|----------------|
| **Purple Air** | ✅ Ready | PM2.5, PM10, Temperature, Humidity, Pressure |
| **Tempest** | ✅ Ready | Temperature, Humidity, Wind, Rain, UV, Lightning |
| **Water Quality** | 🚧 Coming | TBD |
| **Mayfly** | 🚧 Coming | TBD |

## Authentication

- Sensor management endpoints are open (add auth as needed)
- The test upload endpoint requires: `Authorization: Bearer test-sensor-api-key-12345`

## Frontend Integration

This backend is designed to be accessed via Cloudflare Tunnel by a hosted frontend.
Set the `FRONTEND_URL` environment variable to enable CORS.
    """,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)


# =============================================================================
# CORS MIDDLEWARE
# =============================================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=Config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# INCLUDE ROUTERS
# =============================================================================

# Sensor management endpoints
app.include_router(sensors_router)

# Test upload endpoint (for local testing)
app.include_router(test_upload_router)


# =============================================================================
# ROOT ENDPOINTS
# =============================================================================

@app.get(
    "/",
    summary="API Information",
    description="Get basic API information and available endpoints."
)
async def root():
    """
    Root endpoint with API overview.
    
    Returns links to all available endpoints.
    """
    return {
        "name": "Sensor Data Collector API",
        "version": "1.0.0",
        "documentation": {
            "swagger": "/docs",
            "redoc": "/redoc",
            "openapi": "/openapi.json"
        },
        "endpoints": {
            "all_sensors": "GET /api/sensors",
            "purple_air": {
                "list": "GET /api/sensors/purple-air",
                "add": "POST /api/sensors/purple-air"
            },
            "tempest": {
                "list": "GET /api/sensors/tempest",
                "add": "POST /api/sensors/tempest"
            },
            "water_quality": {
                "list": "GET /api/sensors/water-quality",
                "add": "POST /api/sensors/water-quality (not implemented)"
            },
            "mayfly": {
                "list": "GET /api/sensors/mayfly",
                "add": "POST /api/sensors/mayfly (not implemented)"
            },
            "sensor_actions": {
                "get": "GET /api/sensors/{id}",
                "delete": "DELETE /api/sensors/{id}",
                "status": "GET /api/sensors/{id}/status",
                "turn_on": "POST /api/sensors/{id}/turn-on",
                "turn_off": "POST /api/sensors/{id}/turn-off",
                "fetch_now": "POST /api/sensors/{id}/fetch-now"
            },
            "test_upload": "POST /api/test/upload/csv"
        }
    }


@app.get(
    "/health",
    summary="Health Check",
    description="Check if the backend is running."
)
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "polling_interval": Config.POLLING_INTERVAL,
        "external_endpoint": Config.EXTERNAL_ENDPOINT_URL
    }
