"""
Tempest Weather Sensor Service
==============================

This handles WeatherFlow Tempest weather stations.

WHAT'S A TEMPEST?
----------------
Tempest is a fancy weather station that measures:
- Temperature and humidity
- Wind speed, gusts, and direction
- Rain
- UV index and sunlight
- Lightning strikes (yes, really!)

HOW IT WORKS:
------------
We use the WeatherFlow Cloud REST API to get data.
The cloud updates every ~60 seconds.

API Endpoint:
https://swd.weatherflow.com/swd/rest/observations/device/{device_id}?token={api_token}

We track the last observation timestamp and only upload to Community Hub
when new data is detected.

Author: Frank Kusi Appiah
"""

import httpx
import os
import logging
from datetime import datetime, timezone
from typing import Optional

from app.models import TempestReading

logger = logging.getLogger(__name__)


def safe_float(value, default: float = 0.0) -> float:
    """Safely convert value to float."""
    if value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def safe_int(value, default: int = 0) -> int:
    """Safely convert value to int."""
    if value is None:
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


class TempestService:
    """
    Everything for Tempest weather stations.
    
    Now uses the WeatherFlow Cloud REST API for reliable data access.
    Tracks timestamps to detect and upload only NEW data.
    
    Usage:
        service = TempestService(api_token="your-weatherflow-token")
        result = await service.fetch_and_push(
            device_id="205498",
            sensor_name="Campus Weather",
            upload_token="your-community-hub-token"
        )
    """
    
    # WeatherFlow Cloud API
    CLOUD_API_URL = "https://swd.weatherflow.com/swd/rest/observations/device"
    
    # Community Hub upload
    UPLOAD_URL = "https://oberlin.communityhub.cloud/api/data-hub/upload/csv"
    
    def __init__(self, api_token: str = None, request_timeout: float = 15.0):
        """
        Set up the service.
        
        Args:
            api_token: Your WeatherFlow API token (get from tempestwx.com/settings/tokens)
            request_timeout: How long to wait for API responses
        """
        self.api_token = api_token or os.getenv("TEMPEST_API_TOKEN", "")
        self.http_client = httpx.AsyncClient(timeout=request_timeout)
        
        # Track last observation timestamp per device to detect new data
        self._last_observation_time: dict[str, int] = {}
    
    
    async def fetch_from_cloud(self, device_id: str) -> dict:
        """
        Fetch latest observation from WeatherFlow Cloud API.
        
        API: https://swd.weatherflow.com/swd/rest/observations/device/{device_id}
        
        Returns the full API response with observation data.
        """
        if not self.api_token:
            raise ValueError("WeatherFlow API token is required. Set TEMPEST_API_TOKEN env var.")
        
        url = f"{self.CLOUD_API_URL}/{device_id}"
        params = {"token": self.api_token}
        
        response = await self.http_client.get(url, params=params)
        response.raise_for_status()
        
        return response.json()
    
    
    async def fetch_sensor_data(self, ip_address: Optional[str], device_id: str) -> dict:
        """
        Get data from Tempest - uses Cloud API (local Hub deprecated).
        
        Args:
            ip_address: Ignored (kept for backwards compatibility)
            device_id: The Tempest device ID (from WeatherFlow app)
        
        Returns:
            Raw observation data from Cloud API
        """
        # Always use cloud API for reliability
        return await self.fetch_from_cloud(device_id)
    
    
    def parse_cloud_response(self, data: dict) -> tuple[TempestReading, int, float]:
        """
        Parse WeatherFlow Cloud API response.
        
        The cloud API returns data in a different format than the local Hub.
        
        Returns:
            tuple: (TempestReading, observation_timestamp, battery_volts)
        """
        obs = data.get("obs", [[]])[0] if data.get("obs") else []
        device_info = data.get("device", {})
        
        if not obs or len(obs) < 18:
            # Return empty reading if data is missing
            return (
                TempestReading(
                    timestamp=datetime.now(timezone.utc),
                    temperature_f=0.0,
                    humidity_percent=0.0,
                    pressure_mb=0.0,
                    wind_speed_mph=0.0,
                    wind_gust_mph=0.0,
                    wind_direction_deg=0,
                    rain_inches=0.0,
                    uv_index=0.0,
                    solar_radiation=0.0,
                    lightning_count=0
                ),
                0,
                0.0
            )
        
        # WeatherFlow obs_st array indices:
        # [0] = timestamp (epoch)
        # [1] = wind lull (m/s)
        # [2] = wind avg (m/s)
        # [3] = wind gust (m/s)
        # [4] = wind direction (degrees)
        # [5] = wind sample interval (s)
        # [6] = pressure (mb)
        # [7] = air temperature (C)
        # [8] = relative humidity (%)
        # [9] = illuminance (lux)
        # [10] = UV index
        # [11] = solar radiation (W/m²)
        # [12] = rain accumulated (mm)
        # [13] = precipitation type (0=none, 1=rain, 2=hail)
        # [14] = lightning strike avg distance (km)
        # [15] = lightning strike count
        # [16] = battery (V)
        # [17] = report interval (min)
        
        epoch = safe_int(obs[0])
        wind_avg_ms = safe_float(obs[2])
        wind_gust_ms = safe_float(obs[3])
        wind_dir = safe_int(obs[4])
        pressure = safe_float(obs[6])
        temp_c = safe_float(obs[7])
        humidity = safe_float(obs[8])
        uv = safe_float(obs[10])
        solar = safe_float(obs[11])
        rain_mm = safe_float(obs[12])
        lightning = safe_int(obs[15])
        battery = safe_float(obs[16]) if len(obs) > 16 else 0.0
        
        # Convert units
        temp_f = (temp_c * 9/5) + 32 if temp_c else 0
        wind_avg_mph = wind_avg_ms * 2.237 if wind_avg_ms else 0
        wind_gust_mph = wind_gust_ms * 2.237 if wind_gust_ms else 0
        rain_inches = rain_mm * 0.03937 if rain_mm else 0
        
        timestamp = datetime.fromtimestamp(epoch, tz=timezone.utc) if epoch else datetime.now(timezone.utc)
        
        reading = TempestReading(
            timestamp=timestamp,
            temperature_f=round(temp_f, 1),
            humidity_percent=round(humidity, 0),
            pressure_mb=round(pressure, 1),
            wind_speed_mph=round(wind_avg_mph, 1),
            wind_gust_mph=round(wind_gust_mph, 1),
            wind_direction_deg=wind_dir,
            rain_inches=round(rain_inches, 2),
            uv_index=round(uv, 1),
            solar_radiation=round(solar, 0),
            lightning_count=lightning,
            battery_volts=round(battery, 2)
        )
        
        return reading, epoch, battery
    
    
    def is_new_observation(self, device_id: str, observation_time: int) -> bool:
        """
        Check if this observation is newer than the last one we saw.
        
        Prevents uploading duplicate data when the cloud hasn't updated yet.
        """
        last_time = self._last_observation_time.get(device_id, 0)
        
        if observation_time > last_time:
            self._last_observation_time[device_id] = observation_time
            return True
        
        return False
    
    
    def convert_to_csv(self, reading: TempestReading, include_header: bool = True) -> str:
        """Convert reading to CSV format."""
        lines = []
        if include_header:
            lines.append(TempestReading.csv_header())
        lines.append(reading.to_csv_row())
        return "\n".join(lines)
    
    
    async def push_to_endpoint(self, csv_data: str, sensor_name: str, upload_token: str) -> dict:
        """Upload CSV to Community Hub with retry logic."""
        import asyncio
        
        headers = {
            "user-token": upload_token,
            "Content-Type": "text/csv"
        }
        
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        clean_name = "".join(c if c.isalnum() else "_" for c in sensor_name)
        filename = f"{clean_name}_{timestamp}.csv"
        
        csv_bytes = csv_data.encode("utf-8")
        
        # Retry logic for cloud errors (502, 503, 504)
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
                    "uploaded_at": datetime.now(timezone.utc).isoformat(),
                    "csv_sample": csv_data
                }
            except httpx.HTTPStatusError as e:
                if e.response.status_code in [502, 503, 504] and attempt < max_retries - 1:
                    logger.warning(f"[{sensor_name}] Cloud error {e.response.status_code}, retrying in {retry_delay}s...")
                    await asyncio.sleep(retry_delay)
                    continue
                raise
    
    
    async def fetch_and_push(
        self, 
        ip_address: Optional[str],  # Ignored, kept for compatibility
        device_id: str, 
        sensor_name: str,
        upload_token: str
    ) -> dict:
        """
        The main function - fetch data from cloud and upload if new.
        
        Called every 60 seconds for active Tempest sensors.
        Only uploads to Community Hub when NEW data is detected.
        """
        try:
            # Fetch from WeatherFlow Cloud API
            logger.info(f"[{sensor_name}] Fetching from WeatherFlow Cloud API (device: {device_id})...")
            raw_data = await self.fetch_from_cloud(device_id)
            
            # Parse the response
            reading, obs_time, battery = self.parse_cloud_response(raw_data)
            
            # Check if this is new data
            if not self.is_new_observation(device_id, obs_time):
                logger.debug(f"[{sensor_name}] No new data (last obs: {datetime.fromtimestamp(obs_time, tz=timezone.utc)})")
                return {
                    "status": "success",
                    "sensor_name": sensor_name,
                    "reading": {
                        **reading.model_dump(),
                        "battery_volts": battery
                    },
                    "upload_result": {
                        "status": "skipped",
                        "reason": "no_new_data",
                        "observation_time": obs_time
                    }
                }
            
            # New data! Convert to CSV and upload
            logger.info(f"[{sensor_name}] New data detected! Uploading to Community Hub...")
            csv_data = self.convert_to_csv(reading, include_header=True)
            upload_result = await self.push_to_endpoint(csv_data, sensor_name, upload_token)
            
            return {
                "status": "success",
                "sensor_name": sensor_name,
                "reading": {
                    **reading.model_dump(),
                    "battery_volts": battery
                },
                "upload_result": upload_result
            }
            
        except httpx.ConnectError as e:
            return {
                "status": "error",
                "sensor_name": sensor_name,
                "error_type": "connection_error",
                "error_message": f"Cannot connect to WeatherFlow Cloud API: {str(e)}"
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
            elif e.response.status_code == 401:
                error_type = "auth_error"
                error_msg = "Invalid API token - check your WeatherFlow token"
            elif e.response.status_code == 404:
                error_type = "not_found"
                error_msg = f"Device {device_id} not found in WeatherFlow Cloud"
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
        except ValueError as e:
            return {
                "status": "error",
                "sensor_name": sensor_name,
                "error_type": "config_error",
                "error_message": str(e)
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
        """Clean up."""
        await self.http_client.aclose()
