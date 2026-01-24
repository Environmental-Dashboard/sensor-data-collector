"""
Voltage Meter Service
=====================

This service communicates with ESP32 Battery Cutoff Monitor devices.

WHAT IT DOES:
------------
1. Gets voltage readings from the ESP32
2. Controls the relay (turn load ON/OFF)
3. Adjusts voltage thresholds
4. Uploads data to Community Hub

ESP32 API ENDPOINTS:
-------------------
- GET /status.json - Current status (voltage, relay state, thresholds)
- GET /relay?on=1 - Turn relay ON (power up load)
- GET /relay?on=0 - Turn relay OFF (power down load)
- GET /relay?auto=1 - Enable auto mode
- GET /settings?lower=X&upper=Y - Set voltage thresholds
- GET /settings?target=X - Auto-calibrate ADC

Author: Frank Kusi Appiah
"""

import httpx
import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)


def safe_float(value, default: float = 0.0) -> float:
    """Safely convert value to float, handling None and invalid strings."""
    if value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def safe_int(value, default: int = 0) -> int:
    """Safely convert value to int, handling None and invalid strings."""
    if value is None:
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def safe_bool(value, default: bool = False) -> bool:
    """Safely convert value to bool."""
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.lower() in ('true', '1', 'yes', 'on')
    return default


