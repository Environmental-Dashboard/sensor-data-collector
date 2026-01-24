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
5. Power saving mode: cycles relay ON/OFF for battery-powered sensors

NOW WITH PERSISTENCE:
--------------------
Sensors are saved to a JSON file (sensors_db.json) so they survive restarts!
- Add a sensor = saved to file
- Delete a sensor = removed from file
- Restart server = sensors are loaded back automatically

POWER SAVING MODE:
-----------------
For Purple Air sensors with linked Voltage Meters:
- 30 seconds before poll: Turn relay ON (status: WAKING)
- Sensor boots and connects to WiFi (~25s)
- At poll time: Fetch data (status: ACTIVE briefly)
- After fetch: Turn relay OFF (status: SLEEPING)

Author: Frank Kusi Appiah
"""

import asyncio
import json
import uuid
import os
import logging
import sys
from datetime import datetime, timezone, timedelta
from typing import Optional
from pathlib import Path
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.date import DateTrigger

# Configure logging for sensor manager
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(message)s',
    datefmt='%H:%M:%S',
    handlers=[logging.StreamHandler(sys.stderr)]
)
logger = logging.getLogger(__name__)

from app.models import (
    SensorType,
    SensorStatus,
    SensorResponse,
    AddPurpleAirSensorRequest,
    AddTempestSensorRequest,
    AddVoltageMeterRequest,
    PowerMode,
)
from app.services.purple_air_service import PurpleAirService
from app.services.tempest_service import TempestService
from app.services.voltage_meter_service import VoltageMeterService
from app.services.email_service import EmailService


class SensorManager:
    """
    The central manager for all sensors.
    
    Sensors are now persisted to a JSON file so they survive server restarts!
    """
    
    # Where to store the sensors database
    DB_FILE = Path(__file__).parent.parent.parent / "sensors_db.json"
    
    # Power saving mode timing constants
    PRE_WAKE_TIME = 30      # seconds before poll to turn ON relay
    WIFI_GRACE_PERIOD = 10  # extra seconds to wait if sensor not ready
    WIFI_RETRY_INTERVAL = 1 # seconds between connection attempts
    POWER_OFF_DELAY = 1     # seconds to wait before turning relay off
    
    def __init__(
        self,
        purple_air_service: PurpleAirService,
        tempest_service: TempestService,
        voltage_meter_service: VoltageMeterService,
        polling_interval: int = 60
    ):
        """
        Set up the manager.
        
        Args:
            purple_air_service: The service that handles Purple Air sensors
            tempest_service: The service that handles Tempest sensors
            voltage_meter_service: The service that handles Voltage Meter sensors
            polling_interval: How often to fetch data (seconds). Default is 60.
        """
        self.purple_air_service = purple_air_service
        self.tempest_service = tempest_service
        self.voltage_meter_service = voltage_meter_service
        self.polling_interval = polling_interval
        
        # Email service for sending alerts
        self.email_service = EmailService()
        
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
            logger.info(f"No existing database found at {self.DB_FILE}")
            return
        
        try:
            with open(self.DB_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Convert the data back to proper types
            for sensor_id, sensor in data.items():
                try:
                    # Convert string types back to enums
                    sensor["sensor_type"] = SensorType(sensor["sensor_type"])
                    sensor["status"] = SensorStatus(sensor["status"])
                    
                    # Convert datetime strings back to datetime objects
                    if sensor.get("last_active"):
                        sensor["last_active"] = datetime.fromisoformat(sensor["last_active"])
                    if sensor.get("created_at"):
                        sensor["created_at"] = datetime.fromisoformat(sensor["created_at"])
                    
                    self._sensors[sensor_id] = sensor
                except (ValueError, KeyError, TypeError) as e:
                    logger.error(f"Error loading sensor {sensor_id}: {e}, skipping")
                    continue
            
            logger.info(f"Loaded {len(self._sensors)} sensors from database")
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing sensors database JSON: {e}")
            # Backup corrupted file
            backup_path = self.DB_FILE.with_suffix('.json.backup')
            try:
                import shutil
                shutil.copy2(self.DB_FILE, backup_path)
                logger.warning(f"Corrupted database backed up to {backup_path}")
            except Exception as backup_err:
                logger.error(f"Failed to backup corrupted database: {backup_err}")
        except Exception as e:
            logger.error(f"Error loading sensors database: {e}", exc_info=True)
    
    
    def _save_to_file(self):
        """Save sensors to the JSON file (atomic write)."""
        try:
            # Convert to JSON-serializable format
            data = {}
            for sensor_id, sensor in self._sensors.items():
                try:
                    sensor_copy = sensor.copy()
                    
                    # Convert enums to strings
                    if isinstance(sensor_copy.get("sensor_type"), SensorType):
                        sensor_copy["sensor_type"] = sensor_copy["sensor_type"].value
                    if isinstance(sensor_copy.get("status"), SensorStatus):
                        sensor_copy["status"] = sensor_copy["status"].value
                    
                    # Convert datetimes to ISO strings
                    if sensor_copy.get("last_active"):
                        if isinstance(sensor_copy["last_active"], datetime):
                            sensor_copy["last_active"] = sensor_copy["last_active"].isoformat()
                    if sensor_copy.get("created_at"):
                        if isinstance(sensor_copy["created_at"], datetime):
                            sensor_copy["created_at"] = sensor_copy["created_at"].isoformat()
                    
                    data[sensor_id] = sensor_copy
                except Exception as e:
                    logger.error(f"Error serializing sensor {sensor_id}: {e}")
                    continue
            
            # Atomic write: write to temp file first, then rename
            temp_file = self.DB_FILE.with_suffix('.json.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            # Atomic rename (works on Windows too)
            temp_file.replace(self.DB_FILE)
            logger.debug(f"Saved {len(data)} sensors to database")
            
        except PermissionError as e:
            logger.error(f"Permission denied saving sensors database: {e}")
        except OSError as e:
            logger.error(f"OS error saving sensors database: {e}")
        except Exception as e:
            logger.error(f"Error saving sensors database: {e}", exc_info=True)
    
    
    def _restart_active_sensors(self):
        """Restart polling for sensors that were active before shutdown."""
        for sensor_id, sensor in self._sensors.items():
            if sensor.get("is_active"):
                logger.info(f"Restarting polling for sensor: {sensor['name']}")
                try:
                    if sensor["sensor_type"] == SensorType.PURPLE_AIR:
                        self._start_polling_job(sensor_id, self._poll_purple_air_sensor)
                    elif sensor["sensor_type"] == SensorType.TEMPEST:
                        self._start_polling_job(sensor_id, self._poll_tempest_sensor)
                    elif sensor["sensor_type"] == SensorType.VOLTAGE_METER:
                        self._start_polling_job(sensor_id, self._poll_voltage_meter)
                except Exception as e:
                    logger.error(f"Failed to restart polling for sensor {sensor_id}: {e}")
                    sensor["is_active"] = False
    
    
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
        
        # Send new sensor notification email
        self.email_service.send_new_sensor_notification(
            sensor_id=sensor_id,
            sensor_name=request.name,
            sensor_type="purple_air",
            location=request.location,
            ip_address=request.ip_address,
            upload_token=request.upload_token
        )
        
        return SensorResponse(**{k: v for k, v in sensor_data.items() if k != "upload_token"})
    
    
    def add_voltage_meter_sensor(self, request: AddVoltageMeterRequest) -> SensorResponse:
        """
        Register a new Voltage Meter (ESP32 Battery Cutoff Monitor).
        """
        sensor_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        
        # Auto-generate name if linked to a sensor
        name = request.name
        linked_sensor_name = None
        if request.linked_sensor_id:
            linked_sensor = self._sensors.get(request.linked_sensor_id)
            if linked_sensor:
                linked_sensor_name = linked_sensor.get("name")
                if not name:
                    name = f"{linked_sensor_name} Voltmeter"
        
        if not name:
            name = f"Voltage Meter {sensor_id[:8]}"
        
        sensor_data = {
            "id": sensor_id,
            "sensor_type": SensorType.VOLTAGE_METER,
            "name": name,
            "location": request.location,
            "ip_address": request.ip_address,
            "device_id": None,
            "upload_token": request.upload_token,
            "status": SensorStatus.INACTIVE,
            "is_active": False,
            "last_active": None,
            "last_error": None,
            "created_at": now,
            "linked_sensor_id": request.linked_sensor_id,
            "linked_sensor_name": linked_sensor_name,
            "battery_volts": None,
        }
        
        self._sensors[sensor_id] = sensor_data
        self._save_to_file()
        
        # Send new sensor notification email
        self.email_service.send_new_sensor_notification(
            sensor_id=sensor_id,
            sensor_name=name,
            sensor_type="voltage_meter",
            location=request.location,
            ip_address=request.ip_address,
            upload_token=request.upload_token
        )
        
        return SensorResponse(**{k: v for k, v in sensor_data.items() if k != "upload_token"})
    
    
    def add_tempest_sensor(self, request: AddTempestSensorRequest) -> SensorResponse:
        """
        Register a new Tempest weather station.
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
        self._save_to_file()  # Persist to disk
        
        # Send new sensor notification email
        self.email_service.send_new_sensor_notification(
            sensor_id=sensor_id,
            sensor_name=request.name,
            sensor_type="tempest",
            location=request.location,
            ip_address=request.ip_address,
            upload_token=request.upload_token
        )
        
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
    
    
    def update_sensor_field(self, sensor_id: str, field: str, value) -> bool:
        """Update a single field on a sensor."""
        if sensor_id not in self._sensors:
            return False
        self._sensors[sensor_id][field] = value
        self._save_to_file()
        return True
    
    
    def get_all_sensors(self, sensor_type: Optional[SensorType] = None) -> list[SensorResponse]:
        """Get all sensors, optionally filtered by type."""
        sensors = list(self._sensors.values())
        
        if sensor_type:
            sensors = [s for s in sensors if s["sensor_type"] == sensor_type]
        
        return [SensorResponse(**{k: v for k, v in s.items() if k != "upload_token"}) for s in sensors]
    
    
    def set_polling_frequency(self, sensor_id: str, minutes: int) -> Optional[SensorResponse]:
        """
        Update polling frequency for a sensor (in minutes).

        For power saving mode we want coarse steps: 5min, 10min, 15min, ...
        So we clamp to at least 5 and round to the nearest multiple of 5.
        """
        sensor = self._sensors.get(sensor_id)
        if not sensor:
            return None

        # Clamp and quantize to 5-minute steps
        if minutes < 5:
            minutes = 5
        step = 5
        minutes = int(round(minutes / step) * step)

        interval_seconds = minutes * 60
        sensor["polling_frequency"] = interval_seconds

        # Restart polling job with new interval if active
        if sensor.get("is_active"):
            self._stop_polling_job(sensor_id)
            if sensor["sensor_type"] == SensorType.PURPLE_AIR:
                self._start_polling_job(sensor_id, self._poll_purple_air_sensor, frequency=interval_seconds)
            elif sensor["sensor_type"] == SensorType.TEMPEST:
                self._start_polling_job(sensor_id, self._poll_tempest_sensor, frequency=interval_seconds)
            elif sensor["sensor_type"] == SensorType.VOLTAGE_METER:
                self._start_polling_job(sensor_id, self._poll_voltage_meter, frequency=interval_seconds)

        self._save_to_file()

        # Return updated sensor
        return SensorResponse(**{k: v for k, v in sensor.items() if k != "upload_token"})


    def get_last_sent_data(self, sensor_id: str) -> Optional[dict]:
        """
        Get the last data we generated/sent for a sensor.

        This is meant for UI diagnostics like "Last Sent Data".
        Returns None if sensor doesn't exist.
        """
        sensor = self._sensors.get(sensor_id)
        if not sensor:
            return None

        return {
            "sensor_id": sensor_id,
            "sensor_name": sensor.get("name"),
            "sensor_type": str(sensor.get("sensor_type")),
            "last_upload_attempt": sensor.get("last_upload_attempt"),
            "last_active": sensor.get("last_active").isoformat() if sensor.get("last_active") else None,
            "last_error": sensor.get("last_error"),
            "status": str(sensor.get("status")),
            "status_reason": sensor.get("status_reason"),
            "last_csv_sample": sensor.get("last_csv_sample"),
            "last_error_details": sensor.get("last_error_details"),
        }
    
    
    def delete_sensor(self, sensor_id: str) -> bool:
        """Delete a sensor permanently."""
        if sensor_id not in self._sensors:
            return False
        
        self._stop_polling_job(sensor_id)
        del self._sensors[sensor_id]
        self._save_to_file()  # Persist to disk
        
        return True
    
    
    def update_sensor(self, sensor_id: str, request) -> Optional[SensorResponse]:
        """
        Update a sensor's fields from an UpdateSensorRequest.
        
        Handles:
        - Basic fields: name, location, ip_address, device_id, upload_token, power_mode
        - linked_sensor_id: For voltage meters, links to a Purple Air sensor
        """
        if sensor_id not in self._sensors:
            return None
        
        sensor = self._sensors[sensor_id]
        updates = request.model_dump(exclude_unset=True)
        
        # Handle linked_sensor_id specially - also update linked_sensor_name
        if "linked_sensor_id" in updates:
            linked_id = updates["linked_sensor_id"]
            if linked_id:
                linked_sensor = self._sensors.get(linked_id)
                if linked_sensor:
                    sensor["linked_sensor_id"] = linked_id
                    sensor["linked_sensor_name"] = linked_sensor.get("name")
                    logger.info(f"Linked sensor {sensor_id} to {linked_id} ({linked_sensor.get('name')})")
            else:
                # Clear the link
                sensor["linked_sensor_id"] = None
                sensor["linked_sensor_name"] = None
                logger.info(f"Unlinked sensor {sensor_id}")
            del updates["linked_sensor_id"]
        
        # Update other fields (allow adding new fields too)
        allowed_fields = {"name", "location", "ip_address", "device_id", "upload_token", "power_mode"}
        for key, value in updates.items():
            if value is not None and key in allowed_fields:
                sensor[key] = value
        
        self._save_to_file()
        
        return SensorResponse(**{k: v for k, v in sensor.items() if k != "upload_token"})
    
    
    def _update_sensor_status(
        self, 
        sensor: dict, 
        new_status: SensorStatus, 
        error_message: Optional[str] = None,
        error_type: Optional[str] = None
    ):
        """
        Update sensor status and send email alert if needed.
        
        This handles:
        - Status transitions (error -> active, active -> error, etc.)
        - Email alerts on errors
        - Recovery notifications when sensor comes back online
        """
        old_status_raw = sensor.get("status")
        sensor_id = sensor.get("id")
        sensor_name = sensor.get("name", "Unknown")
        sensor_type = str(sensor.get("sensor_type", "unknown"))
        location = sensor.get("location")
        
        # Normalize old_status to string for comparison (handles both enum and string)
        if isinstance(old_status_raw, SensorStatus):
            old_status = old_status_raw.value
        else:
            old_status = str(old_status_raw) if old_status_raw else ""
        
        new_status_str = new_status.value
        
        # Skip if status hasn't changed
        if old_status == new_status_str:
            # Just update error message if provided
            if error_message:
                sensor["last_error"] = error_message
            return
        
        # Update status
        sensor["status"] = new_status
        sensor["status_reason"] = error_type
        sensor["last_error"] = error_message
        
        logger.debug(f"[{sensor_name}] Status transition: {old_status} -> {new_status_str}")
        
        # Define status categories (as strings for comparison)
        # NOTE: "sleeping" and "waking" are NORMAL states in power saving mode, not errors
        error_statuses = ["error", "inactive", "offline"]
        ok_statuses = ["active", "sleeping", "waking"]
        
        # Check if we need to send an alert
        is_error_status = new_status_str in error_statuses
        was_ok_before = old_status in ok_statuses
        
        # IMPORTANT: Don't send alerts for expected state transitions in power saving mode
        # sleeping -> inactive is common when sensor is powered off (expected)
        is_expected_transition = (
            (old_status == "sleeping" and new_status_str == "inactive") or
            (old_status == "inactive" and new_status_str == "sleeping") or
            (old_status == "waking" and new_status_str == "inactive")
        )
        
        # Send error alert if transitioning to error/inactive state (but not expected transitions)
        if is_error_status and was_ok_before and error_message and not is_expected_transition:
            logger.warning(f"[{sensor_name}] Status changed: {old_status} -> {new_status_str}")
            self.email_service.send_sensor_error_alert(
                sensor_id=sensor_id,
                sensor_name=sensor_name,
                sensor_type=sensor_type,
                error_message=error_message,
                status=new_status_str,
                location=location
            )
        
        # Send recovery alert if coming back online (but not for normal power saving transitions)
        was_error_before = old_status in error_statuses
        is_ok_now = new_status_str in ["active", "sleeping"]
        
        # Don't send recovery for normal transitions back to sleeping from inactive
        is_normal_recovery = (old_status == "inactive" and new_status_str == "sleeping")
        
        if was_error_before and is_ok_now and not is_normal_recovery:
            logger.info(f"[{sensor_name}] Recovered: {old_status} -> {new_status_str}")
            self.email_service.send_sensor_recovery_alert(
                sensor_id=sensor_id,
                sensor_name=sensor_name,
                sensor_type=sensor_type,
                location=location
            )
    
    
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
        sensor["status_reason"] = None
        
        # Start polling based on sensor type
        if sensor["sensor_type"] == SensorType.PURPLE_AIR:
            self._start_polling_job(sensor_id, self._poll_purple_air_sensor)
            # For power saving mode, set initial status to SLEEPING
            if sensor.get("power_mode") == PowerMode.POWER_SAVING.value:
                sensor["status"] = SensorStatus.SLEEPING
            else:
                sensor["status"] = SensorStatus.ACTIVE
        elif sensor["sensor_type"] == SensorType.TEMPEST:
            self._start_polling_job(sensor_id, self._poll_tempest_sensor)
            sensor["status"] = SensorStatus.ACTIVE
        elif sensor["sensor_type"] == SensorType.VOLTAGE_METER:
            self._start_polling_job(sensor_id, self._poll_voltage_meter)
            sensor["status"] = SensorStatus.ACTIVE
        
        sensor["is_active"] = True
        self._save_to_file()  # Persist to disk
        
        return SensorResponse(**{k: v for k, v in sensor.items() if k != "upload_token"})
    
    
    def turn_off_sensor(self, sensor_id: str) -> Optional[SensorResponse]:
        """Turn off a sensor - stop collecting data."""
        if sensor_id not in self._sensors:
            return None
        
        sensor = self._sensors[sensor_id]
        
        self._stop_polling_job(sensor_id)
        
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
    
    def _start_polling_job(self, sensor_id: str, callback, frequency: int = None):
        """Start a polling job for a sensor."""
        sensor = self._sensors.get(sensor_id)
        interval = frequency or sensor.get("polling_frequency") or self.polling_interval
        job_id = f"poll_{sensor_id}"
        
        print(f"[{sensor.get('name', sensor_id)}] Starting poll job (interval: {interval}s)")
        
        self.scheduler.add_job(
            callback,
            trigger=IntervalTrigger(seconds=interval),
            id=job_id,
            args=[sensor_id],
            replace_existing=True,
        )
        
        # For power saving mode, also schedule pre-wake job
        sensor_type = sensor.get("sensor_type")
        power_mode = sensor.get("power_mode")
        is_purple_air = sensor_type == SensorType.PURPLE_AIR or sensor_type == SensorType.PURPLE_AIR.value
        is_power_saving = power_mode == PowerMode.POWER_SAVING.value
        
        print(f"[{sensor.get('name', sensor_id)}] type={sensor_type}, power_mode={power_mode}, is_purple_air={is_purple_air}, is_power_saving={is_power_saving}")
        
        if is_purple_air and is_power_saving:
            print(f"[{sensor.get('name', sensor_id)}] >>> SCHEDULING PRE-WAKE JOB (30s before each poll)")
            self._schedule_pre_wake(sensor_id, interval)
        else:
            print(f"[{sensor.get('name', sensor_id)}] No pre-wake needed (not power_saving mode)")
    
    
    def _schedule_pre_wake(self, sensor_id: str, poll_interval: int):
        """Schedule a pre-wake job for power saving mode."""
        prewake_job_id = f"prewake_{sensor_id}"
        sensor = self._sensors.get(sensor_id)
        
        # Pre-wake runs at the same interval, but offset by PRE_WAKE_TIME
        # This ensures relay turns ON 30 seconds before each poll
        start_time = datetime.now(timezone.utc) + timedelta(seconds=poll_interval - self.PRE_WAKE_TIME)
        logger.info(f"[{sensor.get('name', sensor_id)}] Pre-wake scheduled: first at {start_time}, then every {poll_interval}s")
        
        try:
            self.scheduler.add_job(
                self._pre_wake_sensor,
                trigger=IntervalTrigger(seconds=poll_interval),
                id=prewake_job_id,
                args=[sensor_id],
                start_date=start_time,
                replace_existing=True,
            )
        except Exception as e:
            logger.error(f"Failed to schedule pre-wake job for {sensor_id}: {e}")
            raise
    
    
    def _stop_polling_job(self, sensor_id: str):
        """Stop the polling job for a sensor."""
        job_id = f"poll_{sensor_id}"
        prewake_job_id = f"prewake_{sensor_id}"
        
        try:
            self.scheduler.remove_job(job_id)
        except Exception:
            pass
        
        try:
            self.scheduler.remove_job(prewake_job_id)
        except Exception:
            pass
    
    
    async def _pre_wake_sensor(self, sensor_id: str):
        """
        Pre-wake a sensor (power saving mode).
        
        Called 30 seconds before the main poll to turn on the relay
        and give the sensor time to boot and connect to WiFi.
        """
        sensor = self._sensors.get(sensor_id)
        if not sensor:
            logger.warning(f"[PRE-WAKE] Sensor {sensor_id} not found!")
            return
        
        logger.info(f"[{sensor.get('name', sensor_id)}] >>> PRE-WAKE TRIGGERED - Turning relay ON")
        
        # Only pre-wake if in power saving mode
        if sensor.get("power_mode") != PowerMode.POWER_SAVING.value:
            logger.debug(f"[{sensor.get('name', sensor_id)}] Not in power saving mode, skipping pre-wake")
            return
        
        voltage_meter = self._find_voltage_meter_for_sensor(sensor_id)
        if not voltage_meter:
            logger.warning(f"[{sensor['name']}] Power saving mode but no linked Voltage Meter found")
            return
        
        vm_ip = voltage_meter.get("ip_address")
        if not vm_ip:
            logger.error(f"[{sensor['name']}] Voltage meter has no IP address")
            return
        
        logger.info(f"[{sensor['name']}] Pre-wake: Turning relay ON...")
        
        try:
            # Set status to WAKING
            sensor["status"] = SensorStatus.WAKING
            sensor["status_reason"] = None
            self._save_to_file()
            
            # Turn relay ON
            success = await self.voltage_meter_service.set_relay(vm_ip, on=True)
            if not success:
                logger.error(f"[{sensor['name']}] Failed to turn relay ON during pre-wake")
                sensor["status"] = SensorStatus.ERROR
                sensor["status_reason"] = "prewake_failed"
                self._save_to_file()
        except Exception as e:
            logger.error(f"[{sensor['name']}] Error during pre-wake: {e}", exc_info=True)
            sensor["status"] = SensorStatus.ERROR
            sensor["status_reason"] = "prewake_error"
            self._save_to_file()
    
    
    def _find_voltage_meter_for_sensor(self, purple_air_sensor_id: str) -> Optional[dict]:
        """
        Find the Voltage Meter that controls a Purple Air sensor.
        
        Looks for a voltage meter with linked_sensor_id matching the given sensor.
        """
        for sensor in self._sensors.values():
            if (sensor.get("sensor_type") == SensorType.VOLTAGE_METER and
                sensor.get("linked_sensor_id") == purple_air_sensor_id):
                return sensor
        return None
    
    
    async def _poll_purple_air_sensor(self, sensor_id: str):
        """
        Poll a Purple Air sensor.
        
        For normal mode: Just fetch data directly.
        For power saving mode: Sensor should already be awake from pre-wake.
        """
        sensor = self._sensors.get(sensor_id)
        if not sensor:
            logger.warning(f"[POLL] Sensor {sensor_id} not found, skipping poll")
            return
        
        try:
            power_mode = sensor.get("power_mode")
            voltage_meter = self._find_voltage_meter_for_sensor(sensor_id)
            
            # Power saving mode handling
            if power_mode == PowerMode.POWER_SAVING.value and voltage_meter:
                vm_ip = voltage_meter["ip_address"]
                
                # Sensor should be waking/already awake from pre-wake job
                logger.info(f"[{sensor['name']}] Power saving: Fetching data...")
                
                # Fetch data
                result = await self.purple_air_service.fetch_and_push(
                    ip_address=sensor["ip_address"],
                    sensor_name=sensor["name"],
                    upload_token=sensor["upload_token"]
                )
                
                # Turn relay OFF after fetching (go back to sleep)
                await asyncio.sleep(self.POWER_OFF_DELAY)
                logger.info(f"[{sensor['name']}] Power saving: Turning relay OFF...")
                await self.voltage_meter_service.set_relay(vm_ip, on=False)
                
                # Handle result
                if result["status"] == "success":
                    self._update_sensor_status(sensor, SensorStatus.SLEEPING)
                    sensor["last_active"] = datetime.now(timezone.utc)
                    if "upload_result" in result and "csv_sample" in result.get("upload_result", {}):
                        sensor["last_csv_sample"] = result["upload_result"]["csv_sample"]
                else:
                    # Smart error detection - pass power_mode so it knows load OFF might be expected
                    result = await self._enhance_error_with_voltage_meter_status(result, voltage_meter, power_mode)
                    error_type = result.get("error_type")
                    error_msg = result.get("error_message", "Unknown error")
                    
                    if error_type == "battery_low":
                        self._update_sensor_status(sensor, SensorStatus.OFFLINE, error_msg, error_type)
                    elif error_type == "sleeping":
                        # In power saving mode, load OFF with good voltage = sleeping (not an error)
                        self._update_sensor_status(sensor, SensorStatus.SLEEPING)
                    elif error_type in ["connection_error", "timeout"]:
                        # Not responding = INACTIVE (not error)
                        self._update_sensor_status(sensor, SensorStatus.INACTIVE, error_msg, error_type)
                    else:
                        # Real errors (cloud_error, data_error, etc.)
                        self._update_sensor_status(sensor, SensorStatus.ERROR, error_msg, error_type)
                    
                    if result.get("battery_voltage") is not None:
                        sensor["battery_volts"] = result["battery_voltage"]
            else:
                # Normal mode - just fetch directly
                result = await self.purple_air_service.fetch_and_push(
                    ip_address=sensor["ip_address"],
                    sensor_name=sensor["name"],
                    upload_token=sensor["upload_token"]
                )
                
                if result["status"] == "success":
                    self._update_sensor_status(sensor, SensorStatus.ACTIVE)
                    sensor["last_active"] = datetime.now(timezone.utc)
                    if "upload_result" in result and "csv_sample" in result.get("upload_result", {}):
                        sensor["last_csv_sample"] = result["upload_result"]["csv_sample"]
                else:
                    # Check if there's a linked voltage meter for error detection
                    if voltage_meter:
                        result = await self._enhance_error_with_voltage_meter_status(result, voltage_meter, power_mode)
                    
                    error_type = result.get("error_type")
                    error_msg = result.get("error_message", "Unknown error")
                    
                    if error_type == "battery_low":
                        self._update_sensor_status(sensor, SensorStatus.OFFLINE, error_msg, error_type)
                    elif error_type in ["connection_error", "timeout"]:
                        # Not responding = INACTIVE (not error)
                        self._update_sensor_status(sensor, SensorStatus.INACTIVE, error_msg, error_type)
                    else:
                        # Real errors (cloud_error, data_error, etc.)
                        self._update_sensor_status(sensor, SensorStatus.ERROR, error_msg, error_type)
        
        except Exception as e:
            logger.error(f"[{sensor.get('name', sensor_id)}] Error during poll: {e}", exc_info=True)
            self._update_sensor_status(sensor, SensorStatus.ERROR, f"Poll error: {str(e)}", "poll_error")
        finally:
            self._save_to_file()
    
    
    async def _enhance_error_with_voltage_meter_status(
        self, 
        result: dict, 
        voltage_meter: Optional[dict],
        power_mode: Optional[str] = None
    ) -> dict:
        """
        Smart error detection: Check voltage meter to determine cause.
        
        If the sensor can't be reached:
        - Load OFF + Power Saving Mode + Voltage > Cutoff: Sleeping (expected, not an error)
        - Load OFF + Voltage < Cutoff: Battery low (voltage dropped below cutoff)
        - Load ON: WiFi/network error (power is on but can't connect)
        """
        if not voltage_meter:
            return result
        
        try:
            vm_status = await self.voltage_meter_service.get_status(voltage_meter["ip_address"])
            if vm_status:
                voltage = vm_status.get("voltage_v", 0)
                load_on = vm_status.get("load_on", False)
                v_cutoff = vm_status.get("v_cutoff", 12.0)
                
                result["voltage_meter_id"] = voltage_meter["id"]
                result["voltage_meter_name"] = voltage_meter["name"]
                result["battery_voltage"] = voltage
                result["voltage_cutoff"] = v_cutoff
                
                if not load_on:
                    # Relay is OFF - check if it's expected (power saving) or battery low
                    if power_mode == PowerMode.POWER_SAVING.value and voltage >= v_cutoff:
                        # Power saving mode: load OFF with good voltage = sleeping (not an error)
                        result["error_type"] = "sleeping"
                        result["error_message"] = (
                            f"Sleeping (power saving mode) - Battery: {voltage:.1f}V "
                            f"(cutoff: {v_cutoff:.1f}V)"
                        )
                    elif voltage < v_cutoff:
                        # Voltage below cutoff = actual battery low
                        result["error_type"] = "battery_low"
                        result["error_message"] = (
                            f"Battery Low ({voltage:.1f}V) - Sensor powered off "
                            f"(cutoff: {v_cutoff:.1f}V)"
                        )
                    else:
                        # Load OFF but voltage OK and not power saving = unknown reason
                        result["error_type"] = "wifi_error"
                        result["error_message"] = (
                            f"Relay OFF but voltage OK ({voltage:.1f}V) - Check voltage meter settings"
                        )
                else:
                    # Relay is ON but sensor not responding - WiFi issue
                    result["error_type"] = "wifi_error"
                    result["error_message"] = (
                        f"WiFi/Network Error - Power is ON but sensor not responding. "
                        f"Battery: {voltage:.1f}V"
                    )
        except Exception as e:
            logger.error(f"Error checking voltage meter status: {e}", exc_info=True)
        
        return result
    
    
    async def _poll_tempest_sensor(self, sensor_id: str):
        """Poll a Tempest sensor (runs every 60 seconds)."""
        sensor = self._sensors.get(sensor_id)
        if not sensor:
            logger.warning(f"[POLL] Sensor {sensor_id} not found, skipping poll")
            return
        
        try:
            result = await self.tempest_service.fetch_and_push(
                ip_address=sensor["ip_address"],
                device_id=sensor["device_id"],
                sensor_name=sensor["name"],
                upload_token=sensor["upload_token"]
            )
            
            if result["status"] == "success":
                self._update_sensor_status(sensor, SensorStatus.ACTIVE)
                sensor["last_active"] = datetime.now(timezone.utc)
                # Update battery voltage from reading
                if result.get("reading") and result["reading"].get("battery_volts"):
                    sensor["battery_volts"] = result["reading"]["battery_volts"]
            else:
                error_type = result.get("error_type")
                error_msg = result.get("error_message", "Unknown error")
                
                if error_type in ["connection_error", "timeout"]:
                    # API not responding = INACTIVE
                    self._update_sensor_status(sensor, SensorStatus.INACTIVE, error_msg, error_type)
                else:
                    # Real errors (cloud_error, data_error, etc.)
                    self._update_sensor_status(sensor, SensorStatus.ERROR, error_msg, error_type)
        except Exception as e:
            logger.error(f"[{sensor.get('name', sensor_id)}] Error during poll: {e}", exc_info=True)
            self._update_sensor_status(sensor, SensorStatus.ERROR, f"Poll error: {str(e)}", "poll_error")
        finally:
            self._save_to_file()
    
    
    async def _poll_voltage_meter(self, sensor_id: str):
        """Poll a Voltage Meter (runs every 60 seconds)."""
        sensor = self._sensors.get(sensor_id)
        if not sensor:
            logger.warning(f"[POLL] Sensor {sensor_id} not found, skipping poll")
            return
        
        try:
            result = await self.voltage_meter_service.fetch_and_push(
                ip_address=sensor["ip_address"],
                sensor_name=sensor["name"],
                upload_token=sensor["upload_token"]
            )
            
            if result["status"] == "success":
                self._update_sensor_status(sensor, SensorStatus.ACTIVE)
                sensor["last_active"] = datetime.now(timezone.utc)
                # Update battery voltage and relay status from reading
                reading = result.get("reading", {})
                if reading.get("voltage_v") is not None:
                    sensor["battery_volts"] = reading["voltage_v"]
                if reading.get("auto_mode") is not None:
                    sensor["auto_mode"] = reading["auto_mode"]
                if reading.get("load_on") is not None:
                    sensor["load_on"] = reading["load_on"]
                if reading.get("v_cutoff") is not None:
                    sensor["v_cutoff"] = reading["v_cutoff"]
                if reading.get("v_reconnect") is not None:
                    sensor["v_reconnect"] = reading["v_reconnect"]
                # Store CSV sample
                if result.get("csv_sample"):
                    sensor["last_csv_sample"] = result["csv_sample"]
            else:
                error_type = result.get("error_type")
                error_msg = result.get("error_message", "Unknown error")
                
                if error_type in ["connection_error", "timeout"]:
                    # Not responding = INACTIVE
                    self._update_sensor_status(sensor, SensorStatus.INACTIVE, error_msg, error_type)
                else:
                    # Real errors (cloud_error, etc.)
                    self._update_sensor_status(sensor, SensorStatus.ERROR, error_msg, error_type)
        except Exception as e:
            logger.error(f"[{sensor.get('name', sensor_id)}] Error during poll: {e}", exc_info=True)
            self._update_sensor_status(sensor, SensorStatus.ERROR, f"Poll error: {str(e)}", "poll_error")
        finally:
            self._save_to_file()
    
    
    # =========================================================================
    # MANUAL FETCH
    # =========================================================================
    
    async def trigger_fetch_now(self, sensor_id: str) -> dict:
        """Manually trigger a fetch RIGHT NOW."""
        sensor = self._sensors.get(sensor_id)
        if not sensor:
            return {"status": "error", "error_message": "Sensor not found"}
        
        power_mode = sensor.get("power_mode")
        voltage_meter = self._find_voltage_meter_for_sensor(sensor_id) if sensor["sensor_type"] == SensorType.PURPLE_AIR else None
        
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
        elif sensor["sensor_type"] == SensorType.VOLTAGE_METER:
            result = await self.voltage_meter_service.fetch_and_push(
                ip_address=sensor["ip_address"],
                sensor_name=sensor["name"],
                upload_token=sensor["upload_token"]
            )
        else:
            return {"status": "error", "error_message": f"Unknown sensor type: {sensor['sensor_type']}"}
        
        if result["status"] == "success":
            sensor["status"] = SensorStatus.ACTIVE
            sensor["status_reason"] = None
            sensor["last_active"] = datetime.now(timezone.utc)
            sensor["last_error"] = None
            
            # Save CSV sample
            if result.get("csv_sample"):
                sensor["last_csv_sample"] = result["csv_sample"]
            
            # Update voltage meter specific fields
            if sensor["sensor_type"] == SensorType.VOLTAGE_METER:
                reading = result.get("reading", {})
                if reading.get("voltage_v") is not None:
                    sensor["battery_volts"] = reading["voltage_v"]
                if reading.get("auto_mode") is not None:
                    sensor["auto_mode"] = reading["auto_mode"]
                if reading.get("load_on") is not None:
                    sensor["load_on"] = reading["load_on"]
                if reading.get("v_cutoff") is not None:
                    sensor["v_cutoff"] = reading["v_cutoff"]
                if reading.get("v_reconnect") is not None:
                    sensor["v_reconnect"] = reading["v_reconnect"]
        else:
            # Apply smart error detection for Purple Air sensors with voltage meters
            if sensor["sensor_type"] == SensorType.PURPLE_AIR and voltage_meter:
                result = await self._enhance_error_with_voltage_meter_status(result, voltage_meter, power_mode)
            
            sensor["last_error"] = result.get("error_message", "Unknown error")
            sensor["status_reason"] = result.get("error_type")
            
            if result.get("error_type") == "battery_low":
                sensor["status"] = SensorStatus.OFFLINE
            elif result.get("error_type") == "sleeping":
                # In power saving mode, load OFF with good voltage = sleeping (not an error)
                sensor["status"] = SensorStatus.SLEEPING
                sensor["status_reason"] = None
                sensor["last_error"] = None
            elif result.get("error_type") == "cloud_error":
                sensor["status"] = SensorStatus.ERROR
            else:
                sensor["status"] = SensorStatus.ERROR
            
            if result.get("battery_voltage") is not None:
                sensor["battery_volts"] = result["battery_voltage"]
        
        self._save_to_file()
        
        return result
    
    
    # =========================================================================
    # POWER MODE
    # =========================================================================
    
    async def set_power_mode_async(self, sensor_id: str, power_mode: str) -> Optional[SensorResponse]:
        """Set the power mode for a Purple Air sensor (async version)."""
        sensor = self._sensors.get(sensor_id)
        if not sensor:
            return None
        
        if sensor["sensor_type"] != SensorType.PURPLE_AIR:
            return None
        
        old_mode = sensor.get("power_mode")
        sensor["power_mode"] = power_mode

        # Update status based on new mode
        if power_mode == PowerMode.POWER_SAVING.value:
            if sensor["is_active"]:
                sensor["status"] = SensorStatus.SLEEPING
        else:
            if sensor["is_active"]:
                sensor["status"] = SensorStatus.ACTIVE

            # When leaving power saving mode, put the linked Voltage Meter back into AUTO mode
            voltage_meter = self._find_voltage_meter_for_sensor(sensor_id)
            if voltage_meter:
                try:
                    vm_ip = voltage_meter.get("ip_address")
                    if vm_ip:
                        logger.info(f"[{sensor['name']}] Switching to normal mode - setting voltage meter to AUTO")
                        # Let the ESP32 handle cutoff/reconnect logic automatically
                        await self.voltage_meter_service.set_auto_mode(vm_ip, auto=True)
                        # Update cached state
                        await asyncio.sleep(0.5)
                        status = await self.voltage_meter_service.get_status(vm_ip)
                        if status:
                            voltage_meter["auto_mode"] = status.get("auto_mode")
                            voltage_meter["load_on"] = status.get("load_on")
                            self._save_to_file()
                except Exception as e:
                    logger.error(f"Failed to set voltage meter auto mode for sensor {sensor_id}: {e}")
        
        # Restart polling job to update pre-wake schedule
        if sensor["is_active"]:
            self._stop_polling_job(sensor_id)
            self._start_polling_job(sensor_id, self._poll_purple_air_sensor)
        
        self._save_to_file()
        
        return SensorResponse(**{k: v for k, v in sensor.items() if k != "upload_token"})
    
    def set_power_mode(self, sensor_id: str, power_mode: str) -> Optional[SensorResponse]:
        """
        Set the power mode for a Purple Air sensor (sync wrapper - DEPRECATED).
        
        NOTE: This method creates a new event loop which is not recommended.
        Use set_power_mode_async() instead, which is called directly by the router.
        """
        logger.warning("set_power_mode() sync wrapper called - use set_power_mode_async() instead")
        # Use asyncio to run the async version
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(self.set_power_mode_async(sensor_id, power_mode))
            finally:
                loop.close()
        except Exception as e:
            logger.error(f"Error in sync set_power_mode wrapper: {e}", exc_info=True)
            return None
    
    
    # =========================================================================
    # CLEANUP
    # =========================================================================
    
    async def shutdown(self):
        """Clean up when the server is shutting down."""
        try:
            # Save sensors one last time
            self._save_to_file()
        except Exception as e:
            logger.error(f"Error saving sensors during shutdown: {e}", exc_info=True)
        
        try:
            # Shutdown scheduler gracefully
            self.scheduler.shutdown(wait=False)
        except Exception as e:
            logger.error(f"Error shutting down scheduler: {e}", exc_info=True)
        
        # Close HTTP clients (ensure they're closed even if one fails)
        services_to_close = [
            ("purple_air", self.purple_air_service),
            ("tempest", self.tempest_service),
            ("voltage_meter", self.voltage_meter_service),
        ]
        
        for service_name, service in services_to_close:
            try:
                await service.close()
                logger.debug(f"Closed {service_name} service")
            except Exception as e:
                logger.error(f"Error closing {service_name} service: {e}", exc_info=True)