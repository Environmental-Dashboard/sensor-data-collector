"""
Sensor Models
=============
Pydantic models for sensor data validation and serialization.

This module defines all data structures used throughout the application:
- Request models: What the frontend sends to the backend
- Response models: What the backend returns to the frontend  
- Internal models: Data structures for sensor readings

SENSOR TYPES SUPPORTED:
1. Purple Air - Air quality sensors (PM2.5, temperature, humidity)
2. Water Quality - Water quality sensors (TBD - placeholder)
3. Mayfly - Mayfly dataloggers (TBD - placeholder)
4. Tempest - WeatherFlow Tempest weather stations

Author: Frank Kusi Appiah
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum


# =============================================================================
# ENUMS
# =============================================================================

class SensorType(str, Enum):
    """
    Types of sensors supported by the system.
    
    Each sensor type has its own:
    - Add request fields (e.g., Purple Air needs IP address)
    - Data parsing logic
    - CSV output format
    """
    PURPLE_AIR = "purple_air"
    WATER_QUALITY = "water_quality"
    MAYFLY = "mayfly"
    TEMPEST = "tempest"


class SensorStatus(str, Enum):
    """
    Current operational status of a sensor.
    
    Status Flow:
    - INACTIVE: Sensor registered but not polling
    - ACTIVE: Sensor is polling and sending data successfully
    - ERROR: Last poll failed (will retry on next interval)
    - OFFLINE: Sensor unreachable for extended period
    """
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    OFFLINE = "offline"


# =============================================================================
# REQUEST MODELS - What frontend sends to backend
# =============================================================================

class AddPurpleAirSensorRequest(BaseModel):
    """
    Request body for adding a new Purple Air sensor.
    
    Purple Air sensors are accessed via their LOCAL IP address on the same
    network. They expose a JSON endpoint at http://<ip>/json
    
    Fields:
        ip_address: Local network IP (e.g., "192.168.1.100")
        name: Human-readable identifier (e.g., "Lab Room Sensor")
        location: Physical location description (e.g., "Science Building Room 201")
    
    Example Request:
        POST /api/sensors/purple-air
        {
            "ip_address": "192.168.1.100",
            "name": "Lab Room Sensor",
            "location": "Science Building Room 201"
        }
    """
    ip_address: str = Field(
        ..., 
        description="Local IP address of the sensor (e.g., 192.168.1.100)",
        examples=["192.168.1.100", "10.0.0.50"]
    )
    name: str = Field(
        ..., 
        description="Human-readable name for the sensor",
        min_length=1,
        max_length=100,
        examples=["Lab Room Sensor", "Outdoor Air Monitor"]
    )
    location: str = Field(
        ..., 
        description="Physical location of the sensor",
        min_length=1,
        max_length=200,
        examples=["Science Building Room 201", "Main Campus Quad"]
    )


class AddTempestSensorRequest(BaseModel):
    """
    Request body for adding a WeatherFlow Tempest weather station.
    
    Tempest sensors can be accessed via:
    1. Local UDP broadcast (port 50222) - no internet required
    2. WeatherFlow REST API - requires API token
    
    For local network access, we use the Hub's IP address.
    
    Fields:
        ip_address: IP of the Tempest Hub on local network
        name: Human-readable identifier
        location: Physical location description
        device_id: Tempest device ID (found in WeatherFlow app)
    
    Example Request:
        POST /api/sensors/tempest
        {
            "ip_address": "192.168.1.150",
            "name": "Campus Weather Station",
            "location": "Rooftop Observatory",
            "device_id": "12345"
        }
    """
    ip_address: str = Field(
        ..., 
        description="IP address of Tempest Hub on local network"
    )
    name: str = Field(
        ..., 
        description="Human-readable name for the sensor",
        min_length=1,
        max_length=100
    )
    location: str = Field(
        ..., 
        description="Physical location of the sensor",
        min_length=1,
        max_length=200
    )
    device_id: str = Field(
        ..., 
        description="Tempest device ID from WeatherFlow app"
    )


class AddWaterQualitySensorRequest(BaseModel):
    """
    Request body for adding a Water Quality sensor.
    
    NOTE: This is a placeholder. Specific fields will be added when
    water quality sensor requirements are defined.
    """
    name: str = Field(..., description="Human-readable name")
    location: str = Field(..., description="Physical location")


class AddMayflySensorRequest(BaseModel):
    """
    Request body for adding a Mayfly datalogger.
    
    NOTE: This is a placeholder. Specific fields will be added when
    Mayfly datalogger requirements are defined.
    """
    name: str = Field(..., description="Human-readable name")
    location: str = Field(..., description="Physical location")


class UpdateSensorRequest(BaseModel):
    """
    Request body for updating sensor properties.
    
    All fields are optional - only provided fields will be updated.
    """
    name: Optional[str] = Field(None, description="New name for the sensor")
    location: Optional[str] = Field(None, description="New location description")


# =============================================================================
# RESPONSE MODELS - What backend returns to frontend
# =============================================================================

class SensorResponse(BaseModel):
    """
    Standard sensor response returned by all API endpoints.
    
    This is the unified response format for all sensor types.
    Frontend uses this to display sensor cards and status.
    
    Fields:
        id: Unique identifier (UUID)
        sensor_type: Type of sensor (purple_air, tempest, etc.)
        name: Human-readable name
        location: Physical location
        ip_address: Network IP (if applicable)
        device_id: Device identifier (for Tempest)
        status: Current status (active, inactive, error, offline)
        is_active: Whether polling is enabled
        last_active: Timestamp of last successful data fetch
        last_error: Error message from last failed fetch
        created_at: When the sensor was registered
    """
    id: str = Field(..., description="Unique identifier (UUID)")
    sensor_type: SensorType = Field(..., description="Type of sensor")
    name: str = Field(..., description="Human-readable name")
    location: str = Field(..., description="Physical location")
    ip_address: Optional[str] = Field(None, description="Network IP address")
    device_id: Optional[str] = Field(None, description="Device ID (for Tempest)")
    status: SensorStatus = Field(default=SensorStatus.INACTIVE)
    is_active: bool = Field(default=False, description="Whether polling is enabled")
    last_active: Optional[datetime] = Field(None, description="Last successful fetch")
    last_error: Optional[str] = Field(None, description="Last error message")
    created_at: datetime = Field(..., description="Registration timestamp")


class SensorListResponse(BaseModel):
    """
    Response containing a list of sensors.
    
    Used by endpoints that return multiple sensors.
    """
    sensors: list[SensorResponse] = Field(..., description="List of sensors")
    total: int = Field(..., description="Total count of sensors")


class FetchResultResponse(BaseModel):
    """
    Response from a manual fetch operation.
    
    Returned when calling POST /api/sensors/{id}/fetch-now
    """
    status: str = Field(..., description="'success' or 'error'")
    sensor_name: str = Field(..., description="Name of the sensor")
    message: Optional[str] = Field(None, description="Status message")
    error_message: Optional[str] = Field(None, description="Error details if failed")
    data: Optional[dict] = Field(None, description="Fetched data (if successful)")
    uploaded_at: Optional[str] = Field(None, description="Upload timestamp")


# =============================================================================
# PURPLE AIR DATA MODELS
# =============================================================================

class PurpleAirReading(BaseModel):
    """
    Data model for a single Purple Air sensor reading.
    
    Purple Air sensors provide air quality data via a local JSON endpoint.
    This model captures the key fields we need for CSV export.
    
    CSV Columns (in order):
        Timestamp, Temperature (°F), Humidity (%), Dewpoint (°F),
        Pressure (hPa), PM1.0 (µg/m³), PM2.5 (µg/m³), PM10.0 (µg/m³), PM2.5 AQI
    
    Data Source:
        HTTP GET http://<sensor_ip>/json
    """
    timestamp: datetime = Field(..., description="Reading timestamp")
    temperature_f: float = Field(..., description="Temperature in Fahrenheit")
    humidity_percent: float = Field(..., description="Relative humidity %")
    dewpoint_f: float = Field(..., description="Dewpoint in Fahrenheit")
    pressure_hpa: float = Field(..., description="Pressure in hectopascals")
    pm1_0_cf1: float = Field(..., description="PM1.0 concentration µg/m³")
    pm2_5_cf1: float = Field(..., description="PM2.5 concentration µg/m³")
    pm10_0_cf1: float = Field(..., description="PM10.0 concentration µg/m³")
    pm2_5_aqi: int = Field(..., description="PM2.5 Air Quality Index")

    def to_csv_row(self) -> str:
        """Convert reading to CSV row string."""
        return (
            f"{self.timestamp.isoformat()},"
            f"{self.temperature_f},"
            f"{self.humidity_percent},"
            f"{self.dewpoint_f},"
            f"{self.pressure_hpa},"
            f"{self.pm1_0_cf1},"
            f"{self.pm2_5_cf1},"
            f"{self.pm10_0_cf1},"
            f"{self.pm2_5_aqi}"
        )

    @staticmethod
    def csv_header() -> str:
        """Return CSV header row."""
        return (
            "Timestamp,Temperature (°F),Humidity (%),"
            "Dewpoint (°F),Pressure (hPa),"
            "PM1.0 :cf_1( µg/m³),PM2.5 :cf_1( µg/m³),"
            "PM10.0 :cf_1( µg/m³),PM2.5 AQI"
        )


# =============================================================================
# TEMPEST WEATHER DATA MODELS
# =============================================================================

class TempestReading(BaseModel):
    """
    Data model for a WeatherFlow Tempest weather station reading.
    
    Tempest provides comprehensive weather data including:
    - Temperature, humidity, pressure
    - Wind speed and direction
    - Rain accumulation
    - UV index and solar radiation
    - Lightning strike data
    
    CSV Columns (in order):
        Timestamp, Temperature (°F), Humidity (%), Pressure (mb),
        Wind Speed (mph), Wind Gust (mph), Wind Direction (°),
        Rain (in), UV Index, Solar Radiation (W/m²), Lightning Count
    
    Data Source:
        UDP broadcast on port 50222 OR
        HTTP GET from Tempest Hub
    """
    timestamp: datetime = Field(..., description="Reading timestamp")
    temperature_f: float = Field(..., description="Temperature in Fahrenheit")
    humidity_percent: float = Field(..., description="Relative humidity %")
    pressure_mb: float = Field(..., description="Pressure in millibars")
    wind_speed_mph: float = Field(..., description="Wind speed in mph")
    wind_gust_mph: float = Field(..., description="Wind gust in mph")
    wind_direction_deg: int = Field(..., description="Wind direction in degrees")
    rain_inches: float = Field(..., description="Rain accumulation in inches")
    uv_index: float = Field(..., description="UV index")
    solar_radiation: float = Field(..., description="Solar radiation W/m²")
    lightning_count: int = Field(..., description="Lightning strikes detected")

    def to_csv_row(self) -> str:
        """Convert reading to CSV row string."""
        return (
            f"{self.timestamp.isoformat()},"
            f"{self.temperature_f},"
            f"{self.humidity_percent},"
            f"{self.pressure_mb},"
            f"{self.wind_speed_mph},"
            f"{self.wind_gust_mph},"
            f"{self.wind_direction_deg},"
            f"{self.rain_inches},"
            f"{self.uv_index},"
            f"{self.solar_radiation},"
            f"{self.lightning_count}"
        )

    @staticmethod
    def csv_header() -> str:
        """Return CSV header row."""
        return (
            "Timestamp,Temperature (°F),Humidity (%),"
            "Pressure (mb),Wind Speed (mph),Wind Gust (mph),"
            "Wind Direction (°),Rain (in),UV Index,"
            "Solar Radiation (W/m²),Lightning Count"
        )
