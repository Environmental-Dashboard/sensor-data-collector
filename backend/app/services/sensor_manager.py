"""
Sensor Manager Service
======================
Central manager for all sensor types.

This is the core service that orchestrates:
- Sensor registration (CRUD operations)
- Status tracking
- Polling schedules (automatic data collection)
- Coordination between sensor services

ARCHITECTURE:
    The SensorManager is instantiated once at application startup.
    It maintains:
    - In-memory sensor registry (dict of sensor configs)
    - APScheduler instance for polling jobs
    - References to individual sensor services

POLLING WORKFLOW:
    1. User adds a sensor via API
    2. User turns on the sensor
    3. SensorManager creates a scheduled job
    4. Every interval (default 60s), the job:
       - Calls the appropriate sensor service
       - Updates sensor status based on result
    5. User can turn off to stop polling

Author: Sensor Data Collector Team
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
    Central manager for all sensors in the system.
    
    This class provides a unified interface for managing sensors
    of all types. It handles:
    
    - CRUD operations (Add, Get, Delete sensors)
    - Sensor control (Turn on/off data collection)
    - Status tracking (Last active, errors)
    - Scheduling (Automatic polling at configured interval)
    
    Usage:
        # Initialize with services
        manager = SensorManager(
            purple_air_service=purple_air_service,
            tempest_service=tempest_service,
            polling_interval=60
        )
        
        # Add a sensor
        sensor = manager.add_purple_air_sensor(request)
        
        # Start polling
        await manager.turn_on_sensor(sensor.id)
        
        # Manual fetch
        result = await manager.trigger_fetch_now(sensor.id)
        
        # Stop polling
        manager.turn_off_sensor(sensor.id)
        
        # Remove sensor
        manager.delete_sensor(sensor.id)
    
    Attributes:
        purple_air_service: Service for Purple Air sensors
        tempest_service: Service for Tempest weather stations
        polling_interval: Seconds between automatic fetches
        scheduler: APScheduler instance for polling jobs
    """
    
    def __init__(
        self,
        purple_air_service: PurpleAirService,
        tempest_service: TempestService,
        polling_interval: int = 60
    ):
        """
        Initialize the sensor manager.
        
        Args:
            purple_air_service: Initialized PurpleAirService instance
            tempest_service: Initialized TempestService instance
            polling_interval: How often to poll sensors (seconds)
        """
        self.purple_air_service = purple_air_service
        self.tempest_service = tempest_service
        self.polling_interval = polling_interval
        
        # In-memory sensor storage
        # Key: sensor_id (str)
        # Value: sensor data dict
        self._sensors: dict[str, dict] = {}
        
        # APScheduler for polling jobs
        self.scheduler = AsyncIOScheduler()
        self.scheduler.start()
    
    # =========================================================================
    # SENSOR CRUD OPERATIONS
    # =========================================================================
    
    def add_purple_air_sensor(
        self, 
        request: AddPurpleAirSensorRequest
    ) -> SensorResponse:
        """
        Register a new Purple Air sensor.
        
        Creates a sensor record with the provided configuration.
        The sensor starts in INACTIVE state - call turn_on_sensor()
        to start data collection.
        
        Args:
            request: Contains ip_address, name, location
            
        Returns:
            Created sensor response
            
        Example:
            request = AddPurpleAirSensorRequest(
                ip_address="192.168.1.100",
                name="Lab Sensor",
                location="Science Building"
            )
            sensor = manager.add_purple_air_sensor(request)
            print(sensor.id)  # UUID
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
            "status": SensorStatus.INACTIVE,
            "is_active": False,
            "last_active": None,
            "last_error": None,
            "created_at": now,
        }
        
        self._sensors[sensor_id] = sensor_data
        
        return SensorResponse(**sensor_data)
    
    def add_tempest_sensor(
        self, 
        request: AddTempestSensorRequest
    ) -> SensorResponse:
        """
        Register a new Tempest weather station.
        
        Args:
            request: Contains ip_address, name, location, device_id
            
        Returns:
            Created sensor response
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
            "status": SensorStatus.INACTIVE,
            "is_active": False,
            "last_active": None,
            "last_error": None,
            "created_at": now,
        }
        
        self._sensors[sensor_id] = sensor_data
        
        return SensorResponse(**sensor_data)
    
    def get_sensor(self, sensor_id: str) -> Optional[SensorResponse]:
        """
        Get a sensor by ID.
        
        Args:
            sensor_id: UUID of the sensor
            
        Returns:
            Sensor data or None if not found
        """
        sensor_data = self._sensors.get(sensor_id)
        if sensor_data:
            return SensorResponse(**sensor_data)
        return None
    
    def get_all_sensors(
        self, 
        sensor_type: Optional[SensorType] = None
    ) -> list[SensorResponse]:
        """
        Get all sensors, optionally filtered by type.
        
        Args:
            sensor_type: Filter by type (optional)
            
        Returns:
            List of sensor responses
            
        Example:
            # Get all sensors
            all_sensors = manager.get_all_sensors()
            
            # Get only Purple Air sensors
            pa_sensors = manager.get_all_sensors(SensorType.PURPLE_AIR)
        """
        sensors = list(self._sensors.values())
        
        if sensor_type:
            sensors = [s for s in sensors if s["sensor_type"] == sensor_type]
        
        return [SensorResponse(**s) for s in sensors]
    
    def delete_sensor(self, sensor_id: str) -> bool:
        """
        Delete a sensor.
        
        Stops any active polling and removes the sensor from registry.
        
        Args:
            sensor_id: UUID of the sensor
            
        Returns:
            True if deleted, False if not found
        """
        if sensor_id not in self._sensors:
            return False
        
        # Stop polling if active
        self._stop_polling_job(sensor_id)
        
        # Remove from storage
        del self._sensors[sensor_id]
        
        return True
    
    # =========================================================================
    # SENSOR CONTROL (Turn On/Off)
    # =========================================================================
    
    async def turn_on_sensor(self, sensor_id: str) -> Optional[SensorResponse]:
        """
        Turn on data collection for a sensor.
        
        Creates a scheduled job that runs every polling_interval seconds.
        The job fetches data from the sensor and pushes it to the endpoint.
        
        Args:
            sensor_id: UUID of the sensor
            
        Returns:
            Updated sensor or None if not found
            
        Side Effects:
            - Creates APScheduler job
            - Updates sensor status to ACTIVE
            - Sets is_active to True
        """
        if sensor_id not in self._sensors:
            return None
        
        sensor = self._sensors[sensor_id]
        
        # Already active? Return as-is
        if sensor["is_active"]:
            return SensorResponse(**sensor)
        
        # Start polling based on sensor type
        if sensor["sensor_type"] == SensorType.PURPLE_AIR:
            self._start_polling_job(
                sensor_id=sensor_id,
                callback=self._poll_purple_air_sensor
            )
        elif sensor["sensor_type"] == SensorType.TEMPEST:
            self._start_polling_job(
                sensor_id=sensor_id,
                callback=self._poll_tempest_sensor
            )
        
        # Update status
        sensor["is_active"] = True
        sensor["status"] = SensorStatus.ACTIVE
        
        return SensorResponse(**sensor)
    
    def turn_off_sensor(self, sensor_id: str) -> Optional[SensorResponse]:
        """
        Turn off data collection for a sensor.
        
        Stops the scheduled polling job. The sensor remains registered
        and can be turned on again later.
        
        Args:
            sensor_id: UUID of the sensor
            
        Returns:
            Updated sensor or None if not found
        """
        if sensor_id not in self._sensors:
            return None
        
        sensor = self._sensors[sensor_id]
        
        # Stop the polling job
        self._stop_polling_job(sensor_id)
        
        # Update status
        sensor["is_active"] = False
        sensor["status"] = SensorStatus.INACTIVE
        
        return SensorResponse(**sensor)
    
    def get_sensor_status(self, sensor_id: str) -> Optional[dict]:
        """
        Get current status details for a sensor.
        
        Returns more detailed status info than the standard response.
        
        Args:
            sensor_id: UUID of the sensor
            
        Returns:
            Status dict or None if not found
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
    # POLLING JOB MANAGEMENT
    # =========================================================================
    
    def _start_polling_job(self, sensor_id: str, callback):
        """
        Start a polling job for a sensor.
        
        Creates an APScheduler job that runs the callback every
        polling_interval seconds.
        
        Args:
            sensor_id: UUID of the sensor
            callback: Async function to call (receives sensor_id)
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
        """
        Stop the polling job for a sensor.
        
        Args:
            sensor_id: UUID of the sensor
        """
        job_id = f"poll_{sensor_id}"
        
        try:
            self.scheduler.remove_job(job_id)
        except Exception:
            pass  # Job might not exist
    
    async def _poll_purple_air_sensor(self, sensor_id: str):
        """
        Polling callback for Purple Air sensors.
        
        Called by the scheduler every polling_interval seconds.
        Fetches data and updates sensor status.
        
        Args:
            sensor_id: UUID of the sensor to poll
        """
        sensor = self._sensors.get(sensor_id)
        if not sensor:
            return
        
        ip_address = sensor["ip_address"]
        sensor_name = sensor["name"]
        
        # Fetch and push
        result = await self.purple_air_service.fetch_and_push(
            ip_address, 
            sensor_name
        )
        
        # Update status
        if result["status"] == "success":
            sensor["status"] = SensorStatus.ACTIVE
            sensor["last_active"] = datetime.now(timezone.utc)
            sensor["last_error"] = None
        else:
            sensor["status"] = SensorStatus.ERROR
            sensor["last_error"] = result.get("error_message", "Unknown error")
    
    async def _poll_tempest_sensor(self, sensor_id: str):
        """
        Polling callback for Tempest weather stations.
        
        Args:
            sensor_id: UUID of the sensor to poll
        """
        sensor = self._sensors.get(sensor_id)
        if not sensor:
            return
        
        ip_address = sensor["ip_address"]
        device_id = sensor["device_id"]
        sensor_name = sensor["name"]
        
        # Fetch and push
        result = await self.tempest_service.fetch_and_push(
            ip_address,
            device_id,
            sensor_name
        )
        
        # Update status
        if result["status"] == "success":
            sensor["status"] = SensorStatus.ACTIVE
            sensor["last_active"] = datetime.now(timezone.utc)
            sensor["last_error"] = None
        else:
            sensor["status"] = SensorStatus.ERROR
            sensor["last_error"] = result.get("error_message", "Unknown error")
    
    # =========================================================================
    # MANUAL FETCH (for testing)
    # =========================================================================
    
    async def trigger_fetch_now(self, sensor_id: str) -> dict:
        """
        Manually trigger a fetch for a sensor.
        
        Useful for testing without waiting for the scheduler.
        Returns the full result including fetched data.
        
        Args:
            sensor_id: UUID of the sensor
            
        Returns:
            Result dict with status, data, or error
            
        Example:
            result = await manager.trigger_fetch_now(sensor_id)
            if result["status"] == "success":
                print(result["reading"])
            else:
                print(result["error_message"])
        """
        sensor = self._sensors.get(sensor_id)
        if not sensor:
            return {
                "status": "error", 
                "error_message": "Sensor not found"
            }
        
        if sensor["sensor_type"] == SensorType.PURPLE_AIR:
            result = await self.purple_air_service.fetch_and_push(
                sensor["ip_address"],
                sensor["name"]
            )
        elif sensor["sensor_type"] == SensorType.TEMPEST:
            result = await self.tempest_service.fetch_and_push(
                sensor["ip_address"],
                sensor["device_id"],
                sensor["name"]
            )
        else:
            return {
                "status": "error",
                "error_message": f"Unsupported sensor type: {sensor['sensor_type']}"
            }
        
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
    # LIFECYCLE
    # =========================================================================
    
    async def shutdown(self):
        """
        Cleanup when shutting down the application.
        
        Call this in the application lifespan shutdown handler.
        Stops all polling jobs and closes HTTP clients.
        """
        self.scheduler.shutdown(wait=False)
        await self.purple_air_service.close()
        await self.tempest_service.close()

