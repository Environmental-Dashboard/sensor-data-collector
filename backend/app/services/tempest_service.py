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
The Tempest device sends data to a Hub (base station).
The Hub is connected to your WiFi and we can talk to it.

You can either:
1. Query the Hub directly via REST API
2. Listen for UDP broadcasts on port 50222

We try REST first because it's simpler.

Author: Frank Kusi Appiah
"""

import httpx
import io
import socket
import json
from datetime import datetime, timezone

from app.models import TempestReading


class TempestService:
    """
    Everything for Tempest weather stations.
    
    Usage:
        service = TempestService()
        result = await service.fetch_and_push(
            ip_address="192.168.1.150",
            device_id="12345",
            sensor_name="Campus Weather",
            upload_token="your-token"
        )
    """
    
    # Where to upload the data
    UPLOAD_URL = "https://oberlin.communityhub.cloud/api/data-hub/upload/csv"
    
    def __init__(self, request_timeout: float = 15.0):
        """Set up the service."""
        self.http_client = httpx.AsyncClient(timeout=request_timeout)
    
    
    async def fetch_sensor_data(self, ip_address: str, device_id: str) -> dict:
        """
        Get data from a Tempest Hub.
        
        Args:
            ip_address: IP of the Tempest Hub
            device_id: The Tempest device ID (from WeatherFlow app)
        
        Returns:
            Raw observation data
        """
        url = f"http://{ip_address}/v1/obs"
        
        try:
            response = await self.http_client.get(url)
            response.raise_for_status()
            data = response.json()
            
            # Find our device in the response
            if isinstance(data, dict) and "obs" in data:
                return data
            elif isinstance(data, list):
                for obs in data:
                    if obs.get("serial_number", "").endswith(device_id):
                        return obs
                for obs in data:
                    if obs.get("type") == "obs_st":
                        return obs
            return data
            
        except httpx.HTTPStatusError:
            # Try UDP as backup
            return await self._fetch_via_udp(device_id)
    
    
    async def _fetch_via_udp(self, device_id: str, timeout: float = 5.0) -> dict:
        """
        Backup method: Listen for UDP broadcasts.
        
        Tempest Hub broadcasts data on UDP port 50222.
        """
        UDP_PORT = 50222
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.settimeout(timeout)
        sock.bind(("", UDP_PORT))
        
        try:
            start_time = datetime.now()
            while (datetime.now() - start_time).seconds < timeout:
                try:
                    data, addr = sock.recvfrom(4096)
                    message = json.loads(data.decode("utf-8"))
                    
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
        Parse raw Tempest data into a clean format.
        
        Tempest returns data as an array of numbers. Each position means something:
        - Index 0: timestamp
        - Index 2: wind average (m/s)
        - Index 3: wind gust (m/s)
        - Index 7: temperature (Celsius)
        - etc.
        
        We convert units to make them more useful:
        - Celsius -> Fahrenheit
        - m/s -> mph
        - mm -> inches
        """
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
        
        # Extract values from the array
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
    
    
    def convert_to_csv(self, reading: TempestReading, include_header: bool = True) -> str:
        """Convert reading to CSV format."""
        lines = []
        if include_header:
            lines.append(TempestReading.csv_header())
        lines.append(reading.to_csv_row())
        return "\n".join(lines)
    
    
    async def push_to_endpoint(self, csv_data: str, sensor_name: str, upload_token: str) -> dict:
        """Upload CSV to the cloud."""
        headers = {"Authorization": f"Bearer {upload_token}"}
        
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        clean_name = "".join(c if c.isalnum() else "_" for c in sensor_name)
        filename = f"{clean_name}_{timestamp}.csv"
        
        csv_bytes = csv_data.encode("utf-8")
        csv_file = io.BytesIO(csv_bytes)
        
        files = {"file": (filename, csv_file, "text/csv")}
        
        response = await self.http_client.post(self.UPLOAD_URL, headers=headers, files=files)
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
        sensor_name: str,
        upload_token: str
    ) -> dict:
        """
        The main function - fetch data and upload it.
        
        Called every 60 seconds for active Tempest sensors.
        """
        try:
            raw_data = await self.fetch_sensor_data(ip_address, device_id)
            reading = self.parse_sensor_response(raw_data)
            csv_data = self.convert_to_csv(reading, include_header=True)
            upload_result = await self.push_to_endpoint(csv_data, sensor_name, upload_token)
            
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
        """Clean up."""
        await self.http_client.aclose()