class VoltageMeterService:
    """
    Service for communicating with ESP32 Battery Cutoff Monitor.
    
    The ESP32 monitors battery voltage and controls a relay to protect
    the battery from over-discharge.
    """
    
    # Upload URL for Community Hub
    UPLOAD_URL = "https://oberlin.communityhub.cloud/api/data-hub/upload/csv"
    
    def __init__(self, request_timeout: float = 10.0):
        """
        Initialize the service.
        
        Args:
            request_timeout: How long to wait for ESP32 responses (seconds)
        """
        self.http_client = httpx.AsyncClient(timeout=request_timeout)
    
    
    async def get_status(self, ip_address: str) -> Optional[dict]:
        """
        Get current status from the voltage meter.
        
        Returns:
            {
                "voltage_v": 12.5,
                "load_on": True,
                "auto_mode": True,
                "v_cutoff": 11.0,
                "v_reconnect": 12.6,
                "calibration_factor": 1.17,
                "cycle_count": 42,
                "turn_on_count_48h": 5,
                "uptime_ms": 123456
            }
        """
        try:
            url = f"http://{ip_address}/status.json"
            response = await self.http_client.get(url)
            response.raise_for_status()
            data = response.json()
            
            # Parse with safe defaults
            return {
                "voltage_v": safe_float(data.get("voltage_v")),
                "load_on": safe_bool(data.get("load_on")),
                "auto_mode": safe_bool(data.get("auto_mode")),
                "v_cutoff": safe_float(data.get("v_cutoff"), 12.0),
                "v_reconnect": safe_float(data.get("v_reconnect"), 12.9),
                "calibration_factor": safe_float(data.get("calibration_factor"), 1.0),
                "cycle_count": safe_int(data.get("cycle_count")),
                "turn_on_count_48h": safe_int(data.get("turn_on_count_48h")),
                "last_switch_time_ms": safe_int(data.get("last_switch_time_ms")),
                "uptime_ms": safe_int(data.get("uptime_ms")),
            }
        except httpx.ConnectError as e:
            logger.error(f"Cannot connect to voltage meter at {ip_address}: {e}")
            return None
        except httpx.TimeoutException:
            logger.error(f"Timeout connecting to voltage meter at {ip_address}")
            return None
        except Exception as e:
            logger.error(f"Error getting voltage meter status: {e}")
            return None
    
    
    async def set_relay(self, ip_address: str, on: bool) -> bool:
        """
        Control the relay (turn load ON or OFF).
        
        Args:
            ip_address: ESP32 IP address
            on: True to turn ON, False to turn OFF
            
        Returns:
            True if successful, False otherwise
        """
        try:
            url = f"http://{ip_address}/relay?on={'1' if on else '0'}"
            response = await self.http_client.get(url)
            response.raise_for_status()
            logger.info(f"Relay {'ON' if on else 'OFF'} command sent to {ip_address}")
            return True
        except Exception as e:
            logger.error(f"Error controlling relay at {ip_address}: {e}")
            return False
    
    
    async def set_auto_mode(self, ip_address: str, auto: bool = True) -> bool:
        """
        Enable or disable auto mode on the voltage meter.
        
        In auto mode, the relay is controlled by voltage thresholds.
        """
        try:
            url = f"http://{ip_address}/relay?auto={'1' if auto else '0'}"
            response = await self.http_client.get(url)
            response.raise_for_status()
            logger.info(f"Auto mode {'enabled' if auto else 'disabled'} on {ip_address}")
            return True
        except Exception as e:
            logger.error(f"Error setting auto mode at {ip_address}: {e}")
            return False
    
    
    async def set_thresholds(
        self, 
        ip_address: str, 
        lower: Optional[float] = None, 
        upper: Optional[float] = None
    ) -> bool:
        """
        Set voltage thresholds.
        
        Args:
            ip_address: ESP32 IP address
            lower: Cutoff voltage (turns OFF at or below this)
            upper: Reconnect voltage (turns ON at or above this)
        """
        try:
            params = []
            if lower is not None:
                params.append(f"lower={lower}")
            if upper is not None:
                params.append(f"upper={upper}")
            
            if not params:
                return True  # Nothing to set
            
            url = f"http://{ip_address}/settings?{'&'.join(params)}"
            response = await self.http_client.get(url)
            response.raise_for_status()
            logger.info(f"Thresholds set on {ip_address}: lower={lower}, upper={upper}")
            return True
        except Exception as e:
            logger.error(f"Error setting thresholds at {ip_address}: {e}")
            return False
    
    
    async def calibrate(self, ip_address: str, target_voltage: float) -> bool:
        """
        Auto-calibrate the ADC by providing the actual voltage reading.
        
        Args:
            ip_address: ESP32 IP address
            target_voltage: The actual voltage from a multimeter
        """
        try:
            url = f"http://{ip_address}/settings?target={target_voltage}"
            response = await self.http_client.get(url)
            response.raise_for_status()
            
            # Try to parse response to verify it worked
            try:
                data = response.json()
                logger.info(f"Calibration set on {ip_address} with target={target_voltage}V. Response: {data}")
            except Exception:
                # Some ESP32s might return plain text or empty response, that's OK
                logger.info(f"Calibration set on {ip_address} with target={target_voltage}V")
            
            return True
        except httpx.ConnectError as e:
            logger.error(f"Cannot connect to voltage meter at {ip_address} for calibration: {e}")
            raise Exception(f"Cannot connect to ESP32 at {ip_address}. Check power and network connection.")
        except httpx.TimeoutException:
            logger.error(f"Timeout connecting to voltage meter at {ip_address} for calibration")
            raise Exception(f"ESP32 at {ip_address} did not respond. Check power and network connection.")
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error calibrating voltage meter at {ip_address}: {e.response.status_code}")
            raise Exception(f"ESP32 returned error {e.response.status_code}. Check ESP32 firmware.")
        except Exception as e:
            logger.error(f"Error calibrating voltage meter at {ip_address}: {e}")
            raise Exception(f"Calibration failed: {str(e)}")
    
    
    def create_csv_row(self, status: dict) -> str:
        """Convert status to CSV row."""
        try:
            from zoneinfo import ZoneInfo
            eastern = ZoneInfo("America/New_York")
        except ImportError:
            from datetime import timedelta
            eastern = timezone(timedelta(hours=-5))
        
        now = datetime.now(eastern)
        offset = now.utcoffset()
        if offset:
            total_seconds = int(offset.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            sign = '-' if total_seconds < 0 else '+'
            timestamp = now.strftime(f"%Y-%m-%dT%H:%M:%S{sign}{abs(hours):02d}:{abs(minutes):02d}")
        else:
            timestamp = now.strftime("%Y-%m-%dT%H:%M:%S-05:00")
        
        load_on = 1 if status.get("load_on") else 0
        auto_mode = 1 if status.get("auto_mode") else 0
        
        return (
            f"{timestamp},"
            f"{status.get('voltage_v', 0):.2f},"
            f"{load_on},"
            f"{auto_mode},"
            f"{status.get('v_cutoff', 12.0):.2f},"
            f"{status.get('v_reconnect', 12.9):.2f},"
            f"{status.get('calibration_factor', 1.0):.4f},"
            f"{status.get('cycle_count', 0)},"
            f"{status.get('turn_on_count_48h', 0)},"
            f"{status.get('uptime_ms', 0)}"
        )
    
    
    @staticmethod
    def csv_header() -> str:
        """CSV header for voltage meter data."""
        return "Timestamp,Voltage (V),Load On,Auto Mode,Cutoff (V),Reconnect (V),Calibration Factor,Cycle Count,Cycles 48h,Uptime (ms)"
    
    
    async def push_to_endpoint(self, csv_data: str, sensor_name: str, upload_token: str) -> dict:
        """Upload CSV to Community Hub with retry logic."""
        import asyncio
        
        headers = {
            "user-token": upload_token,
            "Content-Type": "text/csv"
        }
        
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        clean_name = "".join(c if c.isalnum() else "_" for c in sensor_name)
        filename = f"VM_{clean_name}_{timestamp}.csv"
        
        csv_bytes = csv_data.encode("utf-8")
        
        # Retry logic for cloud errors
        max_retries = 2
        retry_delay = 3
        
        for attempt in range(max_retries):
            try:
                response = await self.http_client.post(
                    self.UPLOAD_URL,
                    headers=headers,
                    content=csv_bytes
                )
                response.raise_for_status()
                
                return {
                    "status": "success",
                    "filename": filename,
                    "uploaded_at": datetime.now(timezone.utc).isoformat()
                }
            except httpx.HTTPStatusError as e:
                if e.response.status_code in [502, 503, 504] and attempt < max_retries - 1:
                    logger.warning(f"[{sensor_name}] Cloud error {e.response.status_code}, retrying...")
                    await asyncio.sleep(retry_delay)
                    continue
                raise
    
    
    async def fetch_and_push(
        self, 
        ip_address: str, 
        sensor_name: str, 
        upload_token: str
    ) -> dict:
        """
        Fetch voltage meter status and upload to cloud.
        """
        try:
            # Get status from ESP32
            status = await self.get_status(ip_address)
            if not status:
                return {
                    "status": "error",
                    "sensor_name": sensor_name,
                    "error_type": "connection_error",
                    "error_message": f"Cannot connect to voltage meter at {ip_address}"
                }
            
            # Create CSV
            header = self.csv_header()
            row = self.create_csv_row(status)
            csv_data = f"{header}\n{row}"
            
            # Upload
            upload_result = await self.push_to_endpoint(csv_data, sensor_name, upload_token)
            
            return {
                "status": "success",
                "sensor_name": sensor_name,
                "reading": status,
                "upload_result": upload_result,
                "csv_sample": csv_data
            }
            
        except httpx.HTTPStatusError as e:
            error_body = ""
            try:
                error_body = e.response.text[:500]
            except Exception:
                pass
            
            if e.response.status_code in [502, 503, 504]:
                error_type = "cloud_error"
                error_msg = f"Cloud service error ({e.response.status_code})"
            else:
                error_type = "http_error"
                error_msg = f"HTTP error {e.response.status_code}: {error_body}"
            
            return {
                "status": "error",
                "sensor_name": sensor_name,
                "error_type": error_type,
                "error_message": error_msg,
                "http_status": e.response.status_code
            }
        except Exception as e:
            # Capture full exception details
            error_type_name = type(e).__name__
            error_msg = str(e) if str(e) else repr(e)
            logger.error(f"[{sensor_name}] Unexpected error ({error_type_name}): {error_msg}")
            return {
                "status": "error",
                "sensor_name": sensor_name,
                "error_type": "unknown_error",
                "error_message": f"{error_type_name}: {error_msg}" if error_msg else error_type_name
            }
    
    
    async def close(self):
        """Clean up HTTP client."""
        await self.http_client.aclose()
