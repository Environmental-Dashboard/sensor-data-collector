"""
Sensor Manager
==============

This is the BRAIN of the whole operation!

WHAT IT DOES:
------------
1. Keeps track of all registered sensors
2. Handles adding, deleting, turning on/off sensors
3. Schedules automatic data collection (every 60 seconds)
4. Updates sensor status based on success/failure

THINK OF IT LIKE THIS:
---------------------
You're a manager at a factory. You have workers (sensors).
- You hire workers (add sensors)
- You fire workers (delete sensors)
- You tell workers to start working (turn on)
- You tell workers to take a break (turn off)
- You check on workers (get status)
- Workers do their job every minute automatically (polling)

HOW AUTOMATIC POLLING WORKS:
---------------------------
1. User adds a sensor (it starts as "inactive")
2. User turns it on
3. We create a scheduled job that runs every 60 seconds
4. Every 60 seconds:
   - We call the sensor
   - Get the data
   - Convert to CSV
   - Upload to cloud
   - Update status (success or error)
5. User can turn it off to stop

Author: Frank Kusi Appiah
"""

import uuid
from datetime import datetime, timezone
from typing import Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.models import (
    SensorType,
    SensorStatus,
    SensorResponse,
    AddPurpleAirSensorRequest,
    AddTempestSensorRequest,
)
from app.services.purple_air_service import PurpleAirService
from app.services.tempest_service import TempestService


