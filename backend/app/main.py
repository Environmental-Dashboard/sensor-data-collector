"""
Sensor Data Collector - Backend
================================

This is the backend API that runs on your LOCAL computer.
It connects to sensors on your network and uploads data to the cloud.

Author: Frank Kusi Appiah
"""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from app.routers import sensors_router, set_sensor_manager
from app.services import PurpleAirService, TempestService, VoltageMeterService, SensorManager


load_dotenv()


class Config:
    POLLING_INTERVAL = int(os.getenv("POLLING_INTERVAL", "60"))
    
    # WeatherFlow Tempest API Token
    # Get from https://tempestwx.com/settings/tokens
    # One token works for ALL Tempest devices
    # Token is passed as query parameter: ?token=...
    TEMPEST_API_TOKEN = os.getenv("TEMPEST_API_TOKEN", "61a83ac0-678f-4284-b9aa-e962cf6a7ede")
    
    # CORS - Allow the frontend to connect
    CORS_ORIGINS = [
        "https://ed-sensor-dashboard.vercel.app",   # Production frontend
        "https://ed-sensors-dashboard.vercel.app",  # Alternate
        "http://localhost:5173",                     # Local dev
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
    
    print(f"Tempest API Token: {Config.TEMPEST_API_TOKEN[:8]}...{Config.TEMPEST_API_TOKEN[-4:]}")
    
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


app.add_middleware(
    CORSMiddleware,
    allow_origins=Config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(sensors_router)


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
