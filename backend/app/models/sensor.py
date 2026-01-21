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
from datetime import datetime, timezone
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
    
    API Documentation: https://weatherflow.github.io/Tempest/api/
    
    Note: The WeatherFlow API token is configured in the backend.
    One token works for ALL Tempest devices.
    
    Fields:
        device_id: The Tempest device ID (e.g., "205498")
                   Find this in the WeatherFlow Tempest app under station settings.
        
        location: Where is it physically located?
        
        upload_token: Your upload token for oberlin.communityhub.cloud
    """
    device_id: str = Field(
        ..., 
        description="Device ID from WeatherFlow app (e.g., 205498)",
        examples=["205498", "123456"]
    )
    location: str = Field(
        ..., 
        description="Physical location", 
        min_length=1, 
        max_length=200,
        examples=["Science Building Roof", "Main Quad"]
    )
    upload_token: str = Field(
        ..., 
        description="Your upload token for oberlin.communityhub.cloud"
    )


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
    battery_volts: Optional[float] = Field(None, description="Battery voltage (Tempest only)")


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
        # Format timestamp as ISO 8601 with local timezone offset (like -04:00)
        # This matches the successful upload format: 2026-01-06T01:54:20-04:00
        from datetime import datetime as dt
        
        # Get local timezone
        if self.timestamp.tzinfo is None:
            # If no timezone, assume UTC and convert to local
            utc_time = self.timestamp.replace(tzinfo=timezone.utc)
        else:
            utc_time = self.timestamp
        
        # Convert to local timezone
        local_time = utc_time.astimezone()
        offset = local_time.utcoffset()
        
        if offset:
            total_seconds = int(offset.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            sign = '-' if hours < 0 else '+'
            timestamp_str = local_time.strftime(f"%Y-%m-%dT%H:%M:%S{sign}{abs(hours):02d}:{abs(minutes):02d}")
        else:
            timestamp_str = local_time.strftime("%Y-%m-%dT%H:%M:%S+00:00")
        
        return (
            f"{timestamp_str},"
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
        # Exact format expected by Community Hub - single line, no extra spaces
        return "Timestamp,Temperature (°F),Humidity (%),Dewpoint (°F),Pressure (hPa),PM1.0 :cf_1( µg/m³),PM2.5 :cf_1( µg/m³),PM10.0 :cf_1( µg/m³),PM2.5 AQI"


# =============================================================================
# TEMPEST WEATHER DATA
# =============================================================================
# Weather data from a Tempest weather station.
# API Reference: https://weatherflow.github.io/Tempest/api/

class TempestReading(BaseModel):
    """
    One reading from a Tempest weather station.
    
    ALL available data from Tempest via WebSocket:
    
    TEMPERATURE & HUMIDITY:
        timestamp: When this reading was taken (UTC)
        temperature_c: Temperature in Celsius
        temperature_f: Temperature in Fahrenheit
        humidity_percent: Relative humidity (0-100%)
    
    WIND:
        wind_avg_ms: Average wind speed (m/s)
        wind_avg_mph: Average wind speed (mph)
        wind_gust_ms: Wind gust speed (m/s)
        wind_gust_mph: Wind gust speed (mph)
        wind_lull_ms: Wind lull/minimum (m/s)
        wind_lull_mph: Wind lull/minimum (mph)
        wind_direction_deg: Wind direction (0°=N, 90°=E, 180°=S, 270°=W)
    
    PRESSURE:
        pressure_mb: Station pressure (millibars)
        pressure_inhg: Station pressure (inches of mercury)
    
    SOLAR & UV:
        uv_index: UV radiation level (0-11+)
        solar_radiation_wm2: Solar radiation (W/m²)
        illuminance_lux: Light level (lux)
    
    PRECIPITATION:
        rain_mm: Rain accumulated since last report (mm)
        rain_inches: Rain accumulated since last report (inches)
        precip_type: 0=None, 1=Rain, 2=Hail, 3=Rain+Hail
    
    LIGHTNING:
        lightning_count: Number of strikes detected
        lightning_avg_distance_km: Average distance to strikes (km)
        lightning_avg_distance_mi: Average distance to strikes (miles)
    
    DEVICE:
        battery_volts: Battery voltage (2.4V=low, 2.7V=full)
        report_interval_min: How often device reports (minutes)
    """
    # Timestamp (UTC)
    timestamp: datetime
    
    # Temperature & Humidity
    temperature_c: float = Field(default=0.0, description="Temperature (°C)")
    temperature_f: float = Field(default=0.0, description="Temperature (°F)")
    humidity_percent: float = Field(default=0.0, description="Relative humidity (%)")
    
    # Wind
    wind_avg_ms: float = Field(default=0.0, description="Average wind speed (m/s)")
    wind_avg_mph: float = Field(default=0.0, description="Average wind speed (mph)")
    wind_gust_ms: float = Field(default=0.0, description="Wind gust (m/s)")
    wind_gust_mph: float = Field(default=0.0, description="Wind gust (mph)")
    wind_lull_ms: float = Field(default=0.0, description="Wind lull (m/s)")
    wind_lull_mph: float = Field(default=0.0, description="Wind lull (mph)")
    wind_direction_deg: int = Field(default=0, description="Wind direction (degrees)")
    
    # Pressure
    pressure_mb: float = Field(default=0.0, description="Pressure (millibars)")
    pressure_inhg: float = Field(default=0.0, description="Pressure (inHg)")
    
    # Solar & UV
    uv_index: float = Field(default=0.0, description="UV index")
    solar_radiation_wm2: float = Field(default=0.0, description="Solar radiation (W/m²)")
    illuminance_lux: float = Field(default=0.0, description="Illuminance (lux)")
    
    # Precipitation
    rain_mm: float = Field(default=0.0, description="Rain since last report (mm)")
    rain_inches: float = Field(default=0.0, description="Rain since last report (inches)")
    precip_type: int = Field(default=0, description="0=None, 1=Rain, 2=Hail, 3=Mix")
    
    # Lightning
    lightning_count: int = Field(default=0, description="Lightning strike count")
    lightning_avg_distance_km: float = Field(default=0.0, description="Avg lightning distance (km)")
    lightning_avg_distance_mi: float = Field(default=0.0, description="Avg lightning distance (mi)")
    
    # Device
    battery_volts: float = Field(default=0.0, description="Battery voltage (V)")
    report_interval_min: int = Field(default=1, description="Report interval (minutes)")

    def to_csv_row(self) -> str:
        """Turn this reading into a CSV row."""
        return (
            f"{self.timestamp.strftime('%Y-%m-%dT%H:%M:%SZ')},"  # UTC ISO format
            f"{self.temperature_c:.2f},"
            f"{self.temperature_f:.2f},"
            f"{self.humidity_percent:.1f},"
            f"{self.wind_avg_ms:.2f},"
            f"{self.wind_avg_mph:.2f},"
            f"{self.wind_gust_ms:.2f},"
            f"{self.wind_gust_mph:.2f},"
            f"{self.wind_lull_ms:.2f},"
            f"{self.wind_lull_mph:.2f},"
            f"{self.wind_direction_deg},"
            f"{self.pressure_mb:.2f},"
            f"{self.pressure_inhg:.3f},"
            f"{self.uv_index:.2f},"
            f"{self.solar_radiation_wm2:.1f},"
            f"{self.illuminance_lux:.0f},"
            f"{self.rain_mm:.2f},"
            f"{self.rain_inches:.4f},"
            f"{self.precip_type},"
            f"{self.lightning_count},"
            f"{self.lightning_avg_distance_km:.1f},"
            f"{self.lightning_avg_distance_mi:.1f},"
            f"{self.battery_volts:.2f},"
            f"{self.report_interval_min}"
        )

    @staticmethod
    def csv_header() -> str:
        """The header row for CSV files."""
        return (
            "Timestamp (UTC),"
            "Temperature (°C),Temperature (°F),Humidity (%),"
            "Wind Avg (m/s),Wind Avg (mph),Wind Gust (m/s),Wind Gust (mph),"
            "Wind Lull (m/s),Wind Lull (mph),Wind Direction (°),"
            "Pressure (mb),Pressure (inHg),"
            "UV Index,Solar Radiation (W/m²),Illuminance (lux),"
            "Rain (mm),Rain (in),Precip Type,"
            "Lightning Count,Lightning Distance (km),Lightning Distance (mi),"
            "Battery (V),Report Interval (min)"
        )
