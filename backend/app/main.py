"""
Sensor Data Collector - Backend
================================

This is the backend API that runs on your LOCAL computer.
It connects to sensors on your network and uploads data to the cloud.

Author: Frank Kusi Appiah
"""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import Response
from dotenv import load_dotenv

from app.routers import sensors_router, esp32_router, set_sensor_manager
from app.services import PurpleAirService, TempestService, VoltageMeterService, SensorManager


load_dotenv()


class Config:
    POLLING_INTERVAL = int(os.getenv("POLLING_INTERVAL", "60"))
    
    # WeatherFlow Tempest API Token
    # Get from https://tempestwx.com/settings/tokens
    # One token works for ALL Tempest devices
    # Token is passed as query parameter: ?token=...
    # Set TEMPEST_API_TOKEN in backend/.env (never hardcode tokens in source)
    TEMPEST_API_TOKEN = os.getenv("TEMPEST_API_TOKEN", "")
    
    # CORS - Allow the frontend to connect
    # Add all known Vercel deployment URLs here
    CORS_ORIGINS = [
        "https://frontend-nu-nine-45.vercel.app",
        "https://frontend-oo5y8j4zu-environment-dashboards-projects.vercel.app",
        "https://frontend-2o2a130mj-environment-dashboards-projects.vercel.app",
        "https://frontend-moh64c7s7-environment-dashboards-projects.vercel.app",
        "https://ed-sensor-dashboard.vercel.app",
        "https://ed-sensors-dashboard.vercel.app",
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown."""
    print()
    print("=" * 60)
    print("SENSOR DATA COLLECTOR - Backend")
    print("=" * 60)
    
    purple_air_service = PurpleAirService()
    tempest_service = TempestService(api_token=Config.TEMPEST_API_TOKEN)
    voltage_meter_service = VoltageMeterService()

    if Config.TEMPEST_API_TOKEN:
        print(f"Tempest API Token: {Config.TEMPEST_API_TOKEN[:8]}...{Config.TEMPEST_API_TOKEN[-4:]}")
    else:
        print("WARNING: TEMPEST_API_TOKEN is not set - Tempest sensors will not work.")
        print("         Add it to backend/.env (see env.example.txt)")
    
    sensor_manager = SensorManager(
        purple_air_service=purple_air_service,
        tempest_service=tempest_service,
        voltage_meter_service=voltage_meter_service,
        polling_interval=Config.POLLING_INTERVAL,
    )
    
    set_sensor_manager(sensor_manager)
    
    print(f"Polling every {Config.POLLING_INTERVAL} seconds")
    print(f"Uploads to: oberlin.communityhub.cloud")
    print()
    print("Sensors: Purple Air, Tempest, Voltage Meter")
    print("API Docs: http://localhost:8000/docs")
    print("=" * 60)
    print()
    
    yield
    
    print("Shutting down...")
    await sensor_manager.shutdown()


app = FastAPI(
    title="Sensor Data Collector",
    description="Backend API for collecting sensor data and uploading to the cloud.",
    version="1.0.0",
    lifespan=lifespan,
)


def _is_allowed_origin(origin: str) -> bool:
    """Allow explicit origins plus this team's Vercel preview deployments.

    Note: deliberately NOT a blanket *.vercel.app match - anyone can deploy
    to vercel.app, so that would let arbitrary sites call this API from a browser.
    """
    if origin in Config.CORS_ORIGINS:
        return True
    # Vercel preview deploys for this team, e.g.
    # https://frontend-xxxx-environment-dashboards-projects.vercel.app
    return origin.startswith("https://") and origin.endswith("-environment-dashboards-projects.vercel.app")


# Custom CORS middleware to handle Vercel preview deployment origins
@app.middleware("http")
async def cors_middleware(request: Request, call_next):
    """Handle CORS for known frontend origins and localhost."""
    origin = request.headers.get("origin")
    allowed = origin is not None and _is_allowed_origin(origin)

    # Handle preflight OPTIONS request
    if request.method == "OPTIONS":
        response = Response(status_code=200)
        if allowed:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "*"
            response.headers["Access-Control-Max-Age"] = "3600"
        return response

    # Handle actual request
    response = await call_next(request)
    if allowed:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "*"
    return response


app.include_router(sensors_router)
app.include_router(esp32_router)


@app.get("/")
async def root():
    return {
        "message": "Sensor Data Collector Backend",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "polling_interval": Config.POLLING_INTERVAL
    }
