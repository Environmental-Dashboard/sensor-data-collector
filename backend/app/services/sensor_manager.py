"""
Sensor Manager
==============

This is the BRAIN of the whole operation!

WHAT IT DOES:
------------
1. Keeps track of all registered sensors (persisted to JSON file)
2. Handles adding, deleting, turning on/off sensors
3. Schedules automatic data collection (every 60 seconds)
4. Updates sensor status based on success/failure

NOW WITH PERSISTENCE:
--------------------
Sensors are saved to a JSON file (sensors_db.json) so they survive restarts!
- Add a sensor = saved to file
- Delete a sensor = removed from file
- Restart server = sensors are loaded back automatically

Author: Frank Kusi Appiah
"""

import json
import uuid
import os
from datetime import datetime, timezone
from typing import Optional
from pathlib import Path
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
    
    Sensors are now persisted to a JSON file so they survive server restarts!
    """
    
    # Where to store the sensors database
    DB_FILE = Path(__file__).parent.parent.parent / "sensors_db.json"
    
    def __init__(
        self,
        purple_air_service: PurpleAirService,
        tempest_service: TempestService,
        polling_interval: int = 60,
        tempest_api_token: str = ""
    ):
        """
        Set up the manager.
        
        Args:
            purple_air_service: The service that handles Purple Air sensors
            tempest_service: The service that handles Tempest sensors
            polling_interval: How often to fetch data (seconds). Default is 60.
            tempest_api_token: WeatherFlow API token for all Tempest sensors
        """
        self.purple_air_service = purple_air_service
        self.tempest_service = tempest_service
        self.polling_interval = polling_interval
        self.tempest_api_token = tempest_api_token
        
        # This is where we store all sensors in memory
        self._sensors: dict[str, dict] = {}
        
        # Load sensors from file
        self._load_from_file()
        
        # This is the scheduler - it runs jobs on a timer
        self.scheduler = AsyncIOScheduler()
        self.scheduler.start()
        
        # Restart polling for sensors that were active
        self._restart_active_sensors()
    
    
    # =========================================================================
    # DATABASE PERSISTENCE
    # =========================================================================
    
    def _load_from_file(self):
        """Load sensors from the JSON file."""
        if not self.DB_FILE.exists():
            print(f"No existing database found at {self.DB_FILE}")
            return
        
        try:
            with open(self.DB_FILE, 'r') as f:
                data = json.load(f)
            
            # Convert the data back to proper types
            for sensor_id, sensor in data.items():
                # Convert string types back to enums
                sensor["sensor_type"] = SensorType(sensor["sensor_type"])
                sensor["status"] = SensorStatus(sensor["status"])
                
                # Convert datetime strings back to datetime objects
                if sensor.get("last_active"):
                    sensor["last_active"] = datetime.fromisoformat(sensor["last_active"])
                if sensor.get("created_at"):
                    sensor["created_at"] = datetime.fromisoformat(sensor["created_at"])
                
                self._sensors[sensor_id] = sensor
            
            print(f"Loaded {len(self._sensors)} sensors from database")
        except Exception as e:
            print(f"Error loading sensors database: {e}")
    
    
    def _save_to_file(self):
        """Save sensors to the JSON file."""
        try:
            # Convert to JSON-serializable format
            data = {}
            for sensor_id, sensor in self._sensors.items():
                sensor_copy = sensor.copy()
                
                # Convert enums to strings
                sensor_copy["sensor_type"] = sensor_copy["sensor_type"].value
                sensor_copy["status"] = sensor_copy["status"].value
                
                # Convert datetimes to ISO strings
                if sensor_copy.get("last_active"):
                    sensor_copy["last_active"] = sensor_copy["last_active"].isoformat()
                if sensor_copy.get("created_at"):
                    sensor_copy["created_at"] = sensor_copy["created_at"].isoformat()
                
                data[sensor_id] = sensor_copy
            
            with open(self.DB_FILE, 'w') as f:
                json.dump(data, f, indent=2)
            
        except Exception as e:
            print(f"Error saving sensors database: {e}")
    
    
    def _restart_active_sensors(self):
        """Restart data collection for sensors that were active before shutdown."""
        for sensor_id, sensor in self._sensors.items():
            if sensor.get("is_active"):
                print(f"Restarting data collection for sensor: {sensor['name']}")
                if sensor["sensor_type"] == SensorType.PURPLE_AIR:
                    self._start_polling_job(sensor_id, self._poll_purple_air_sensor)
                elif sensor["sensor_type"] == SensorType.TEMPEST:
                    # Tempest uses cloud WebSocket listener (uses centralized API token)
                    self.tempest_service.start_listener(
                        device_id=sensor["device_id"],
                        api_token=self.tempest_api_token,
                        upload_token=sensor["upload_token"],
                        sensor_name=sensor["name"],
                        on_data_callback=self._on_tempest_data
                    )
    
    
    # =========================================================================
    # ADDING SENSORS
    # =========================================================================
    
    def add_purple_air_sensor(self, request: AddPurpleAirSensorRequest) -> SensorResponse:
        """
        Register a new Purple Air sensor.
        """
        sensor_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        
        sensor_data = {
            "id": sensor_id,
            "sensor_type": SensorType.PURPLE_AIR,
            "name": request.name,
            "location": request.location,
            "ip_address": request.ip_address,
            "device_id": None,
            "upload_token": request.upload_token,
            "status": SensorStatus.INACTIVE,
            "is_active": False,
            "last_active": None,
            "last_error": None,
            "created_at": now,
        }
        
        self._sensors[sensor_id] = sensor_data
        self._save_to_file()  # Persist to disk
        
        return SensorResponse(**{k: v for k, v in sensor_data.items() if k != "upload_token"})
    
    
    def add_tempest_sensor(self, request: AddTempestSensorRequest) -> SensorResponse:
        """
        Register a new Tempest weather station.
        
        Uses WeatherFlow cloud WebSocket API for real-time data.
        API docs: https://weatherflow.github.io/Tempest/api/
        
        Note: API token is stored centrally in backend config, not per-sensor.
        """
        sensor_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        
        sensor_data = {
            "id": sensor_id,
            "sensor_type": SensorType.TEMPEST,
            "name": request.device_id,  # Use device_id as name
            "location": request.location,
            "ip_address": None,  # Not used for cloud API
            "device_id": request.device_id,
            "upload_token": request.upload_token,
            "status": SensorStatus.INACTIVE,
            "is_active": False,
            "last_active": None,
            "last_error": None,
            "created_at": now,
            "battery_volts": None,  # Will be updated when data is fetched
        }
        
        self._sensors[sensor_id] = sensor_data
        self._save_to_file()  # Persist to disk
        
        return SensorResponse(**{k: v for k, v in sensor_data.items() if k != "upload_token"})
    
    
    # =========================================================================
    # GETTING SENSORS
    # =========================================================================
    
    def get_sensor(self, sensor_id: str) -> Optional[SensorResponse]:
        """Get a single sensor by ID."""
        sensor_data = self._sensors.get(sensor_id)
        if sensor_data:
            return SensorResponse(**{k: v for k, v in sensor_data.items() if k != "upload_token"})
        return None
    
    
    def get_all_sensors(self, sensor_type: Optional[SensorType] = None) -> list[SensorResponse]:
        """Get all sensors, optionally filtered by type."""
        sensors = list(self._sensors.values())
        
        if sensor_type:
            sensors = [s for s in sensors if s["sensor_type"] == sensor_type]
        
        return [SensorResponse(**{k: v for k, v in s.items() if k != "upload_token"}) for s in sensors]
    
    
    def delete_sensor(self, sensor_id: str) -> bool:
        """Delete a sensor permanently."""
        if sensor_id not in self._sensors:
            return False
        
        self._stop_polling_job(sensor_id)
        del self._sensors[sensor_id]
        self._save_to_file()  # Persist to disk
        
        return True
    
    
    # =========================================================================
    # TURNING SENSORS ON/OFF
    # =========================================================================
    
    async def turn_on_sensor(self, sensor_id: str) -> Optional[SensorResponse]:
        """Turn on a sensor - start collecting data!"""
        if sensor_id not in self._sensors:
            return None
        
        sensor = self._sensors[sensor_id]
        
        if sensor["is_active"]:
            return SensorResponse(**{k: v for k, v in sensor.items() if k != "upload_token"})
        
        # Clear old error when turning on
        sensor["last_error"] = None
        
        # Start data collection based on sensor type
        if sensor["sensor_type"] == SensorType.PURPLE_AIR:
            self._start_polling_job(sensor_id, self._poll_purple_air_sensor)
        elif sensor["sensor_type"] == SensorType.TEMPEST:
            # Tempest uses cloud WebSocket listener (uses centralized API token)
            self.tempest_service.start_listener(
                device_id=sensor["device_id"],
                api_token=self.tempest_api_token,
                upload_token=sensor["upload_token"],
                sensor_name=sensor["name"],
                on_data_callback=self._on_tempest_data
            )
        
        sensor["is_active"] = True
        sensor["status"] = SensorStatus.ACTIVE
        self._save_to_file()  # Persist to disk
        
        return SensorResponse(**{k: v for k, v in sensor.items() if k != "upload_token"})
    
    
    def turn_off_sensor(self, sensor_id: str) -> Optional[SensorResponse]:
        """Turn off a sensor - stop collecting data."""
        if sensor_id not in self._sensors:
            return None
        
        sensor = self._sensors[sensor_id]
        
        # Stop data collection based on sensor type
        if sensor["sensor_type"] == SensorType.PURPLE_AIR:
            self._stop_polling_job(sensor_id)
        elif sensor["sensor_type"] == SensorType.TEMPEST:
            self.tempest_service.stop_listener(sensor["device_id"])
        
        sensor["is_active"] = False
        sensor["status"] = SensorStatus.INACTIVE
        self._save_to_file()  # Persist to disk
        
        return SensorResponse(**{k: v for k, v in sensor.items() if k != "upload_token"})
    
    
    def get_sensor_status(self, sensor_id: str) -> Optional[dict]:
        """Get detailed status for a sensor."""
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
    # POLLING JOBS
    # =========================================================================
    
    def _start_polling_job(self, sensor_id: str, callback):
        """Start a polling job for a sensor."""
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
            pass
    
    
    async def _poll_purple_air_sensor(self, sensor_id: str):
        """Poll a Purple Air sensor (runs every 60 seconds)."""
        sensor = self._sensors.get(sensor_id)
        if not sensor:
            return
        
        result = await self.purple_air_service.fetch_and_push(
            ip_address=sensor["ip_address"],
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
        
        self._save_to_file()  # Persist status updates
    
    
    async def _on_tempest_data(self, device_id: str, result: dict):
        """
        Callback when Tempest data is received from cloud WebSocket.
        
        This is called automatically whenever WeatherFlow sends new data.
        """
        # Find the sensor by device_id
        sensor = None
        for s in self._sensors.values():
            if s.get("device_id") == device_id and s["sensor_type"] == SensorType.TEMPEST:
                sensor = s
                break
        
        if not sensor:
            return
        
        if result["status"] == "success":
            sensor["status"] = SensorStatus.ACTIVE
            sensor["last_active"] = datetime.now(timezone.utc)
            sensor["last_error"] = None
            # Store battery voltage from the reading
            reading = result.get("reading", {})
            if reading.get("battery_volts"):
                sensor["battery_volts"] = reading["battery_volts"]
            print(f"Tempest {device_id}: Data received and uploaded")
        else:
            sensor["status"] = SensorStatus.ERROR
            sensor["last_error"] = result.get("error_message", "Unknown error")
            print(f"Tempest {device_id}: Error - {sensor['last_error']}")
        
        self._save_to_file()  # Persist status updates
    
    
    # =========================================================================
    # MANUAL FETCH
    # =========================================================================
    
    async def trigger_fetch_now(self, sensor_id: str) -> dict:
        """Manually trigger a fetch RIGHT NOW."""
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
            # Tempest uses continuous listener - data is pushed automatically
            # For manual fetch, we just return the current status
            return {
                "status": "info",
                "sensor_name": sensor["name"],
                "message": "Tempest sensors push data automatically when received. No manual fetch needed.",
                "last_active": sensor["last_active"].isoformat() if sensor["last_active"] else None,
                "battery_volts": sensor.get("battery_volts")
            }
        else:
            return {"status": "error", "error_message": f"Unknown sensor type: {sensor['sensor_type']}"}
        
        if result["status"] == "success":
            sensor["status"] = SensorStatus.ACTIVE
            sensor["last_active"] = datetime.now(timezone.utc)
            sensor["last_error"] = None
            # Store battery voltage for Tempest sensors
            if sensor["sensor_type"] == SensorType.TEMPEST:
                reading = result.get("reading", {})
                if reading.get("battery_volts"):
                    sensor["battery_volts"] = reading["battery_volts"]
        else:
            sensor["status"] = SensorStatus.ERROR
            sensor["last_error"] = result.get("error_message")
        
        self._save_to_file()  # Persist status updates
        
        return result
    
    
    # =========================================================================
    # CLEANUP
    # =========================================================================
    
    async def shutdown(self):
        """Clean up when the server is shutting down."""
        self._save_to_file()  # Save one last time
        self.scheduler.shutdown(wait=False)
        await self.purple_air_service.close()
        await self.tempest_service.close()
