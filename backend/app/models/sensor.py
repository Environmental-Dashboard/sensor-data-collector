"""
Sensor Models
=============

Hey! This file defines all the data structures (models) used in our app.
Think of models like templates or blueprints for data.

For example, when someone adds a Purple Air sensor, they need to provide:
- IP address (where the sensor lives on the network)
- Name (what we call it)
- Location (where it physically is)
- Token (password to upload data to the cloud)

This file makes sure all that data is valid before we use it.

WHAT'S IN HERE:
---------------
1. SensorType - The types of sensors we support (purple_air, tempest, etc.)
2. SensorStatus - Is the sensor working? (active, inactive, error, offline)
3. Request Models - Data the frontend sends TO us
4. Response Models - Data we send BACK to the frontend
5. Reading Models - The actual sensor data (temperature, humidity, etc.)

Author: Frank Kusi Appiah
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum


# =============================================================================
# SENSOR TYPES
# =============================================================================
# These are the different kinds of sensors we can work with.
# Each one collects different data and connects differently.

class SensorType(str, Enum):
    """
    What kind of sensor is this?
    
    PURPLE_AIR = Air quality sensor (measures PM2.5, dust, etc.)
    TEMPEST = Weather station (temp, wind, rain, lightning)
    WATER_QUALITY = Water sensor (coming soon)
    DO_SENSOR = Dissolved Oxygen sensor (coming soon)
    """
    PURPLE_AIR = "purple_air"
    WATER_QUALITY = "water_quality"
    DO_SENSOR = "do_sensor"
    TEMPEST = "tempest"


# =============================================================================
# SENSOR STATUS
# =============================================================================
# This tells us if the sensor is working or not.

class SensorStatus(str, Enum):
    """
    How's the sensor doing right now?
    
    ACTIVE = Everything's good! Sensor is sending data.
    INACTIVE = Sensor is registered but we're not collecting data (turned off).
    ERROR = Something went wrong on the last attempt.
    OFFLINE = Can't reach the sensor at all.
    """
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    OFFLINE = "offline"


# =============================================================================
# REQUEST MODELS - What the frontend sends to us
# =============================================================================
# When someone clicks "Add Sensor" on the website, this is what we receive.

class AddPurpleAirSensorRequest(BaseModel):
    """
    Adding a Purple Air sensor? Send us this info!
    
    Example - what the frontend sends:
    {
        "ip_address": "192.168.1.100",
        "name": "Lab Room Sensor",
        "location": "Science Building Room 201",
        "upload_token": "abc123xyz..."
    }
    
    Fields:
        ip_address: The sensor's IP on your local network (like 192.168.1.100)
                   You can find this in your router or the PurpleAir app.
        
        name: Give it a friendly name so you know which one it is.
        
        location: Where is it physically? Helps you remember later.
        
        upload_token: The password/token for uploading to the cloud endpoint.
                     Get this from oberlin.communityhub.cloud
    """
    ip_address: str = Field(
        ..., 
        description="Local IP address of the sensor (e.g., 192.168.1.100)",
        examples=["192.168.1.100", "10.17.192.162"]
    )
    name: str = Field(
        ..., 
        description="Give it a name you'll remember",
        min_length=1,
        max_length=100,
        examples=["Lab Room Sensor", "Outdoor Air Monitor"]
    )
    location: str = Field(
        ..., 
        description="Where is this sensor located?",
        min_length=1,
        max_length=200,
        examples=["Science Building Room 201", "Main Campus Quad"]
    )
    upload_token: str = Field(
        ...,
        description="Your upload token from oberlin.communityhub.cloud",
        min_length=1
    )


class AddTempestSensorRequest(BaseModel):
    """
    Adding a Tempest weather station? Here's what we need.
    
    Tempest is a WeatherFlow device that measures weather stuff:
    temperature, wind, rain, UV, even lightning!
    
    Fields:
        ip_address: IP of the Tempest Hub (the base station)
        name: What do you want to call it?
        location: Where is it?
        device_id: The Tempest device ID (find this in the WeatherFlow app)
        upload_token: Your cloud upload token
    """
    ip_address: str = Field(..., description="IP of the Tempest Hub")
    name: str = Field(..., description="Friendly name", min_length=1, max_length=100)
    location: str = Field(..., description="Physical location", min_length=1, max_length=200)
    device_id: str = Field(..., description="Device ID from WeatherFlow app")
    upload_token: str = Field(..., description="Your upload token")


class AddWaterQualitySensorRequest(BaseModel):
    """
    Water Quality sensor - Coming soon!
    
    We haven't built this yet, but when we do, you'll add water sensors here.
    """
    name: str = Field(..., description="Sensor name")
    location: str = Field(..., description="Where is it?")
    upload_token: str = Field(..., description="Your upload token")


class AddDOSensorRequest(BaseModel):
    """
    Dissolved Oxygen Sensor - Coming soon!
    
    DO sensors measure dissolved oxygen levels in water.
    We'll add support for this later.
    """
    name: str = Field(..., description="Sensor name")
    location: str = Field(..., description="Where is it?")
    upload_token: str = Field(..., description="Your upload token")


class UpdateSensorRequest(BaseModel):
    """
    Want to update a sensor's info? Send what you want to change.
    
    You don't have to send everything - just what you want to update.
    """
    name: Optional[str] = Field(None, description="New name")
    location: Optional[str] = Field(None, description="New location")


# =============================================================================
# RESPONSE MODELS - What we send back to the frontend
# =============================================================================
# After adding a sensor or asking for info, this is what you get back.

class SensorResponse(BaseModel):
    """
    This is what a sensor looks like when we send it to you.
    
    Every sensor you add gets all these fields:
    
        id: A unique ID we generate (like "550e8400-e29b-41d4-a716-446655440000")
            You'll use this ID to turn on/off, delete, etc.
        
        sensor_type: What kind of sensor (purple_air, tempest, etc.)
        
        name: The name you gave it
        
        location: Where it is
        
        ip_address: Its network address
        
        device_id: For Tempest sensors, the device ID
        
        status: Is it working? (active, inactive, error, offline)
        
        is_active: true = we're collecting data, false = turned off
        
        last_active: When did we last successfully get data?
        
        last_error: If something went wrong, what was the error?
        
        created_at: When was this sensor added?
    """
    id: str = Field(..., description="Unique sensor ID (UUID)")
    sensor_type: SensorType = Field(..., description="Type of sensor")
    name: str = Field(..., description="Sensor name")
    location: str = Field(..., description="Physical location")
    ip_address: Optional[str] = Field(None, description="Network IP")
    device_id: Optional[str] = Field(None, description="Device ID (Tempest)")
    status: SensorStatus = Field(default=SensorStatus.INACTIVE)
    is_active: bool = Field(default=False, description="Is polling enabled?")
    last_active: Optional[datetime] = Field(None, description="Last successful data fetch")
    last_error: Optional[str] = Field(None, description="Last error message")
    created_at: datetime = Field(..., description="When sensor was added")


class SensorListResponse(BaseModel):
    """
    When you ask for a list of sensors, you get this.
    
    Example:
    {
        "sensors": [...list of sensors...],
        "total": 5
    }
    """
    sensors: list[SensorResponse] = Field(..., description="List of sensors")
    total: int = Field(..., description="How many sensors total")


class FetchResultResponse(BaseModel):
    """
    After we fetch data from a sensor, here's what happened.
    
    If it worked:
        status = "success"
        reading = {temperature: 72, humidity: 45, ...}
        uploaded_at = when we sent it to the cloud
        
    If it failed:
        status = "error"
        error_message = what went wrong
    """
    status: str = Field(..., description="'success' or 'error'")
    sensor_name: str = Field(..., description="Which sensor")
    message: Optional[str] = Field(None, description="Status message")
    error_message: Optional[str] = Field(None, description="What went wrong")
    data: Optional[dict] = Field(None, description="The data we got")
    uploaded_at: Optional[str] = Field(None, description="When we uploaded it")


# =============================================================================
# PURPLE AIR DATA - What we get from the sensor
# =============================================================================
# This is the actual air quality data from a Purple Air sensor.

class PurpleAirReading(BaseModel):
    """
    One reading from a Purple Air sensor.
    
    This is the air quality data we collect every 60 seconds:
    
        timestamp: When we took this reading
        
        temperature_f: Temperature in Fahrenheit
        
        humidity_percent: How humid is it? (0-100%)
        
        dewpoint_f: Dewpoint temperature in Fahrenheit
        
        pressure_hpa: Air pressure in hectopascals
        
        pm1_0_cf1: Really tiny particles (PM1.0) in micrograms per cubic meter
        
        pm2_5_cf1: Small particles (PM2.5) - this is the main one people care about!
                   Higher = worse air quality
        
        pm10_0_cf1: Bigger particles (PM10)
        
        pm2_5_aqi: Air Quality Index (0-500)
                   0-50 = Good (green)
                   51-100 = Moderate (yellow)
                   101-150 = Unhealthy for sensitive groups (orange)
                   151-200 = Unhealthy (red)
                   201-300 = Very Unhealthy (purple)
                   301+ = Hazardous (maroon)
    """
    timestamp: datetime
    temperature_f: float = Field(..., description="Temperature (Fahrenheit)")
    humidity_percent: float = Field(..., description="Humidity (0-100%)")
    dewpoint_f: float = Field(..., description="Dewpoint (Fahrenheit)")
    pressure_hpa: float = Field(..., description="Pressure (hPa)")
    pm1_0_cf1: float = Field(..., description="PM1.0 (µg/m³)")
    pm2_5_cf1: float = Field(..., description="PM2.5 (µg/m³) - the important one!")
    pm10_0_cf1: float = Field(..., description="PM10 (µg/m³)")
    pm2_5_aqi: int = Field(..., description="Air Quality Index (0-500)")

    def to_csv_row(self) -> str:
        """Turn this reading into a CSV row (comma-separated values)."""
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
        """The header row for CSV files."""
        return (
            "Timestamp,Temperature (°F),Humidity (%),"
            "Dewpoint (°F),Pressure (hPa),"
            "PM1.0 :cf_1( µg/m³),PM2.5 :cf_1( µg/m³),"
            "PM10.0 :cf_1( µg/m³),PM2.5 AQI"
        )


# =============================================================================
# TEMPEST WEATHER DATA
# =============================================================================
# Weather data from a Tempest weather station.

class TempestReading(BaseModel):
    """
    One reading from a Tempest weather station.
    
    Tempest gives us tons of weather data:
    
        timestamp: When we took this reading
        
        temperature_f: How hot/cold (Fahrenheit)
        
        humidity_percent: Humidity (0-100%)
        
        pressure_mb: Air pressure in millibars
        
        wind_speed_mph: Current wind speed (miles per hour)
        
        wind_gust_mph: Strongest gust recently
        
        wind_direction_deg: Which way is the wind coming from?
                           0° = North, 90° = East, 180° = South, 270° = West
        
        rain_inches: How much rain has fallen
        
        uv_index: UV radiation level (higher = more sunburn risk)
                  0-2 = Low, 3-5 = Moderate, 6-7 = High, 8-10 = Very High, 11+ = Extreme
        
        solar_radiation: Sunlight power in Watts per square meter
        
        lightning_count: Number of lightning strikes detected
    """
    timestamp: datetime
    temperature_f: float
    humidity_percent: float
    pressure_mb: float
    wind_speed_mph: float
    wind_gust_mph: float
    wind_direction_deg: int
    rain_inches: float
    uv_index: float
    solar_radiation: float
    lightning_count: int

    def to_csv_row(self) -> str:
        """Turn this reading into a CSV row."""
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
        """The header row for CSV files."""
        return (
            "Timestamp,Temperature (°F),Humidity (%),"
            "Pressure (mb),Wind Speed (mph),Wind Gust (mph),"
            "Wind Direction (°),Rain (in),UV Index,"
            "Solar Radiation (W/m²),Lightning Count"
        )
