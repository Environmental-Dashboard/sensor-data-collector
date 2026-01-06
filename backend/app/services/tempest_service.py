"""
Tempest Weather Sensor Service
==============================
Complete implementation for WeatherFlow Tempest weather station operations.

This service handles the full data pipeline:
1. Fetch data from Tempest Hub via local network or UDP
2. Parse and validate the response
3. Convert to CSV format
4. Push CSV to external endpoint

TEMPEST LOCAL ACCESS:
    Tempest Hub broadcasts data via UDP on port 50222.
    Alternatively, you can query the hub directly via REST.
    
    UDP Broadcast: Listen on port 50222 for JSON messages
    REST API: http://<hub_ip>/v1/obs (requires firmware 150+)

DATA TYPES FROM TEMPEST:
    - obs_st: Observation from Tempest device (weather data)
    - rapid_wind: Wind data every 3 seconds
    - evt_precip: Rain start event
    - evt_strike: Lightning strike event
    - device_status: Device health info
    - hub_status: Hub health info

Author: Sensor Data Collector Team
"""

import httpx
import io
import socket
import json
from datetime import datetime, timezone
from typing import Optional

from app.models import TempestReading


class TempestService:
    """
    Service for WeatherFlow Tempest weather station operations.
    
    Tempest provides comprehensive weather data including temperature,
    humidity, wind, rain, UV, solar radiation, and lightning detection.
    
    This service supports two modes of data collection:
    1. REST API: Query the hub directly (simpler, used by default)
    2. UDP Listener: Listen for broadcast messages (more real-time)
    
    Usage:
        service = TempestService(
            external_endpoint_url="https://example.com/upload",
            external_endpoint_token="your-token"
        )
        
        # Fetch and push
        result = await service.fetch_and_push(
            ip_address="192.168.1.150",
            device_id="12345",
            sensor_name="Campus Weather"
        )
    """
    
    def __init__(
        self, 
        external_endpoint_url: str, 
        external_endpoint_token: str,
        request_timeout: float = 10.0
    ):
        """
        Initialize the Tempest service.
        
        Args:
            external_endpoint_url: URL to push CSV data to
            external_endpoint_token: Bearer token for authentication
            request_timeout: HTTP request timeout in seconds
        """
        self.external_endpoint_url = external_endpoint_url
        self.external_endpoint_token = external_endpoint_token
        self.http_client = httpx.AsyncClient(timeout=request_timeout)
    
    async def fetch_sensor_data(
        self, 
        ip_address: str, 
        device_id: str
    ) -> dict:
        """
        Fetch data from Tempest Hub via REST API.
        
        Queries the hub's local REST endpoint for current observations.
        
        Args:
            ip_address: IP address of the Tempest Hub
            device_id: Device ID of the Tempest unit
            
        Returns:
            Raw observation data as dictionary
            
        Raises:
            httpx.ConnectError: Hub unreachable
            httpx.TimeoutException: Request timed out
            
        Example Response (obs_st observation):
            {
                "serial_number": "ST-00012345",
                "type": "obs_st",
                "hub_sn": "HB-00001234",
                "obs": [[
                    1609459200,      # epoch (timestamp)
                    0.18,            # wind_lull (m/s)
                    0.22,            # wind_avg (m/s)
                    0.27,            # wind_gust (m/s)
                    144,             # wind_direction (degrees)
                    3,               # wind_sample_interval (seconds)
                    1017.57,         # pressure (mb)
                    22.37,           # air_temperature (C)
                    50.26,           # relative_humidity (%)
                    328,             # illuminance (lux)
                    0.03,            # uv (index)
                    3,               # solar_radiation (W/m^2)
                    0.000000,        # rain_accumulated (mm)
                    0,               # precipitation_type (0=none,1=rain,2=hail)
                    0,               # lightning_strike_avg_distance (km)
                    0,               # lightning_strike_count
                    2.410,           # battery (volts)
                    1                # report_interval (minutes)
                ]],
                "firmware_revision": 156
            }
        """
        # Try the REST API endpoint first
        url = f"http://{ip_address}/v1/obs"
        
        try:
            response = await self.http_client.get(url)
            response.raise_for_status()
            data = response.json()
            
            # Find the observation for our device
            # The hub returns observations for all connected devices
            if isinstance(data, dict) and "obs" in data:
                return data
            elif isinstance(data, list):
                # Look for our device in the list
                for obs in data:
                    if obs.get("serial_number", "").endswith(device_id):
                        return obs
                # If not found, return first obs_st type
                for obs in data:
                    if obs.get("type") == "obs_st":
                        return obs
                        
            return data
            
        except httpx.HTTPStatusError:
            # Fall back to UDP if REST doesn't work
            return await self._fetch_via_udp(device_id)
    
    async def _fetch_via_udp(
        self, 
        device_id: str, 
        timeout: float = 5.0
    ) -> dict:
        """
        Fetch data by listening to UDP broadcast.
        
        Tempest Hub broadcasts data on UDP port 50222.
        This method listens for a message matching our device.
        
        Args:
            device_id: Device ID to look for
            timeout: How long to wait for a matching message
            
        Returns:
            Observation data
            
        Note:
            This is a fallback method. The REST API is preferred.
        """
        UDP_PORT = 50222
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.settimeout(timeout)
        sock.bind(("", UDP_PORT))
        
        try:
            # Wait for a message from our device
            start_time = datetime.now()
            while (datetime.now() - start_time).seconds < timeout:
                try:
                    data, addr = sock.recvfrom(4096)
                    message = json.loads(data.decode("utf-8"))
                    
                    # Check if this is from our device
                    if message.get("type") == "obs_st":
                        serial = message.get("serial_number", "")
                        if device_id in serial or not device_id:
                            return message
                except socket.timeout:
                    break
                    
            raise Exception(f"No data received from device {device_id}")
            
        finally:
            sock.close()
    
    def parse_sensor_response(self, raw_data: dict) -> TempestReading:
        """
        Parse raw Tempest observation into a structured reading.
        
        Converts the array-based observation format to named fields,
        and converts units as needed.
        
        Args:
            raw_data: Raw observation from fetch_sensor_data()
            
        Returns:
            TempestReading with all weather data
            
        Unit Conversions:
            - Temperature: Celsius -> Fahrenheit
            - Wind speed: m/s -> mph
            - Pressure: mb (no conversion needed)
            - Rain: mm -> inches
        """
        # Extract observation array
        obs = raw_data.get("obs", [[]])[0]
        
        if not obs or len(obs) < 17:
            # Return empty reading if data is missing
            return TempestReading(
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
            )
        
        # Parse observation array (indices based on Tempest API spec)
        # Index: Field
        # 0: epoch
        # 1: wind_lull (m/s)
        # 2: wind_avg (m/s)
        # 3: wind_gust (m/s)
        # 4: wind_direction (degrees)
        # 5: wind_sample_interval
        # 6: pressure (mb)
        # 7: air_temperature (C)
        # 8: relative_humidity (%)
        # 9: illuminance (lux)
        # 10: uv (index)
        # 11: solar_radiation (W/m^2)
        # 12: rain_accumulated (mm)
        # 13: precipitation_type
        # 14: lightning_strike_avg_distance (km)
        # 15: lightning_strike_count
        # 16: battery (volts)
        # 17: report_interval (minutes)
        
        epoch = obs[0] if len(obs) > 0 else 0
        wind_avg_ms = obs[2] if len(obs) > 2 else 0
        wind_gust_ms = obs[3] if len(obs) > 3 else 0
        wind_dir = obs[4] if len(obs) > 4 else 0
        pressure = obs[6] if len(obs) > 6 else 0
        temp_c = obs[7] if len(obs) > 7 else 0
        humidity = obs[8] if len(obs) > 8 else 0
        uv = obs[10] if len(obs) > 10 else 0
        solar = obs[11] if len(obs) > 11 else 0
        rain_mm = obs[12] if len(obs) > 12 else 0
        lightning = obs[15] if len(obs) > 15 else 0
        
        # Convert units
        temp_f = (temp_c * 9/5) + 32 if temp_c else 0
        wind_avg_mph = wind_avg_ms * 2.237 if wind_avg_ms else 0
        wind_gust_mph = wind_gust_ms * 2.237 if wind_gust_ms else 0
        rain_inches = rain_mm * 0.03937 if rain_mm else 0
        
        # Parse timestamp
        timestamp = datetime.fromtimestamp(epoch, tz=timezone.utc) if epoch else datetime.now(timezone.utc)
        
        return TempestReading(
            timestamp=timestamp,
            temperature_f=round(temp_f, 2),
            humidity_percent=round(float(humidity), 2),
            pressure_mb=round(float(pressure), 2),
            wind_speed_mph=round(wind_avg_mph, 2),
            wind_gust_mph=round(wind_gust_mph, 2),
            wind_direction_deg=int(wind_dir),
            rain_inches=round(rain_inches, 4),
            uv_index=round(float(uv), 2),
            solar_radiation=round(float(solar), 2),
            lightning_count=int(lightning)
        )
    
    def convert_to_csv(
        self, 
        reading: TempestReading, 
        include_header: bool = True
    ) -> str:
        """
        Convert a Tempest reading to CSV format.
        
        Args:
            reading: Parsed weather reading
            include_header: Whether to include header row
            
        Returns:
            CSV formatted string
        """
        lines = []
        
        if include_header:
            lines.append(TempestReading.csv_header())
        
        lines.append(reading.to_csv_row())
        
        return "\n".join(lines)
    
    async def push_to_endpoint(
        self, 
        csv_data: str, 
        sensor_name: str
    ) -> dict:
        """
        Push CSV data to the external endpoint.
        
        Args:
            csv_data: CSV string to upload
            sensor_name: Used to generate filename
            
        Returns:
            Upload result dict
        """
        headers = {
            "Authorization": f"Bearer {self.external_endpoint_token}"
        }
        
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        clean_name = "".join(c if c.isalnum() else "_" for c in sensor_name)
        filename = f"{clean_name}_{timestamp}.csv"
        
        csv_bytes = csv_data.encode("utf-8")
        csv_file = io.BytesIO(csv_bytes)
        
        files = {
            "file": (filename, csv_file, "text/csv")
        }
        
        response = await self.http_client.post(
            self.external_endpoint_url,
            headers=headers,
            files=files
        )
        response.raise_for_status()
        
        return {
            "status": "success",
            "filename": filename,
            "uploaded_at": datetime.now(timezone.utc).isoformat()
        }
    
    async def fetch_and_push(
        self, 
        ip_address: str, 
        device_id: str,
        sensor_name: str
    ) -> dict:
        """
        Complete workflow: Fetch → Parse → Convert → Push.
        
        Args:
            ip_address: IP of the Tempest Hub
            device_id: Tempest device ID
            sensor_name: Name for logging and filename
            
        Returns:
            Result dict with status and data or error
        """
        try:
            raw_data = await self.fetch_sensor_data(ip_address, device_id)
            reading = self.parse_sensor_response(raw_data)
            csv_data = self.convert_to_csv(reading, include_header=True)
            upload_result = await self.push_to_endpoint(csv_data, sensor_name)
            
            return {
                "status": "success",
                "sensor_name": sensor_name,
                "reading": reading.model_dump(),
                "upload_result": upload_result
            }
            
        except httpx.ConnectError as e:
            return {
                "status": "error",
                "sensor_name": sensor_name,
                "error_type": "connection_error",
                "error_message": f"Cannot connect to Tempest Hub at {ip_address}: {str(e)}"
            }
        except Exception as e:
            return {
                "status": "error",
                "sensor_name": sensor_name,
                "error_type": "unknown_error",
                "error_message": str(e)
            }
    
    async def close(self):
        """Close the HTTP client."""
        await self.http_client.aclose()

