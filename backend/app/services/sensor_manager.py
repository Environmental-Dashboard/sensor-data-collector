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
from datetime import datetime, timezone, timedelta
from typing import Optional
from pathlib import Path
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.date import DateTrigger

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
        """Restart polling for sensors that were active before shutdown."""
        for sensor_id, sensor in self._sensors.items():
            if sensor.get("is_active"):
                print(f"Restarting polling for sensor: {sensor['name']}")
                if sensor["sensor_type"] == SensorType.PURPLE_AIR:
                    self._start_polling_job(sensor_id, self._poll_purple_air_sensor)
                elif sensor["sensor_type"] == SensorType.TEMPEST:
                    self._start_polling_job(sensor_id, self._poll_tempest_sensor)
                elif sensor["sensor_type"] == SensorType.VOLTAGE_METER:
                    self._start_polling_job(sensor_id, self._poll_voltage_meter)
    
    
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
        
        self.scheduler.add_job(
            callback,
            trigger=IntervalTrigger(seconds=interval),
            id=job_id,
            args=[sensor_id],
            replace_existing=True,
        )
        
        # For power saving mode, also schedule pre-wake job
        if sensor and sensor.get("sensor_type") == SensorType.PURPLE_AIR:
            if sensor.get("power_mode") == PowerMode.POWER_SAVING.value:
                self._schedule_pre_wake(sensor_id, interval)
    
    
    def _schedule_pre_wake(self, sensor_id: str, poll_interval: int):
        """Schedule a pre-wake job for power saving mode."""
        prewake_job_id = f"prewake_{sensor_id}"
        
        # Pre-wake runs at the same interval, but offset by PRE_WAKE_TIME
        # This ensures relay turns ON 30 seconds before each poll
        self.scheduler.add_job(
            self._pre_wake_sensor,
            trigger=IntervalTrigger(seconds=poll_interval),
            id=prewake_job_id,
            args=[sensor_id],
            start_date=datetime.now(timezone.utc) + timedelta(seconds=poll_interval - self.PRE_WAKE_TIME),
            replace_existing=True,
        )
    
    
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
            return
        
        # Only pre-wake if in power saving mode
        if sensor.get("power_mode") != PowerMode.POWER_SAVING.value:
            return
        
        voltage_meter = self._find_voltage_meter_for_sensor(sensor_id)
        if not voltage_meter:
            print(f"[{sensor['name']}] Power saving mode but no linked Voltage Meter found")
            return
        
        vm_ip = voltage_meter["ip_address"]
        print(f"[{sensor['name']}] Pre-wake: Turning relay ON...")
        
        # Set status to WAKING
        sensor["status"] = SensorStatus.WAKING
        sensor["status_reason"] = None
        self._save_to_file()
        
        # Turn relay ON
        success = await self.voltage_meter_service.set_relay(vm_ip, on=True)
        if not success:
            print(f"[{sensor['name']}] Failed to turn relay ON")
    
    
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
            return
        
        power_mode = sensor.get("power_mode")
        voltage_meter = self._find_voltage_meter_for_sensor(sensor_id)
        
        # Power saving mode handling
        if power_mode == PowerMode.POWER_SAVING.value and voltage_meter:
            vm_ip = voltage_meter["ip_address"]
            
            # Sensor should be waking/already awake from pre-wake job
            print(f"[{sensor['name']}] Power saving: Fetching data...")
            
            # Fetch data
            result = await self.purple_air_service.fetch_and_push(
                ip_address=sensor["ip_address"],
                sensor_name=sensor["name"],
                upload_token=sensor["upload_token"]
            )
            
            # Turn relay OFF after fetching (go back to sleep)
            await asyncio.sleep(self.POWER_OFF_DELAY)
            print(f"[{sensor['name']}] Power saving: Turning relay OFF...")
            await self.voltage_meter_service.set_relay(vm_ip, on=False)
            
            # Handle result
            if result["status"] == "success":
                sensor["status"] = SensorStatus.SLEEPING
                sensor["status_reason"] = None
                sensor["last_active"] = datetime.now(timezone.utc)
                sensor["last_error"] = None
                if "upload_result" in result and "csv_sample" in result.get("upload_result", {}):
                    sensor["last_csv_sample"] = result["upload_result"]["csv_sample"]
            else:
                # Smart error detection - pass power_mode so it knows load OFF might be expected
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
                else:
                    sensor["status"] = SensorStatus.ERROR
                
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
                sensor["status"] = SensorStatus.ACTIVE
                sensor["status_reason"] = None
                sensor["last_active"] = datetime.now(timezone.utc)
                sensor["last_error"] = None
                if "upload_result" in result and "csv_sample" in result.get("upload_result", {}):
                    sensor["last_csv_sample"] = result["upload_result"]["csv_sample"]
            else:
                # Check if there's a linked voltage meter for error detection
                if voltage_meter:
                    result = await self._enhance_error_with_voltage_meter_status(result, voltage_meter, power_mode)
                
                sensor["last_error"] = result.get("error_message", "Unknown error")
                sensor["status_reason"] = result.get("error_type")
                
                if result.get("error_type") == "battery_low":
                    sensor["status"] = SensorStatus.OFFLINE
                elif result.get("error_type") == "cloud_error":
                    sensor["status"] = SensorStatus.ERROR
                else:
                    sensor["status"] = SensorStatus.ERROR
        
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
            print(f"Error checking voltage meter status: {e}")
        
        return result
    
    
    async def _poll_tempest_sensor(self, sensor_id: str):
        """Poll a Tempest sensor (runs every 60 seconds)."""
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
            sensor["status_reason"] = None
            sensor["last_active"] = datetime.now(timezone.utc)
            sensor["last_error"] = None
            # Update battery voltage from reading
            if result.get("reading") and result["reading"].get("battery_volts"):
                sensor["battery_volts"] = result["reading"]["battery_volts"]
        else:
            sensor["status"] = SensorStatus.ERROR
            sensor["status_reason"] = result.get("error_type")
            sensor["last_error"] = result.get("error_message", "Unknown error")
        
        self._save_to_file()
    
    
    async def _poll_voltage_meter(self, sensor_id: str):
        """Poll a Voltage Meter (runs every 60 seconds)."""
        sensor = self._sensors.get(sensor_id)
        if not sensor:
            return
        
        result = await self.voltage_meter_service.fetch_and_push(
            ip_address=sensor["ip_address"],
            sensor_name=sensor["name"],
            upload_token=sensor["upload_token"]
        )
        
        if result["status"] == "success":
            sensor["status"] = SensorStatus.ACTIVE
            sensor["status_reason"] = None
            sensor["last_active"] = datetime.now(timezone.utc)
            sensor["last_error"] = None
            # Update battery voltage from reading
            if result.get("reading") and result["reading"].get("voltage_v") is not None:
                sensor["battery_volts"] = result["reading"]["voltage_v"]
            # Store CSV sample
            if result.get("csv_sample"):
                sensor["last_csv_sample"] = result["csv_sample"]
        else:
            sensor["status"] = SensorStatus.ERROR
            sensor["status_reason"] = result.get("error_type")
            sensor["last_error"] = result.get("error_message", "Unknown error")
        
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
    
    def set_power_mode(self, sensor_id: str, power_mode: str) -> Optional[SensorResponse]:
        """Set the power mode for a Purple Air sensor."""
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
                        # Let the ESP32 handle cutoff/reconnect logic automatically
                        asyncio.create_task(self.voltage_meter_service.set_auto_mode(vm_ip, auto=True))
                except Exception as e:
                    print(f"Warning: failed to set voltage meter auto mode for sensor {sensor_id}: {e}")
        
        # Restart polling job to update pre-wake schedule
        if sensor["is_active"]:
            self._stop_polling_job(sensor_id)
            self._start_polling_job(sensor_id, self._poll_purple_air_sensor)
        
        self._save_to_file()
        
        return SensorResponse(**{k: v for k, v in sensor.items() if k != "upload_token"})
    
    
    # =========================================================================
    # CLEANUP
    # =========================================================================
    
    async def shutdown(self):
        """Clean up when the server is shutting down."""
        self._save_to_file()
        self.scheduler.shutdown(wait=False)
        await self.purple_air_service.close()
        await self.tempest_service.close()
        await self.voltage_meter_service.close()