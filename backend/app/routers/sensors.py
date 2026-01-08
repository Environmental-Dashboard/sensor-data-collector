"""
Sensors API Router
==================

Yo! This is where all the API endpoints live.

WHAT'S AN ENDPOINT?
------------------
An endpoint is like a door into our app. When the frontend wants to do something
(like add a sensor), it knocks on a specific door (endpoint).

For example:
- POST /api/sensors/purple-air = "I want to add a Purple Air sensor"
- GET /api/sensors = "Show me all sensors"
- POST /api/sensors/{id}/turn-on = "Start collecting data from this sensor"

HOW IT WORKS:
------------
1. Frontend sends an HTTP request (GET, POST, DELETE)
2. FastAPI routes it to the right function here
3. We call the SensorManager to do the work
4. We send back a response (usually JSON)

ALL ENDPOINTS:
-------------
GET    /api/sensors/              - List all sensors
GET    /api/sensors/{id}          - Get one sensor
DELETE /api/sensors/{id}          - Delete a sensor
GET    /api/sensors/{id}/status   - Get sensor status
POST   /api/sensors/{id}/turn-on  - Start collecting data
POST   /api/sensors/{id}/turn-off - Stop collecting data
POST   /api/sensors/{id}/fetch-now - Manually fetch data right now

POST   /api/sensors/purple-air    - Add a Purple Air sensor
GET    /api/sensors/purple-air    - List Purple Air sensors

POST   /api/sensors/tempest       - Add a Tempest sensor
GET    /api/sensors/tempest       - List Tempest sensors

POST   /api/sensors/water-quality - Add Water Quality sensor (coming soon)
GET    /api/sensors/water-quality - List Water Quality sensors

POST   /api/sensors/do-sensor     - Add DO sensor (coming soon)
GET    /api/sensors/do-sensor     - List DO sensors

Author: Frank Kusi Appiah
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Optional

from app.models import (
    SensorType,
    AddPurpleAirSensorRequest,
    AddTempestSensorRequest,
    AddWaterQualitySensorRequest,
    AddDOSensorRequest,
    SensorResponse,
    SensorListResponse,
)


# Create the router - this groups all our sensor endpoints together
router = APIRouter(prefix="/api/sensors", tags=["sensors"])


# =============================================================================
# DEPENDENCY INJECTION
# =============================================================================
# This is a fancy way of saying "give the endpoints access to the SensorManager"

_sensor_manager = None  # This gets set when the app starts


def set_sensor_manager(manager):
    """
    Called when the app starts to give us the sensor manager.
    
    Think of this like: "Hey router, here's your manager to work with"
    """
    global _sensor_manager
    _sensor_manager = manager


def get_sensor_manager():
    """
    Get the sensor manager for use in endpoints.
    
    Every endpoint function that needs the manager uses this.
    """
    if _sensor_manager is None:
        raise HTTPException(status_code=500, detail="Server not fully started yet")
    return _sensor_manager


# =============================================================================
# PURPLE AIR ENDPOINTS
# =============================================================================

@router.post("/purple-air", response_model=SensorResponse)
async def add_purple_air_sensor(
    request: AddPurpleAirSensorRequest,
    manager = Depends(get_sensor_manager)
):
    """
    Add a new Purple Air sensor.
    
    Send us:
    - ip_address: The sensor's IP on your network (like "10.17.192.162")
    - name: What you want to call it (like "Lab Sensor")
    - location: Where it is (like "Science Building Room 201")
    - upload_token: Your token from oberlin.communityhub.cloud
    
    We'll give you back the sensor with its new ID.
    Then call /turn-on to start collecting data!
    """
    # Check if the IP looks valid
    parts = request.ip_address.split(".")
    if len(parts) != 4:
        raise HTTPException(status_code=400, detail="That doesn't look like a valid IP address. Should be like: 192.168.1.100")
    
    for part in parts:
        try:
            num = int(part)
            if num < 0 or num > 255:
                raise ValueError()
        except ValueError:
            raise HTTPException(status_code=400, detail="Each part of the IP should be a number from 0-255")
    
    # Check if we already have a sensor with this IP
    existing_sensors = manager.get_all_sensors(SensorType.PURPLE_AIR)
    for sensor in existing_sensors:
        if sensor.ip_address == request.ip_address:
            raise HTTPException(status_code=400, detail=f"You already have a sensor at {request.ip_address}!")
    
    # Add it!
    return manager.add_purple_air_sensor(request)


@router.get("/purple-air", response_model=SensorListResponse)
async def get_all_purple_air_sensors(manager = Depends(get_sensor_manager)):
    """
    Get all Purple Air sensors.
    
    Returns a list of all your Purple Air sensors with their current status.
    """
    sensors = manager.get_all_sensors(SensorType.PURPLE_AIR)
    return SensorListResponse(sensors=sensors, total=len(sensors))


# =============================================================================
# TEMPEST ENDPOINTS
# =============================================================================

@router.post("/tempest", response_model=SensorResponse)
async def add_tempest_sensor(
    request: AddTempestSensorRequest,
    manager = Depends(get_sensor_manager)
):
    """
    Add a Tempest weather station.
    
    Send us:
    - device_id: The Tempest device ID (find this in the WeatherFlow app)
    - location: Where it is
    - upload_token: Your cloud token
    """
    return manager.add_tempest_sensor(request)


@router.get("/tempest", response_model=SensorListResponse)
async def get_all_tempest_sensors(manager = Depends(get_sensor_manager)):
    """Get all Tempest weather stations."""
    sensors = manager.get_all_sensors(SensorType.TEMPEST)
    return SensorListResponse(sensors=sensors, total=len(sensors))


# =============================================================================
# WATER QUALITY ENDPOINTS (Coming Soon!)
# =============================================================================

@router.post("/water-quality", response_model=SensorResponse)
async def add_water_quality_sensor(
    request: AddWaterQualitySensorRequest,
    manager = Depends(get_sensor_manager)
):
    """
    Add a Water Quality sensor.
    
    Sorry, this isn't ready yet! We're still working on it.
    """
    raise HTTPException(status_code=501, detail="Water Quality sensors aren't ready yet. Coming soon!")


@router.get("/water-quality", response_model=SensorListResponse)
async def get_all_water_quality_sensors(manager = Depends(get_sensor_manager)):
    """Get all Water Quality sensors."""
    sensors = manager.get_all_sensors(SensorType.WATER_QUALITY)
    return SensorListResponse(sensors=sensors, total=len(sensors))


# =============================================================================
# DO SENSOR ENDPOINTS (Coming Soon!)
# =============================================================================

@router.post("/do-sensor", response_model=SensorResponse)
async def add_do_sensor(
    request: AddDOSensorRequest,
    manager = Depends(get_sensor_manager)
):
    """
    Add a Dissolved Oxygen sensor.
    
    Sorry, this isn't ready yet! We're still working on it.
    """
    raise HTTPException(status_code=501, detail="DO sensors aren't ready yet. Coming soon!")


@router.get("/do-sensor", response_model=SensorListResponse)
async def get_all_do_sensors(manager = Depends(get_sensor_manager)):
    """Get all Dissolved Oxygen sensors."""
    sensors = manager.get_all_sensors(SensorType.DO_SENSOR)
    return SensorListResponse(sensors=sensors, total=len(sensors))


# =============================================================================
# GENERAL SENSOR ENDPOINTS (Work for any sensor type)
# =============================================================================

@router.get("/", response_model=SensorListResponse)
async def get_all_sensors(
    sensor_type: Optional[SensorType] = None,
    manager = Depends(get_sensor_manager)
):
    """
    Get all sensors.
    
    You can filter by type:
    - /api/sensors/?sensor_type=purple_air
    - /api/sensors/?sensor_type=tempest
    
    Or just get everything:
    - /api/sensors/
    """
    sensors = manager.get_all_sensors(sensor_type)
    return SensorListResponse(sensors=sensors, total=len(sensors))


@router.get("/{sensor_id}", response_model=SensorResponse)
async def get_sensor(sensor_id: str, manager = Depends(get_sensor_manager)):
    """
    Get a specific sensor by its ID.
    
    The ID is the UUID you got when you added the sensor.
    """
    sensor = manager.get_sensor(sensor_id)
    if not sensor:
        raise HTTPException(status_code=404, detail="Sensor not found. Is the ID correct?")
    return sensor


@router.delete("/{sensor_id}")
async def delete_sensor(sensor_id: str, manager = Depends(get_sensor_manager)):
    """
    Delete a sensor.
    
    This stops data collection and removes the sensor completely.
    There's no undo! Make sure you want to do this.
    """
    success = manager.delete_sensor(sensor_id)
    if not success:
        raise HTTPException(status_code=404, detail="Sensor not found. Is the ID correct?")
    return {"status": "deleted", "sensor_id": sensor_id, "message": "Sensor has been removed"}


@router.get("/{sensor_id}/status")
async def get_sensor_status(sensor_id: str, manager = Depends(get_sensor_manager)):
    """
    Get the current status of a sensor.
    
    This tells you:
    - Is it active? (collecting data)
    - When did it last successfully collect data?
    - Is there an error?
    """
    status = manager.get_sensor_status(sensor_id)
    if not status:
        raise HTTPException(status_code=404, detail="Sensor not found")
    return status


@router.post("/{sensor_id}/turn-on", response_model=SensorResponse)
async def turn_on_sensor(sensor_id: str, manager = Depends(get_sensor_manager)):
    """
    Turn on a sensor - start collecting data!
    
    This starts the automatic polling:
    - Every 60 seconds, we fetch data from the sensor
    - Convert it to CSV
    - Upload it to the cloud
    
    The sensor status will change to "active".
    """
    sensor = await manager.turn_on_sensor(sensor_id)
    if not sensor:
        raise HTTPException(status_code=404, detail="Sensor not found")
    return sensor


@router.post("/{sensor_id}/turn-off", response_model=SensorResponse)
async def turn_off_sensor(sensor_id: str, manager = Depends(get_sensor_manager)):
    """
    Turn off a sensor - stop collecting data.
    
    The sensor stays registered, we just stop polling.
    You can turn it back on later!
    """
    sensor = manager.turn_off_sensor(sensor_id)
    if not sensor:
        raise HTTPException(status_code=404, detail="Sensor not found")
    return sensor


@router.post("/{sensor_id}/fetch-now")
async def trigger_fetch_now(sensor_id: str, manager = Depends(get_sensor_manager)):
    """
    Manually fetch data RIGHT NOW.
    
    Great for testing! You don't have to wait for the 60-second timer.
    
    Returns the actual data if successful, or an error message if not.
    """
    result = await manager.trigger_fetch_now(sensor_id)
    
    if result.get("status") == "error" and "not found" in result.get("error_message", "").lower():
        raise HTTPException(status_code=404, detail="Sensor not found")
    
    return result
