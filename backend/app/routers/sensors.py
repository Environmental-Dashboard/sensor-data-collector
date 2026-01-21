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
import io
import httpx

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
# HEALTH CHECK ENDPOINTS (Must come before parameterized routes)
# =============================================================================

@router.get("/health/upload-test")
async def test_upload_endpoint(
    upload_token: str,
    manager = Depends(get_sensor_manager)
):
    """
    Test the upload endpoint connectivity and token validity.
    
    This sends a minimal test CSV file to verify:
    - Connectivity to Community Hub
    - Token validity
    - Upload endpoint is working
    
    Args:
        upload_token: The token to test
    
    Returns:
        Success/error status with detailed diagnostics
    """
    from datetime import datetime, timezone
    
    test_csv = "Timestamp,Temperature (°F),Humidity (%)\n2026-01-01T00:00:00+00:00,72.0,45.0"
    upload_url = "https://oberlin.communityhub.cloud/api/data-hub/upload/csv"
    
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"test_{timestamp}.csv"
    
    headers = {"user-token": upload_token}
    csv_bytes = test_csv.encode("utf-8")
    csv_file = io.BytesIO(csv_bytes)
    files = {"file": (filename, csv_file, "text/csv")}
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(upload_url, headers=headers, files=files)
            response.raise_for_status()
            
            return {
                "status": "success",
                "message": "Upload endpoint is reachable and token is valid",
                "http_status": response.status_code,
                "test_file": filename,
                "upload_url": upload_url
            }
    except httpx.ConnectError as e:
        return {
            "status": "error",
            "error_type": "connection_error",
            "message": f"Cannot connect to upload endpoint: {str(e)}",
            "upload_url": upload_url
        }
    except httpx.HTTPStatusError as e:
        error_body = ""
        try:
            error_body = e.response.text[:500]
        except:
            pass
        
        return {
            "status": "error",
            "error_type": "http_error",
            "message": f"Upload endpoint returned HTTP {e.response.status_code}",
            "http_status": e.response.status_code,
            "error_response": error_body,
            "upload_url": upload_url
        }
    except Exception as e:
        return {
            "status": "error",
            "error_type": "unknown_error",
            "message": str(e),
            "upload_url": upload_url
        }


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


@router.get("/{sensor_id}/diagnostics")
async def get_sensor_diagnostics(sensor_id: str, manager = Depends(get_sensor_manager)):
    """
    Get detailed diagnostics for a sensor.
    
    Returns:
    - Last upload attempt timestamp
    - Last error details (if any)
    - Last CSV sample (truncated to 500 chars)
    - Network connectivity status (for Purple Air)
    - Sensor reachability
    """
    sensor = manager.get_sensor(sensor_id)
    if not sensor:
        raise HTTPException(status_code=404, detail="Sensor not found")
    
    # Get internal sensor data for diagnostics
    # Access internal sensors dict (we need to add a method for this)
    all_sensors = manager.get_all_sensors()
    sensor_obj = next((s for s in all_sensors if s.id == sensor_id), None)
    if not sensor_obj:
        raise HTTPException(status_code=404, detail="Sensor not found")
    
    # Get full sensor data including internal fields
    sensor_data = manager.get_sensor_data(sensor_id)
    if not sensor_data:
        raise HTTPException(status_code=404, detail="Sensor data not found")
    
    diagnostics = {
        "sensor_id": sensor_id,
        "sensor_name": sensor_data.get("name"),
        "sensor_type": sensor_data.get("sensor_type").value if sensor_data.get("sensor_type") else None,
        "status": sensor_data.get("status").value if sensor_data.get("status") else None,
        "is_active": sensor_data.get("is_active", False),
        "last_active": sensor_data.get("last_active").isoformat() if sensor_data.get("last_active") else None,
        "last_upload_attempt": sensor_data.get("last_upload_attempt"),
        "last_error": sensor_data.get("last_error"),
        "last_error_details": sensor_data.get("last_error_details"),
        "last_csv_sample": sensor_data.get("last_csv_sample"),  # Truncated CSV
    }
    
    # Add connectivity check for Purple Air sensors
    if sensor_data.get("sensor_type") == SensorType.PURPLE_AIR:
        ip_address = sensor_data.get("ip_address")
        if ip_address:
            # Try to ping the sensor
            import httpx
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    response = await client.get(f"http://{ip_address}/json", timeout=5.0)
                    diagnostics["connectivity"] = {
                        "reachable": True,
                        "response_time_ms": response.elapsed.total_seconds() * 1000,
                        "status_code": response.status_code
                    }
            except Exception as e:
                diagnostics["connectivity"] = {
                    "reachable": False,
                    "error": str(e)
                }
    
    return diagnostics


@router.get("/{sensor_id}/csv-preview")
async def get_csv_preview(sensor_id: str, manager = Depends(get_sensor_manager)):
    """
    Get a preview of the CSV that would be generated for this sensor.
    
    This helps debug CSV format issues by showing exactly what would be uploaded.
    """
    sensor = manager.get_sensor(sensor_id)
    if not sensor:
        raise HTTPException(status_code=404, detail="Sensor not found")
    
    # Trigger a fetch to get current data
    result = await manager.trigger_fetch_now(sensor_id)
    
    if result.get("status") == "success":
        # Extract CSV from upload result if available
        upload_result = result.get("upload_result", {})
        csv_sample = upload_result.get("csv_sample", "CSV sample not available")
        
        return {
            "sensor_id": sensor_id,
            "sensor_name": sensor.name,
            "csv_preview": csv_sample,
            "csv_length": len(csv_sample),
            "note": "This is the CSV that was generated. Check if format matches Community Hub requirements."
        }
    else:
        return {
            "sensor_id": sensor_id,
            "sensor_name": sensor.name,
            "error": result.get("error_message", "Unknown error"),
            "note": "Could not generate CSV preview due to error"
        }