"""======================
Central manager for all sensor types.

This is the core service that orchestrates:
- Sensor registration (CRUD operations)
- Status tracking
- Polling schedules (automatic data collection)
- Coordination between sensor services

ARCHITECTURE:
    The SensorManager is instantiated once at application startup.
    It maintains:
    - In-memory sensor registry (dict of sensor configs)
    - APScheduler instance for polling jobs
    - References to individual sensor services

POLLING WORKFLOW:
    1. User adds a sensor via API
    2. User turns on the sensor
    3. SensorManager creates a scheduled job
    4. Every interval (default 60s), the job:
       - Calls the appropriate sensor service
       - Updates sensor status based on result
    5. User can turn off to stop polling

Author: Sensor Data Collector Team
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
    Central manager for all sensors in the system.
    
    This class provides a unified interface for managing sensors
    of all types. It handles:
    
    - CRUD operations (Add, Get, Delete sensors)
    - Sensor control (Turn on/off data collection)
    - Status tracking (Last active, errors)
    - Scheduling (Automatic polling at configured interval)
    
    Usage:
        # Initialize with services
        manager = SensorManager(
            purple_air_service=purple_air_service,
            tempest_service=tempest_service,
            polling_interval=60
        )
        
        # Add a sensor
        sensor = manager.add_purple_air_sensor(request)
        
        # Start polling
        await manager.turn_on_sensor(sensor.id)
        
        # Manual fetch
        result = await manager.trigger_fetch_now(sensor.id)
        
        # Stop polling
        manager.turn_off_sensor(sensor.id)
        
        # Remove sensor
        manager.delete_sensor(sensor.id)
    
    Attributes:
        purple_air_service: Service for Purple Air sensors
        tempest_service: Service for Tempest weather stations
        polling_interval: Seconds between automatic fetches
        scheduler: APScheduler instance for polling jobs
    """
    
    def __init__(
        self,
        purple_air_service: PurpleAirService,
        tempest_service: TempestService,
        polling_interval: int = 60
    ):
        """
        Initialize the sensor manager.
        
        Args:
            purple_air_service: Initialized PurpleAirService instance
            tempest_service: Initialized TempestService instance
            polling_interval: How often to poll sensors (seconds)
        """
        self.purple_air_service = purple_air_service
        self.tempest_service = tempest_service
        self.polling_interval = polling_interval
        
        # In-memory sensor storage
        # Key: sensor_id (str)
        # Value: sensor data dict
        self._sensors: dict[str, dict] = {}
        
        # APScheduler for polling jobs
        self.scheduler = AsyncIOScheduler()
        self.scheduler.start()
    
    # =========================================================================
    # SENSOR CRUD OPERATIONS
    # =========================================================================
    
    def add_purple_air_sensor(
        self, 
        request: AddPurpleAirSensorRequest
    ) -> SensorResponse:
        """
        Register a new Purple Air sensor.
        
        Creates a sensor record with the provided configuration.
        The sensor starts in INACTIVE state - call turn_on_sensor()
        to start data collection.
        
        Args:
            request: Contains ip_address, name, location
            
        Returns:
            Created sensor response
            
        Example:
            request = AddPurpleAirSensorRequest(
                ip_address="192.168.1.100",
                name="Lab Sensor",
                location="Science Building"
            )
            sensor = manager.add_purple_air_sensor(request)
            print(sensor.id)  # UUID
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
            "status": SensorStatus.INACTIVE,
            "is_active": False,
            "last_active": None,
            "last_error": None,
            "created_at": now,
        }
        
        self._sensors[sensor_id] = sensor_data
        
        return SensorResponse(**sensor_data)
    
    def add_tempest_sensor(
        self, 
        request: AddTempestSensorRequest
    ) -> SensorResponse:
        """
        Register a new Tempest weather station.
        
        Args:
            request: Contains ip_address, name, location, device_id
            
        Returns:
            Created sensor response
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
            "status": SensorStatus.INACTIVE,
            "is_active": False,
            "last_active": None,
            "last_error": None,
            "created_at": now,
        }
        
        self._sensors[sensor_id] = sensor_data
        
        return SensorResponse(**sensor_data)
    
    def get_sensor(self, sensor_id: str) -> Optional[SensorResponse]:
        """
        Get a sensor by ID.
        
        Args:
            sensor_id: UUID of the sensor
            
        Returns:
            Sensor data or None if not found
        """
        sensor_data = self._sensors.get(sensor_id)
        if sensor_data:
            return SensorResponse(**sensor_data)
        return None
    
    def get_all_sensors(
        self, 
        sensor_type: Optional[SensorType] = None
    ) -> list[SensorResponse]:
        """
        Get all sensors, optionally filtered by type.
        
        Args:
            sensor_type: Filter by type (optional)
            
        Returns:
            List of sensor responses
            
        Example:
            # Get all sensors
            all_sensors = manager.get_all_sensors()
            
            # Get only Purple Air sensors
            pa_sensors = manager.get_all_sensors(SensorType.PURPLE_AIR)
        """
        sensors = list(self._sensors.values())
        
        if sensor_type:
            sensors = [s for s in sensors if s["sensor_type"] == sensor_type]
        
        return [SensorResponse(**s) for s in sensors]
    
    def delete_sensor(self, sensor_id: str) -> bool:
        """
        Delete a sensor.
        
        Stops any active polling and removes the sensor from registry.
        
        Args:
            sensor_id: UUID of the sensor
            
        Returns:
            True if deleted, False if not found
        """
        if sensor_id not in self._sensors:
            return False
        
        # Stop polling if active
        self._stop_polling_job(sensor_id)
        
        # Remove from storage
        del self._sensors[sensor_id]
        
        return True
    
    # =========================================================================
    # SENSOR CONTROL (Turn On/Off)
    # =========================================================================
    
    async def turn_on_sensor(self, sensor_id: str) -> Optional[SensorResponse]:
        """
        Turn on data collection for a sensor.
        
        Creates a scheduled job that runs every polling_interval seconds.
        The job fetches data from the sensor and pushes it to the endpoint.
        
        Args:
            sensor_id: UUID of the sensor
            
        Returns:
            Updated sensor or None if not found
            
        Side Effects:
            - Creates APScheduler job
            - Updates sensor status to ACTIVE
            - Sets is_active to True
        """
        if sensor_id not in self._sensors:
            return None
        
        sensor = self._sensors[sensor_id]
        
        # Already active? Return as-is
        if sensor["is_active"]:
            return SensorResponse(**sensor)
        
        # Start polling based on sensor type
        if sensor["sensor_type"] == SensorType.PURPLE_AIR:
            self._start_polling_job(
                sensor_id=sensor_id,
                callback=self._poll_purple_air_sensor
            )
        elif sensor["sensor_type"] == SensorType.TEMPEST:
            self._start_polling_job(
                sensor_id=sensor_id,
                callback=self._poll_tempest_sensor
            )
        
        # Update status
        sensor["is_active"] = True
        sensor["status"] = SensorStatus.ACTIVE
        
        return SensorResponse(**sensor)
    
    def turn_off_sensor(self, sensor_id: str) -> Optional[SensorResponse]:
        """
        Turn off data collection for a sensor.
        
        Stops the scheduled polling job. The sensor remains registered
        and can be turned on again later.
        
        Args:
            sensor_id: UUID of the sensor
            
        Returns:
            Updated sensor or None if not found
        """
        if sensor_id not in self._sensors:
            return None
        
        sensor = self._sensors[sensor_id]
        
        # Stop the polling job
        self._stop_polling_job(sensor_id)
        
        # Update status
        sensor["is_active"] = False
        sensor["status"] = SensorStatus.INACTIVE
        
        return SensorResponse(**sensor)
    
    def get_sensor_status(self, sensor_id: str) -> Optional[dict]:
        """
        Get current status details for a sensor.
        
        Returns more detailed status info than the standard response.
        
        Args:
            sensor_id: UUID of the sensor
            
        Returns:
            Status dict or None if not found
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
    # POLLING JOB MANAGEMENT
    # =========================================================================
    
    def _start_polling_job(self, sensor_id: str, callback):
        """
        Start a polling job for a sensor.
        
        Creates an APScheduler job that runs the callback every
        polling_interval seconds.
        
        Args:
            sensor_id: UUID of the sensor
            callback: Async function to call (receives sensor_id)
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
        """
        Stop the polling job for a sensor.
        
        Args:
            sensor_id: UUID of the sensor
        """
        job_id = f"poll_{sensor_id}"
        
        try:
            self.scheduler.remove_job(job_id)
        except Exception:
            pass  # Job might not exist
    
    async def _poll_purple_air_sensor(self, sensor_id: str):
        """
        Polling callback for Purple Air sensors.
        
        Called by the scheduler every polling_interval seconds.
        Fetches data and updates sensor status.
        
        Args:
            sensor_id: UUID of the sensor to poll
        """
        sensor = self._sensors.get(sensor_id)
        if not sensor:
            return
        
        ip_address = sensor["ip_address"]
        sensor_name = sensor["name"]
        
        # Fetch and push
        result = await self.purple_air_service.fetch_and_push(
            ip_address, 
            sensor_name
        )
        
        # Update status
        if result["status"] == "success":
            sensor["status"] = SensorStatus.ACTIVE
            sensor["last_active"] = datetime.now(timezone.utc)
            sensor["last_error"] = None
        else:
            sensor["status"] = SensorStatus.ERROR
            sensor["last_error"] = result.get("error_message", "Unknown error")
    
    async def _poll_tempest_sensor(self, sensor_id: str):
        """
        Polling callback for Tempest weather stations.
        
        Args:
            sensor_id: UUID of the sensor to poll
        """
        sensor = self._sensors.get(sensor_id)
        if not sensor:
            return
        
        ip_address = sensor["ip_address"]
        device_id = sensor["device_id"]
        sensor_name = sensor["name"]
        
        # Fetch and push
        result = await self.tempest_service.fetch_and_push(
            ip_address,
            device_id,
            sensor_name
        )
        
        # Update status
        if result["status"] == "success":
            sensor["status"] = SensorStatus.ACTIVE
            sensor["last_active"] = datetime.now(timezone.utc)
            sensor["last_error"] = None
        else:
            sensor["status"] = SensorStatus.ERROR
            sensor["last_error"] = result.get("error_message", "Unknown error")
    
    # =========================================================================
    # MANUAL FETCH (for testing)
    # =========================================================================
    
    async def trigger_fetch_now(self, sensor_id: str) -> dict:
        """
        Manually trigger a fetch for a sensor.
        
        Useful for testing without waiting for the scheduler.
        Returns the full result including fetched data.
        
        Args:
            sensor_id: UUID of the sensor
            
        Returns:
            Result dict with status, data, or error
            
        Example:
            result = await manager.trigger_fetch_now(sensor_id)
            if result["status"] == "success":
                print(result["reading"])
            else:
                print(result["error_message"])
        """
        sensor = self._sensors.get(sensor_id)
        if not sensor:
            return {
                "status": "error", 
                "error_message": "Sensor not found"
            }
        
        if sensor["sensor_type"] == SensorType.PURPLE_AIR:
            result = await self.purple_air_service.fetch_and_push(
                sensor["ip_address"],
                sensor["name"]
            )
        elif sensor["sensor_type"] == SensorType.TEMPEST:
            result = await self.tempest_service.fetch_and_push(
                sensor["ip_address"],
                sensor["device_id"],
                sensor["name"]
            )
        else:
            return {
                "status": "error",
                "error_message": f"Unsupported sensor type: {sensor['sensor_type']}"
            }
        
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
    # LIFECYCLE
    # =========================================================================
    
    async def shutdown(self):
        """
        Cleanup when shutting down the application.
        
        Call this in the application lifespan shutdown handler.
        Stops all polling jobs and closes HTTP clients.
        """
        self.scheduler.shutdown(wait=False)
        await self.purple_air_service.close()
        await self.tempest_service.close()