class SensorManager:
    """
    The central manager for all sensors.
    
    This is created once when the server starts and handles everything.
    
    EXAMPLE USAGE:
    -------------
    # Add a sensor
    sensor = manager.add_purple_air_sensor(request)
    
    # Turn it on (starts collecting data every 60 seconds)
    await manager.turn_on_sensor(sensor.id)
    
    # Check status
    status = manager.get_sensor_status(sensor.id)
    
    # Manually fetch data right now (for testing)
    result = await manager.trigger_fetch_now(sensor.id)
    
    # Turn it off
    manager.turn_off_sensor(sensor.id)
    
    # Delete it
    manager.delete_sensor(sensor.id)
    """
    
    def __init__(
        self,
        purple_air_service: PurpleAirService,
        tempest_service: TempestService,
        polling_interval: int = 60
    ):
        """
        Set up the manager.
        
        Args:
            purple_air_service: The service that handles Purple Air sensors
            tempest_service: The service that handles Tempest sensors
            polling_interval: How often to fetch data (seconds). Default is 60.
        """
        self.purple_air_service = purple_air_service
        self.tempest_service = tempest_service
        self.polling_interval = polling_interval
        
        # This is where we store all sensors
        # It's a dictionary: sensor_id -> sensor_data
        # In a real production app, this would be a database!
        self._sensors: dict[str, dict] = {}
        
        # This is the scheduler - it runs jobs on a timer
        # Think of it like a cron job or Task Scheduler
        self.scheduler = AsyncIOScheduler()
        self.scheduler.start()
    
    
    # =========================================================================
    # ADDING SENSORS
    # =========================================================================
    
    def add_purple_air_sensor(self, request: AddPurpleAirSensorRequest) -> SensorResponse:
        """
        Register a new Purple Air sensor.
        
        What happens:
        1. We generate a unique ID for this sensor
        2. We save it in our storage
        3. We return the sensor info
        
        The sensor starts as INACTIVE - you need to call turn_on() to start
        collecting data!
        
        Args:
            request: The sensor info (ip_address, name, location, upload_token)
        
        Returns:
            The created sensor with its new ID
        """
        # Generate a unique ID (UUID = Universally Unique Identifier)
        sensor_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        
        # Create the sensor record
        sensor_data = {
            "id": sensor_id,
            "sensor_type": SensorType.PURPLE_AIR,
            "name": request.name,
            "location": request.location,
            "ip_address": request.ip_address,
            "device_id": None,  # Not used for Purple Air
            "upload_token": request.upload_token,  # The user's cloud token
            "status": SensorStatus.INACTIVE,
            "is_active": False,
            "last_active": None,
            "last_error": None,
            "created_at": now,
        }
        
        # Save it
        self._sensors[sensor_id] = sensor_data
        
        # Return the response (without the token for security)
        return SensorResponse(**{k: v for k, v in sensor_data.items() if k != "upload_token"})
    
    
    def add_tempest_sensor(self, request: AddTempestSensorRequest) -> SensorResponse:
        """
        Register a new Tempest weather station.
        
        Same as Purple Air but with device_id.
        """
        sensor_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        
        sensor_data = {
            "id": sensor_id,
            "sensor_type": SensorType.TEMPEST,
            "name": request.name,
            "location": request.location,
            "ip_address": request.ip_address,
            "device_id": request.device_id,
            "upload_token": request.upload_token,
            "status": SensorStatus.INACTIVE,
            "is_active": False,
            "last_active": None,
            "last_error": None,
            "created_at": now,
        }
        
        self._sensors[sensor_id] = sensor_data
        
        return SensorResponse(**{k: v for k, v in sensor_data.items() if k != "upload_token"})
    
    
    # =========================================================================
    # GETTING SENSORS
    # =========================================================================
    
    def get_sensor(self, sensor_id: str) -> Optional[SensorResponse]:
        """
        Get a single sensor by ID.
        
        Args:
            sensor_id: The sensor's unique ID
        
        Returns:
            The sensor info, or None if not found
        """
        sensor_data = self._sensors.get(sensor_id)
        if sensor_data:
            return SensorResponse(**{k: v for k, v in sensor_data.items() if k != "upload_token"})
        return None
    
    
    def get_all_sensors(self, sensor_type: Optional[SensorType] = None) -> list[SensorResponse]:
        """
        Get all sensors, optionally filtered by type.
        
        Args:
            sensor_type: If provided, only return sensors of this type
        
        Returns:
            List of sensors
        
        Examples:
            # Get ALL sensors
            all_sensors = manager.get_all_sensors()
            
            # Get only Purple Air sensors
            pa_sensors = manager.get_all_sensors(SensorType.PURPLE_AIR)
        """
        sensors = list(self._sensors.values())
        
        if sensor_type:
            sensors = [s for s in sensors if s["sensor_type"] == sensor_type]
        
        # Remove tokens from response
        return [SensorResponse(**{k: v for k, v in s.items() if k != "upload_token"}) for s in sensors]
    
    
    def delete_sensor(self, sensor_id: str) -> bool:
        """
        Delete a sensor.
        
        This stops any running polling and removes the sensor completely.
        
        Args:
            sensor_id: The sensor's unique ID
        
        Returns:
            True if deleted, False if sensor wasn't found
        """
        if sensor_id not in self._sensors:
            return False
        
        # Stop the polling job if it's running
        self._stop_polling_job(sensor_id)
        
        # Remove from storage
        del self._sensors[sensor_id]
        
        return True
    
    
    # =========================================================================
    # TURNING SENSORS ON/OFF
    # =========================================================================
    
    async def turn_on_sensor(self, sensor_id: str) -> Optional[SensorResponse]:
        """
        Turn on a sensor - start collecting data!
        
        What happens:
        1. We create a scheduled job
        2. The job runs every 60 seconds
        3. Each run: fetch data, convert to CSV, upload
        4. Status is set to ACTIVE
        
        Args:
            sensor_id: The sensor to turn on
        
        Returns:
            Updated sensor info, or None if not found
        """
        if sensor_id not in self._sensors:
            return None
        
        sensor = self._sensors[sensor_id]
        
        # Already on? Just return
        if sensor["is_active"]:
            return SensorResponse(**{k: v for k, v in sensor.items() if k != "upload_token"})
        
        # Start polling based on sensor type
        if sensor["sensor_type"] == SensorType.PURPLE_AIR:
            self._start_polling_job(sensor_id, self._poll_purple_air_sensor)
        elif sensor["sensor_type"] == SensorType.TEMPEST:
            self._start_polling_job(sensor_id, self._poll_tempest_sensor)
        
        # Update status
        sensor["is_active"] = True
        sensor["status"] = SensorStatus.ACTIVE
        
        return SensorResponse(**{k: v for k, v in sensor.items() if k != "upload_token"})
    
    
    def turn_off_sensor(self, sensor_id: str) -> Optional[SensorResponse]:
        """
        Turn off a sensor - stop collecting data.
        
        The sensor stays registered, we just stop the automatic polling.
        You can turn it back on later.
        
        Args:
            sensor_id: The sensor to turn off
        
        Returns:
            Updated sensor info, or None if not found
        """
        if sensor_id not in self._sensors:
            return None
        
        sensor = self._sensors[sensor_id]
        
        # Stop the polling job
        self._stop_polling_job(sensor_id)
        
        # Update status
        sensor["is_active"] = False
        sensor["status"] = SensorStatus.INACTIVE
        
        return SensorResponse(**{k: v for k, v in sensor.items() if k != "upload_token"})
    
    
    def get_sensor_status(self, sensor_id: str) -> Optional[dict]:
        """
        Get detailed status for a sensor.
        
        Returns:
            {
                "id": "...",
                "name": "Lab Sensor",
                "status": "active",
                "is_active": true,
                "last_active": "2026-01-06T03:00:00",
                "last_error": null
            }
        """
        sensor = self._sensors.get(sensor_id)
        if not sensor:
            return None
        
        return {
            "id": sensor_id,
            "name": sensor["name"],
            "status": sensor["status"],
            "is_active": sensor["is_active"],
            "last_active": sensor["last_active"].isoformat() if sensor["last_active"] else None,
            "last_error": sensor["last_error"],
        }
    
    
    # =========================================================================
    # POLLING JOBS (The automatic data collection)
    # =========================================================================
    
    def _start_polling_job(self, sensor_id: str, callback):
        """
        Start a polling job for a sensor.
        
        This creates a job that runs every 60 seconds (or whatever polling_interval is).
        """
        job_id = f"poll_{sensor_id}"
        
        self.scheduler.add_job(
            callback,
            trigger=IntervalTrigger(seconds=self.polling_interval),
            id=job_id,
            args=[sensor_id],
            replace_existing=True,
        )
    
    
    def _stop_polling_job(self, sensor_id: str):
        """Stop the polling job for a sensor."""
        job_id = f"poll_{sensor_id}"
        try:
            self.scheduler.remove_job(job_id)
        except Exception:
            pass  # Job might not exist
    
    
    async def _poll_purple_air_sensor(self, sensor_id: str):
        """
        This runs every 60 seconds for active Purple Air sensors.
        
        It fetches data from the sensor and uploads it.
        """
        sensor = self._sensors.get(sensor_id)
        if not sensor:
            return
        
        # Call the Purple Air service
        result = await self.purple_air_service.fetch_and_push(
            ip_address=sensor["ip_address"],
            sensor_name=sensor["name"],
            upload_token=sensor["upload_token"]
        )
        
        # Update status based on result
        if result["status"] == "success":
            sensor["status"] = SensorStatus.ACTIVE
            sensor["last_active"] = datetime.now(timezone.utc)
            sensor["last_error"] = None
        else:
            sensor["status"] = SensorStatus.ERROR
            sensor["last_error"] = result.get("error_message", "Unknown error")
    
    
    async def _poll_tempest_sensor(self, sensor_id: str):
        """
        This runs every 60 seconds for active Tempest sensors.
        """
        sensor = self._sensors.get(sensor_id)
        if not sensor:
            return
        
        result = await self.tempest_service.fetch_and_push(
            ip_address=sensor["ip_address"],
            device_id=sensor["device_id"],
            sensor_name=sensor["name"],
            upload_token=sensor["upload_token"]
        )
        
        if result["status"] == "success":
            sensor["status"] = SensorStatus.ACTIVE
            sensor["last_active"] = datetime.now(timezone.utc)
            sensor["last_error"] = None
        else:
            sensor["status"] = SensorStatus.ERROR
            sensor["last_error"] = result.get("error_message", "Unknown error")
    
    
    # =========================================================================
    # MANUAL FETCH (For Testing)
    # =========================================================================
    
    async def trigger_fetch_now(self, sensor_id: str) -> dict:
        """
        Manually trigger a fetch RIGHT NOW.
        
        This is great for testing - you don't have to wait 60 seconds!
        
        Args:
            sensor_id: The sensor to fetch from
        
        Returns:
            The result of the fetch (success with data, or error with message)
        """
        sensor = self._sensors.get(sensor_id)
        if not sensor:
            return {"status": "error", "error_message": "Sensor not found"}
        
        if sensor["sensor_type"] == SensorType.PURPLE_AIR:
            result = await self.purple_air_service.fetch_and_push(
                ip_address=sensor["ip_address"],
                sensor_name=sensor["name"],
                upload_token=sensor["upload_token"]
            )
        elif sensor["sensor_type"] == SensorType.TEMPEST:
            result = await self.tempest_service.fetch_and_push(
                ip_address=sensor["ip_address"],
                device_id=sensor["device_id"],
                sensor_name=sensor["name"],
                upload_token=sensor["upload_token"]
            )
        else:
            return {"status": "error", "error_message": f"Unknown sensor type: {sensor['sensor_type']}"}
        
        # Update status
        if result["status"] == "success":
            sensor["status"] = SensorStatus.ACTIVE
            sensor["last_active"] = datetime.now(timezone.utc)
            sensor["last_error"] = None
        else:
            sensor["status"] = SensorStatus.ERROR
            sensor["last_error"] = result.get("error_message")
        
        return result
    
    
    # =========================================================================
    # CLEANUP
    # =========================================================================
    
    async def shutdown(self):
        """
        Clean up when the server is shutting down.
        
        This stops all polling jobs and closes network connections.
        """
        self.scheduler.shutdown(wait=False)
        await self.purple_air_service.close()
        await self.tempest_service.close()
