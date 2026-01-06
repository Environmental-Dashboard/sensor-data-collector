"""
Sensor Data Collector - Backend
================================

Hey! Welcome to the backend. This is the heart of our sensor collection system.

WHAT DOES THIS APP DO?
---------------------
1. Manages sensors (add, delete, turn on/off)
2. Automatically collects data from sensors every 60 seconds
3. Converts data to CSV and uploads to the cloud

HOW TO RUN THIS:
---------------
    cd backend
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    uvicorn app.main:app --reload --port 8000

Then open http://localhost:8000/docs to see the API documentation!

FOR REMOTE ACCESS (Frontend on a different server):
-------------------------------------------------
Install cloudflared and run:
    cloudflared tunnel --url http://localhost:8000

This gives you a public URL that the frontend can use.

Author: Frank Kusi Appiah
"""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from app.routers import sensors_router, set_sensor_manager
from app.services import PurpleAirService, TempestService, SensorManager


# Load environment variables from .env file (if it exists)
load_dotenv()


# =============================================================================
# CONFIGURATION
# =============================================================================

class Config:
    """
    App settings - loaded from environment variables.
    
    You can set these in a .env file or as system environment variables.
    """
    
    # How often to fetch data from sensors (in seconds)
    # Default: 60 seconds (1 minute)
    POLLING_INTERVAL = int(os.getenv("POLLING_INTERVAL", "60"))
    
    # Frontend URL(s) for CORS
    # CORS = Cross-Origin Resource Sharing
    # This allows the frontend (on a different server) to talk to us
    FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
    
    # All allowed origins (add your frontend URL here!)
    CORS_ORIGINS = [
        FRONTEND_URL,
        "http://localhost:5173",    # Vite dev server
        "http://localhost:3000",    # Create React App
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
        # Add your production frontend URL here when you deploy!
    ]


# =============================================================================
# APPLICATION STARTUP & SHUTDOWN
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    This runs when the app starts and stops.
    
    STARTUP:
    - Create the services (Purple Air, Tempest)
    - Create the manager
    - Connect everything together
    
    SHUTDOWN:
    - Stop all polling jobs
    - Close network connections
    """
    
    # ========== STARTUP ==========
    print()
    print("=" * 60)
    print("🚀 SENSOR DATA COLLECTOR")
    print("=" * 60)
    
    # Create services
    purple_air_service = PurpleAirService()
    tempest_service = TempestService()
    
    # Create the manager
    sensor_manager = SensorManager(
        purple_air_service=purple_air_service,
        tempest_service=tempest_service,
        polling_interval=Config.POLLING_INTERVAL
    )
    
    # Give the router access to the manager
    set_sensor_manager(sensor_manager)
    
    print(f"✅ Ready to go!")
    print(f"   Polling every {Config.POLLING_INTERVAL} seconds")
    print(f"   Data uploads to: oberlin.communityhub.cloud")
    print()
    print("📡 Supported Sensors:")
    print("   ✅ Purple Air (air quality)")
    print("   ✅ Tempest (weather)")
    print("   🚧 Water Quality (coming soon)")
    print("   🚧 Mayfly (coming soon)")
    print()
    print("📖 API Docs: http://localhost:8000/docs")
    print("=" * 60)
    print()
    
    yield  # App runs here
    
    # ========== SHUTDOWN ==========
    print()
    print("🛑 Shutting down...")
    await sensor_manager.shutdown()
    print("✅ Goodbye!")


# =============================================================================
# CREATE THE APP
# =============================================================================

app = FastAPI(
    title="Sensor Data Collector",
    description="""
## What is this?

A backend for collecting data from environmental sensors and uploading to the cloud.

## How it works

1. **Add a sensor** with its IP address and your upload token
2. **Turn it on** to start automatic data collection
3. **Every 60 seconds**, we fetch data, convert to CSV, and upload

## Supported Sensors

| Sensor | Status | What it measures |
|--------|--------|------------------|
| **Purple Air** | ✅ Ready | Air quality (PM2.5, temperature, humidity) |
| **Tempest** | ✅ Ready | Weather (temp, wind, rain, UV, lightning) |
| **Water Quality** | 🚧 Coming | Water sensors |
| **Mayfly** | 🚧 Coming | Data loggers |

## Quick Start

1. Add a sensor: `POST /api/sensors/purple-air`
2. Turn it on: `POST /api/sensors/{id}/turn-on`
3. Data flows automatically!

    """,
    version="1.0.0",
    lifespan=lifespan,
)


# =============================================================================
# CORS (Allow frontend to talk to us)
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

app.include_router(sensors_router)


# =============================================================================
# ROOT ENDPOINTS
# =============================================================================

@app.get("/")
async def root():
    """
    Welcome! Here's what you can do.
    """
    return {
        "message": "Welcome to Sensor Data Collector! 🎉",
        "docs": "Go to /docs to see all the API endpoints",
        "quick_start": {
            "1_add_sensor": "POST /api/sensors/purple-air",
            "2_turn_on": "POST /api/sensors/{id}/turn-on",
            "3_check_status": "GET /api/sensors/{id}/status",
            "4_manual_fetch": "POST /api/sensors/{id}/fetch-now"
        }
    }


@app.get("/health")
async def health():
    """
    Health check - is the server running?
    """
    return {
        "status": "healthy",
        "polling_interval": Config.POLLING_INTERVAL,
        "upload_endpoint": "oberlin.communityhub.cloud"
    }
