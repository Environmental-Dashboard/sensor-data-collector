"""
Sensors API Router
==================
REST API endpoints for sensor management.

This module provides the HTTP API for all sensor operations.
All endpoints follow REST conventions and return JSON responses.

ENDPOINTS OVERVIEW:
    GET    /api/sensors                    - List all sensors
    GET    /api/sensors/{id}               - Get single sensor
    DELETE /api/sensors/{id}               - Delete sensor
    GET    /api/sensors/{id}/status        - Get sensor status
    POST   /api/sensors/{id}/turn-on       - Start data collection
    POST   /api/sensors/{id}/turn-off      - Stop data collection
    POST   /api/sensors/{id}/fetch-now     - Manual data fetch
    
    POST   /api/sensors/purple-air         - Add Purple Air sensor
    GET    /api/sensors/purple-air         - List Purple Air sensors
    
    POST   /api/sensors/tempest            - Add Tempest sensor
    GET    /api/sensors/tempest            - List Tempest sensors
    
    POST   /api/sensors/water-quality      - Add Water Quality sensor (TBD)
    GET    /api/sensors/water-quality      - List Water Quality sensors
    
    POST   /api/sensors/mayfly             - Add Mayfly sensor (TBD)
    GET    /api/sensors/mayfly             - List Mayfly sensors

Author: Sensor Data Collector Team
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Optional

from app.models import (
    SensorType,
    AddPurpleAirSensorRequest,
    AddTempestSensorRequest,
    AddWaterQualitySensorRequest,
    AddMayflySensorRequest,
    SensorResponse,
    SensorListResponse,
)


router = APIRouter(prefix="/api/sensors", tags=["sensors"])


# =============================================================================
# DEPENDENCY INJECTION
# =============================================================================

# Global reference to sensor manager (set by main.py)
_sensor_manager = None


def set_sensor_manager(manager):
    """
    Set the global sensor manager instance.
    
    Called from main.py during application startup to inject
    the sensor manager into the router.
    
    Args:
        manager: Initialized SensorManager instance
    """
    global _sensor_manager
    _sensor_manager = manager


def get_sensor_manager():
    """
    Dependency to get the sensor manager.
    
    Used in route handlers to access the sensor manager.
    
    Returns:
        SensorManager instance
        
    Raises:
        HTTPException: If manager not initialized
    """
    if _sensor_manager is None:
        raise HTTPException(
            status_code=500, 
            detail="Sensor manager not initialized"
        )
    return _sensor_manager


# =============================================================================
# PURPLE AIR SENSOR ENDPOINTS
# =============================================================================

@router.post(
    "/purple-air", 
    response_model=SensorResponse,
    summary="Add Purple Air Sensor",
    description="""
    Register a new Purple Air sensor for data collection.
    
    Purple Air sensors are accessed via their local IP address on the same
    network as this backend server. They expose a JSON endpoint at http://<ip>/json
    
    **Required Fields:**
    - `ip_address`: Local network IP (e.g., "192.168.1.100")
    - `name`: Human-readable name (e.g., "Lab Room Sensor")
    - `location`: Physical location (e.g., "Science Building Room 201")
    
    **After Adding:**
    - Sensor starts in INACTIVE state
    - Call `/api/sensors/{id}/turn-on` to start data collection
    - Data will be fetched every 60 seconds and pushed to the external endpoint
    """
)
async def add_purple_air_sensor(
    request: AddPurpleAirSensorRequest,
    manager = Depends(get_sensor_manager)
):
    """Add a new Purple Air sensor."""
    # Validate IP format
    parts = request.ip_address.split(".")
    if len(parts) != 4:
        raise HTTPException(
            status_code=400, 
            detail="Invalid IP address format. Expected: xxx.xxx.xxx.xxx"
        )
    
    for part in parts:
        try:
            num = int(part)
            if num < 0 or num > 255:
                raise ValueError()
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid IP address. Each octet must be 0-255"
            )
    
    # Check for duplicate IP
    existing_sensors = manager.get_all_sensors(SensorType.PURPLE_AIR)
    for sensor in existing_sensors:
        if sensor.ip_address == request.ip_address:
            raise HTTPException(
                status_code=400,
                detail=f"Sensor with IP {request.ip_address} already exists"
            )
    
    return manager.add_purple_air_sensor(request)


@router.get(
    "/purple-air", 
    response_model=SensorListResponse,
    summary="List Purple Air Sensors",
    description="Get all registered Purple Air sensors with their current status."
)
async def get_all_purple_air_sensors(manager = Depends(get_sensor_manager)):
    """Get all Purple Air sensors."""
    sensors = manager.get_all_sensors(SensorType.PURPLE_AIR)
    return SensorListResponse(sensors=sensors, total=len(sensors))


# =============================================================================
# TEMPEST WEATHER SENSOR ENDPOINTS
# =============================================================================

@router.post(
    "/tempest", 
    response_model=SensorResponse,
    summary="Add Tempest Weather Station",
    description="""
    Register a new WeatherFlow Tempest weather station.
    
    Tempest sensors are accessed via the Tempest Hub on the local network.
    They provide comprehensive weather data including temperature, humidity,
    wind, rain, UV, solar radiation, and lightning detection.
    
    **Required Fields:**
    - `ip_address`: IP of the Tempest Hub on local network
    - `name`: Human-readable name
    - `location`: Physical location
    - `device_id`: Tempest device ID (from WeatherFlow app)
    """
)
async def add_tempest_sensor(
    request: AddTempestSensorRequest,
    manager = Depends(get_sensor_manager)
):
    """Add a new Tempest weather station."""
    # Validate IP format
    parts = request.ip_address.split(".")
    if len(parts) != 4:
        raise HTTPException(
            status_code=400, 
            detail="Invalid IP address format"
        )
    
    return manager.add_tempest_sensor(request)


@router.get(
    "/tempest", 
    response_model=SensorListResponse,
    summary="List Tempest Sensors",
    description="Get all registered Tempest weather stations."
)
async def get_all_tempest_sensors(manager = Depends(get_sensor_manager)):
    """Get all Tempest sensors."""
    sensors = manager.get_all_sensors(SensorType.TEMPEST)
    return SensorListResponse(sensors=sensors, total=len(sensors))


# =============================================================================
# WATER QUALITY SENSOR ENDPOINTS (Placeholder)
# =============================================================================

@router.post(
    "/water-quality", 
    response_model=SensorResponse,
    summary="Add Water Quality Sensor",
    description="**NOT YET IMPLEMENTED** - Placeholder for Water Quality sensors."
)
async def add_water_quality_sensor(
    request: AddWaterQualitySensorRequest,
    manager = Depends(get_sensor_manager)
):
    """Add a new Water Quality sensor."""
    raise HTTPException(
        status_code=501, 
        detail="Water Quality sensors not yet implemented"
    )


@router.get(
    "/water-quality", 
    response_model=SensorListResponse,
    summary="List Water Quality Sensors"
)
async def get_all_water_quality_sensors(manager = Depends(get_sensor_manager)):
    """Get all Water Quality sensors."""
    sensors = manager.get_all_sensors(SensorType.WATER_QUALITY)
    return SensorListResponse(sensors=sensors, total=len(sensors))


# =============================================================================
# MAYFLY DATALOGGER ENDPOINTS (Placeholder)
# =============================================================================

@router.post(
    "/mayfly", 
    response_model=SensorResponse,
    summary="Add Mayfly Datalogger",
    description="**NOT YET IMPLEMENTED** - Placeholder for Mayfly dataloggers."
)
async def add_mayfly_sensor(
    request: AddMayflySensorRequest,
    manager = Depends(get_sensor_manager)
):
    """Add a new Mayfly datalogger."""
    raise HTTPException(
        status_code=501, 
        detail="Mayfly dataloggers not yet implemented"
    )


@router.get(
    "/mayfly", 
    response_model=SensorListResponse,
    summary="List Mayfly Dataloggers"
)
async def get_all_mayfly_sensors(manager = Depends(get_sensor_manager)):
    """Get all Mayfly dataloggers."""
    sensors = manager.get_all_sensors(SensorType.MAYFLY)
    return SensorListResponse(sensors=sensors, total=len(sensors))


# =============================================================================
# GENERIC SENSOR ENDPOINTS
# =============================================================================

@router.get(
    "/", 
    response_model=SensorListResponse,
    summary="List All Sensors",
    description="""
    Get all sensors, optionally filtered by type.
    
    **Query Parameters:**
    - `sensor_type`: Filter by type (purple_air, tempest, water_quality, mayfly)
    """
)
async def get_all_sensors(
    sensor_type: Optional[SensorType] = None,
    manager = Depends(get_sensor_manager)
):
    """Get all sensors with optional type filter."""
    sensors = manager.get_all_sensors(sensor_type)
    return SensorListResponse(sensors=sensors, total=len(sensors))


@router.get(
    "/{sensor_id}", 
    response_model=SensorResponse,
    summary="Get Sensor",
    description="Get a specific sensor by its ID."
)
async def get_sensor(sensor_id: str, manager = Depends(get_sensor_manager)):
    """Get a single sensor by ID."""
    sensor = manager.get_sensor(sensor_id)
    if not sensor:
        raise HTTPException(status_code=404, detail="Sensor not found")
    return sensor


@router.delete(
    "/{sensor_id}",
    summary="Delete Sensor",
    description="""
    Delete a sensor.
    
    This will:
    - Stop any active data collection for this sensor
    - Remove the sensor from the registry
    - The sensor cannot be recovered after deletion
    """
)
async def delete_sensor(sensor_id: str, manager = Depends(get_sensor_manager)):
    """Delete a sensor."""
    success = manager.delete_sensor(sensor_id)
    if not success:
        raise HTTPException(status_code=404, detail="Sensor not found")
    return {"status": "deleted", "sensor_id": sensor_id}


@router.get(
    "/{sensor_id}/status",
    summary="Get Sensor Status",
    description="""
    Get detailed status information for a sensor.
    
    Returns:
    - `status`: Current status (active, inactive, error, offline)
    - `is_active`: Whether data collection is enabled
    - `last_active`: Timestamp of last successful data fetch
    - `last_error`: Error message from last failed fetch (if any)
    """
)
async def get_sensor_status(sensor_id: str, manager = Depends(get_sensor_manager)):
    """Get sensor status details."""
    status = manager.get_sensor_status(sensor_id)
    if not status:
        raise HTTPException(status_code=404, detail="Sensor not found")
    return status


@router.post(
    "/{sensor_id}/turn-on", 
    response_model=SensorResponse,
    summary="Turn On Sensor",
    description="""
    Start data collection for a sensor.
    
    This creates a scheduled job that:
    - Runs every 60 seconds (configurable)
    - Fetches data from the sensor via its local IP
    - Converts the data to CSV format
    - Pushes the CSV to the external endpoint
    
    The sensor status will be updated to ACTIVE.
    """
)
async def turn_on_sensor(sensor_id: str, manager = Depends(get_sensor_manager)):
    """Turn on data collection."""
    sensor = await manager.turn_on_sensor(sensor_id)
    if not sensor:
        raise HTTPException(status_code=404, detail="Sensor not found")
    return sensor


@router.post(
    "/{sensor_id}/turn-off", 
    response_model=SensorResponse,
    summary="Turn Off Sensor",
    description="""
    Stop data collection for a sensor.
    
    This stops the scheduled polling job. The sensor remains registered
    and can be turned on again later.
    
    The sensor status will be updated to INACTIVE.
    """
)
async def turn_off_sensor(sensor_id: str, manager = Depends(get_sensor_manager)):
    """Turn off data collection."""
    sensor = manager.turn_off_sensor(sensor_id)
    if not sensor:
        raise HTTPException(status_code=404, detail="Sensor not found")
    return sensor


@router.post(
    "/{sensor_id}/fetch-now",
    summary="Fetch Data Now",
    description="""
    Manually trigger a data fetch for a sensor.
    
    Useful for testing without waiting for the scheduled interval.
    
    Returns:
    - `status`: "success" or "error"
    - `reading`: The fetched data (if successful)
    - `upload_result`: Upload confirmation (if successful)
    - `error_message`: Error details (if failed)
    
    **Note:** The sensor does not need to be "on" to use this endpoint.
    """
)
async def trigger_fetch_now(sensor_id: str, manager = Depends(get_sensor_manager)):
    """Manually trigger data fetch."""
    result = await manager.trigger_fetch_now(sensor_id)
    
    if result.get("status") == "error" and "not found" in result.get("error_message", "").lower():
        raise HTTPException(status_code=404, detail="Sensor not found")
    
    return result
