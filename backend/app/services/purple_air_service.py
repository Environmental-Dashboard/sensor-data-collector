"""
Purple Air Sensor Service
=========================
Complete implementation for Purple Air sensor operations.

This service handles the full data pipeline:
1. Fetch JSON data from Purple Air sensor via local IP
2. Parse and validate the response
3. Convert to CSV format
4. Push CSV to external endpoint

PURPLE AIR LOCAL API:
    Purple Air sensors on the local network expose their data at:
    http://<sensor_ip>/json
    
    This returns a JSON object with all sensor readings.
    No authentication required for local access.

EXTERNAL ENDPOINT:
    CSV data is pushed to:
    https://oberlin.communityhub.cloud/api/data-hub/upload/csv
    
    Authentication: Bearer token in Authorization header

Author: Sensor Data Collector Team
"""

import httpx
import io
from datetime import datetime, timezone
from typing import Optional

from app.models import PurpleAirReading


class PurpleAirService:
    """
    Service for Purple Air sensor operations.
    
    This class is instantiated once at application startup and shared
    across all requests. It maintains a persistent HTTP client for
    efficient connection reuse.
    
    Usage:
        service = PurpleAirService(
            external_endpoint_url="https://example.com/upload",
            external_endpoint_token="your-token"
        )
        
        # Fetch and push in one call
        result = await service.fetch_and_push("192.168.1.100", "My Sensor")
        
        # Or step by step
        raw_data = await service.fetch_sensor_data("192.168.1.100")
        reading = service.parse_sensor_response(raw_data)
        csv_data = service.convert_to_csv(reading)
        result = await service.push_to_endpoint(csv_data, "My Sensor")
    """
    
    def __init__(
        self, 
        external_endpoint_url: str, 
        external_endpoint_token: str,
        request_timeout: float = 10.0
    ):
        """
        Initialize the Purple Air service.
        
        Args:
            external_endpoint_url: URL to push CSV data to
            external_endpoint_token: Bearer token for authentication
            request_timeout: HTTP request timeout in seconds
        """
        self.external_endpoint_url = external_endpoint_url
        self.external_endpoint_token = external_endpoint_token
        self.http_client = httpx.AsyncClient(timeout=request_timeout)
    
    async def fetch_sensor_data(self, ip_address: str) -> dict:
        """
        Fetch JSON data from a Purple Air sensor via its local IP.
        
        Purple Air sensors expose their data at http://<ip>/json
        The response contains all current readings.
        
        Args:
            ip_address: Local IP address (e.g., "192.168.1.100")
            
        Returns:
            Raw JSON response as dictionary
            
        Raises:
            httpx.ConnectError: Sensor unreachable
            httpx.TimeoutException: Request timed out
            httpx.HTTPStatusError: Non-2xx response
            
        Example Response:
            {
                "SensorId": "84:f3:eb:xx:xx:xx",
                "DateTime": "2026/01/05T22:26:50z",
                "Geo": "...",
                "Mem": 18000,
                "memfrag": 14,
                "memfb": 14880,
                "memcs": 800,
                "Id": 12345,
                "lat": 41.29,
                "lon": -82.22,
                "Adc": 0.05,
                "loggingrate": 15,
                "place": "outside",
                "version": "7.02",
                "uptime": 1234567,
                "rssi": -55,
                "period": 120,
                "httpsuccess": 1000,
                "httpsends": 1001,
                "hardwareversion": "3.0",
                "hardwarediscovered": "3.0+BME280+PMSX003-B+PMSX003-A",
                "current_temp_f": 40,
                "current_humidity": 62,
                "current_dewpoint_f": 28,
                "pressure": 985.09,
                "p25aqic_b": "82",
                "pm2.5_aqi_b": 82,
                "pm1_0_cf_1": 15.82,
                "pm1_0_cf_1_b": 16.01,
                "p_0_3_um": 3912.45,
                "p_0_3_um_b": 4011.33,
                "pm2_5_cf_1": 26.49,
                "pm2_5_cf_1_b": 27.11,
                "p_0_5_um": 1089.12,
                "p_0_5_um_b": 1102.45,
                "pm10_0_cf_1": 33.05,
                "pm10_0_cf_1_b": 34.22,
                "p_1_0_um": 211.34,
                "p_1_0_um_b": 215.67,
                "pm1_0_atm": 15.82,
                "pm1_0_atm_b": 16.01,
                "p_2_5_um": 33.45,
                "p_2_5_um_b": 35.12,
                "pm2_5_atm": 26.49,
                "pm2_5_atm_b": 27.11,
                "p_5_0_um": 5.67,
                "p_5_0_um_b": 6.01,
                "pm10_0_atm": 33.05,
                "pm10_0_atm_b": 34.22,
                "p_10_0_um": 1.23,
                "p_10_0_um_b": 1.45,
                "pa_latency": 234,
                "wlstate": "Connected",
                "status_0": 2,
                "status_1": 2,
                "status_2": 2,
                "status_5": 2,
                "status_6": 0,
                "ssid": "NetworkName"
            }
        """
        url = f"http://{ip_address}/json"
        
        response = await self.http_client.get(url)
        response.raise_for_status()
        
        return response.json()
    
    def parse_sensor_response(self, raw_data: dict) -> PurpleAirReading:
        """
        Parse raw Purple Air JSON into a structured reading.
        
        Extracts the key fields we need and converts them to
        proper types. Handles missing fields gracefully.
        
        Args:
            raw_data: Raw JSON from fetch_sensor_data()
            
        Returns:
            PurpleAirReading with validated data
            
        Field Mapping:
            JSON Field          -> Model Field
            ----------------------------------------
            DateTime            -> timestamp
            current_temp_f      -> temperature_f
            current_humidity    -> humidity_percent
            current_dewpoint_f  -> dewpoint_f
            pressure            -> pressure_hpa
            pm1_0_cf_1         -> pm1_0_cf1
            pm2_5_cf_1         -> pm2_5_cf1
            pm10_0_cf_1        -> pm10_0_cf1
            pm2.5_aqi          -> pm2_5_aqi
        """
        # Parse timestamp
        timestamp_str = raw_data.get("DateTime")
        if timestamp_str:
            # Purple Air format: "2026/01/05T22:26:50z"
            # Convert to ISO format for parsing
            try:
                clean_ts = timestamp_str.replace("/", "-").replace("z", "+00:00")
                timestamp = datetime.fromisoformat(clean_ts)
            except ValueError:
                timestamp = datetime.now(timezone.utc)
        else:
            timestamp = datetime.now(timezone.utc)
        
        # Extract readings with defaults for missing values
        return PurpleAirReading(
            timestamp=timestamp,
            temperature_f=float(raw_data.get("current_temp_f", 0)),
            humidity_percent=float(raw_data.get("current_humidity", 0)),
            dewpoint_f=float(raw_data.get("current_dewpoint_f", 0)),
            pressure_hpa=float(raw_data.get("pressure", 0)),
            pm1_0_cf1=float(raw_data.get("pm1_0_cf_1", 0)),
            pm2_5_cf1=float(raw_data.get("pm2_5_cf_1", 0)),
            pm10_0_cf1=float(raw_data.get("pm10_0_cf_1", 0)),
            pm2_5_aqi=int(raw_data.get("pm2.5_aqi", raw_data.get("pm2_5_aqi", 0)))
        )
    
    def convert_to_csv(
        self, 
        reading: PurpleAirReading, 
        include_header: bool = True
    ) -> str:
        """
        Convert a Purple Air reading to CSV format.
        
        Args:
            reading: Parsed sensor reading
            include_header: Whether to include header row
            
        Returns:
            CSV formatted string
            
        Output Format:
            Timestamp,Temperature (°F),Humidity (%),Dewpoint (°F),Pressure (hPa),PM1.0 :cf_1( µg/m³),PM2.5 :cf_1( µg/m³),PM10.0 :cf_1( µg/m³),PM2.5 AQI
            2026-01-05T22:26:50+00:00,40,62,28,985.09,15.82,26.49,33.05,82
        """
        lines = []
        
        if include_header:
            lines.append(PurpleAirReading.csv_header())
        
        lines.append(reading.to_csv_row())
        
        return "\n".join(lines)
    
    async def push_to_endpoint(
        self, 
        csv_data: str, 
        sensor_name: str
    ) -> dict:
        """
        Push CSV data to the external endpoint.
        
        Uploads the CSV as a file using multipart/form-data.
        
        Args:
            csv_data: CSV string to upload
            sensor_name: Used to generate filename
            
        Returns:
            Dict with upload result:
            {
                "status": "success",
                "filename": "sensor_name_20260105_222650.csv",
                "uploaded_at": "2026-01-05T22:26:50+00:00"
            }
            
        Raises:
            httpx.HTTPStatusError: Upload failed
        """
        headers = {
            "Authorization": f"Bearer {self.external_endpoint_token}"
        }
        
        # Generate filename with timestamp
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        # Clean sensor name for filename (replace spaces, special chars)
        clean_name = "".join(c if c.isalnum() else "_" for c in sensor_name)
        filename = f"{clean_name}_{timestamp}.csv"
        
        # Create file-like object
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
        sensor_name: str
    ) -> dict:
        """
        Complete workflow: Fetch → Parse → Convert → Push.
        
        This is the main method called by the scheduler every minute.
        It handles the entire data pipeline in one call.
        
        Args:
            ip_address: Local IP of the Purple Air sensor
            sensor_name: Name for logging and filename
            
        Returns:
            Result dict:
            {
                "status": "success" | "error",
                "sensor_name": "...",
                "reading": {...},        # If successful
                "upload_result": {...},  # If successful
                "error_type": "...",     # If error
                "error_message": "..."   # If error
            }
        """
        try:
            # Step 1: Fetch from sensor
            raw_data = await self.fetch_sensor_data(ip_address)
            
            # Step 2: Parse response
            reading = self.parse_sensor_response(raw_data)
            
            # Step 3: Convert to CSV
            csv_data = self.convert_to_csv(reading, include_header=True)
            
            # Step 4: Push to endpoint
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
                "error_message": f"Cannot connect to sensor at {ip_address}: {str(e)}"
            }
        except httpx.TimeoutException:
            return {
                "status": "error",
                "sensor_name": sensor_name,
                "error_type": "timeout",
                "error_message": f"Request to sensor at {ip_address} timed out"
            }
        except httpx.HTTPStatusError as e:
            return {
                "status": "error",
                "sensor_name": sensor_name,
                "error_type": "http_error",
                "error_message": f"HTTP error: {e.response.status_code}"
            }
        except Exception as e:
            return {
                "status": "error",
                "sensor_name": sensor_name,
                "error_type": "unknown_error",
                "error_message": str(e)
            }
    
    async def close(self):
        """Close the HTTP client. Call this on application shutdown."""
        await self.http_client.aclose()

=========================
Complete implementation for Purple Air sensor operations.

This service handles the full data pipeline:
1. Fetch JSON data from Purple Air sensor via local IP
2. Parse and validate the response
3. Convert to CSV format
4. Push CSV to external endpoint

PURPLE AIR LOCAL API:
    Purple Air sensors on the local network expose their data at:
    http://<sensor_ip>/json
    
    This returns a JSON object with all sensor readings.
    No authentication required for local access.

EXTERNAL ENDPOINT:
    CSV data is pushed to:
    https://oberlin.communityhub.cloud/api/data-hub/upload/csv
    
    Authentication: Bearer token in Authorization header

Author: Sensor Data Collector Team
"""

import httpx
import io
from datetime import datetime, timezone
from typing import Optional

from app.models import PurpleAirReading


class PurpleAirService:
    """
    Service for Purple Air sensor operations.
    
    This class is instantiated once at application startup and shared
    across all requests. It maintains a persistent HTTP client for
    efficient connection reuse.
    
    Usage:
        service = PurpleAirService(
            external_endpoint_url="https://example.com/upload",
            external_endpoint_token="your-token"
        )
        
        # Fetch and push in one call
        result = await service.fetch_and_push("192.168.1.100", "My Sensor")
        
        # Or step by step
        raw_data = await service.fetch_sensor_data("192.168.1.100")
        reading = service.parse_sensor_response(raw_data)
        csv_data = service.convert_to_csv(reading)
        result = await service.push_to_endpoint(csv_data, "My Sensor")
    """
    
    def __init__(
        self, 
        external_endpoint_url: str, 
        external_endpoint_token: str,
        request_timeout: float = 10.0
    ):
        """
        Initialize the Purple Air service.
        
        Args:
            external_endpoint_url: URL to push CSV data to
            external_endpoint_token: Bearer token for authentication
            request_timeout: HTTP request timeout in seconds
        """
        self.external_endpoint_url = external_endpoint_url
        self.external_endpoint_token = external_endpoint_token
        self.http_client = httpx.AsyncClient(timeout=request_timeout)
    
    async def fetch_sensor_data(self, ip_address: str) -> dict:
        """
        Fetch JSON data from a Purple Air sensor via its local IP.
        
        Purple Air sensors expose their data at http://<ip>/json
        The response contains all current readings.
        
        Args:
            ip_address: Local IP address (e.g., "192.168.1.100")
            
        Returns:
            Raw JSON response as dictionary
            
        Raises:
            httpx.ConnectError: Sensor unreachable
            httpx.TimeoutException: Request timed out
            httpx.HTTPStatusError: Non-2xx response
            
        Example Response:
            {
                "SensorId": "84:f3:eb:xx:xx:xx",
                "DateTime": "2026/01/05T22:26:50z",
                "Geo": "...",
                "Mem": 18000,
                "memfrag": 14,
                "memfb": 14880,
                "memcs": 800,
                "Id": 12345,
                "lat": 41.29,
                "lon": -82.22,
                "Adc": 0.05,
                "loggingrate": 15,
                "place": "outside",
                "version": "7.02",
                "uptime": 1234567,
                "rssi": -55,
                "period": 120,
                "httpsuccess": 1000,
                "httpsends": 1001,
                "hardwareversion": "3.0",
                "hardwarediscovered": "3.0+BME280+PMSX003-B+PMSX003-A",
                "current_temp_f": 40,
                "current_humidity": 62,
                "current_dewpoint_f": 28,
                "pressure": 985.09,
                "p25aqic_b": "82",
                "pm2.5_aqi_b": 82,
                "pm1_0_cf_1": 15.82,
                "pm1_0_cf_1_b": 16.01,
                "p_0_3_um": 3912.45,
                "p_0_3_um_b": 4011.33,
                "pm2_5_cf_1": 26.49,
                "pm2_5_cf_1_b": 27.11,
                "p_0_5_um": 1089.12,
                "p_0_5_um_b": 1102.45,
                "pm10_0_cf_1": 33.05,
                "pm10_0_cf_1_b": 34.22,
                "p_1_0_um": 211.34,
                "p_1_0_um_b": 215.67,
                "pm1_0_atm": 15.82,
                "pm1_0_atm_b": 16.01,
                "p_2_5_um": 33.45,
                "p_2_5_um_b": 35.12,
                "pm2_5_atm": 26.49,
                "pm2_5_atm_b": 27.11,
                "p_5_0_um": 5.67,
                "p_5_0_um_b": 6.01,
                "pm10_0_atm": 33.05,
                "pm10_0_atm_b": 34.22,
                "p_10_0_um": 1.23,
                "p_10_0_um_b": 1.45,
                "pa_latency": 234,
                "wlstate": "Connected",
                "status_0": 2,
                "status_1": 2,
                "status_2": 2,
                "status_5": 2,
                "status_6": 0,
                "ssid": "NetworkName"
            }
        """
        url = f"http://{ip_address}/json"
        
        response = await self.http_client.get(url)
        response.raise_for_status()
        
        return response.json()
    
    def parse_sensor_response(self, raw_data: dict) -> PurpleAirReading:
        """
        Parse raw Purple Air JSON into a structured reading.
        
        Extracts the key fields we need and converts them to
        proper types. Handles missing fields gracefully.
        
        Args:
            raw_data: Raw JSON from fetch_sensor_data()
            
        Returns:
            PurpleAirReading with validated data
            
        Field Mapping:
            JSON Field          -> Model Field
            ----------------------------------------
            DateTime            -> timestamp
            current_temp_f      -> temperature_f
            current_humidity    -> humidity_percent
            current_dewpoint_f  -> dewpoint_f
            pressure            -> pressure_hpa
            pm1_0_cf_1         -> pm1_0_cf1
            pm2_5_cf_1         -> pm2_5_cf1
            pm10_0_cf_1        -> pm10_0_cf1
            pm2.5_aqi          -> pm2_5_aqi
        """
        # Parse timestamp
        timestamp_str = raw_data.get("DateTime")
        if timestamp_str:
            # Purple Air format: "2026/01/05T22:26:50z"
            # Convert to ISO format for parsing
            try:
                clean_ts = timestamp_str.replace("/", "-").replace("z", "+00:00")
                timestamp = datetime.fromisoformat(clean_ts)
            except ValueError:
                timestamp = datetime.now(timezone.utc)
        else:
            timestamp = datetime.now(timezone.utc)
        
        # Extract readings with defaults for missing values
        return PurpleAirReading(
            timestamp=timestamp,
            temperature_f=float(raw_data.get("current_temp_f", 0)),
            humidity_percent=float(raw_data.get("current_humidity", 0)),
            dewpoint_f=float(raw_data.get("current_dewpoint_f", 0)),
            pressure_hpa=float(raw_data.get("pressure", 0)),
            pm1_0_cf1=float(raw_data.get("pm1_0_cf_1", 0)),
            pm2_5_cf1=float(raw_data.get("pm2_5_cf_1", 0)),
            pm10_0_cf1=float(raw_data.get("pm10_0_cf_1", 0)),
            pm2_5_aqi=int(raw_data.get("pm2.5_aqi", raw_data.get("pm2_5_aqi", 0)))
        )
    
    def convert_to_csv(
        self, 
        reading: PurpleAirReading, 
        include_header: bool = True
    ) -> str:
        """
        Convert a Purple Air reading to CSV format.
        
        Args:
            reading: Parsed sensor reading
            include_header: Whether to include header row
            
        Returns:
            CSV formatted string
            
        Output Format:
            Timestamp,Temperature (°F),Humidity (%),Dewpoint (°F),Pressure (hPa),PM1.0 :cf_1( µg/m³),PM2.5 :cf_1( µg/m³),PM10.0 :cf_1( µg/m³),PM2.5 AQI
            2026-01-05T22:26:50+00:00,40,62,28,985.09,15.82,26.49,33.05,82
        """
        lines = []
        
        if include_header:
            lines.append(PurpleAirReading.csv_header())
        
        lines.append(reading.to_csv_row())
        
        return "\n".join(lines)
    
    async def push_to_endpoint(
        self, 
        csv_data: str, 
        sensor_name: str
    ) -> dict:
        """
        Push CSV data to the external endpoint.
        
        Uploads the CSV as a file using multipart/form-data.
        
        Args:
            csv_data: CSV string to upload
            sensor_name: Used to generate filename
            
        Returns:
            Dict with upload result:
            {
                "status": "success",
                "filename": "sensor_name_20260105_222650.csv",
                "uploaded_at": "2026-01-05T22:26:50+00:00"
            }
            
        Raises:
            httpx.HTTPStatusError: Upload failed
        """
        headers = {
            "Authorization": f"Bearer {self.external_endpoint_token}"
        }
        
        # Generate filename with timestamp
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        # Clean sensor name for filename (replace spaces, special chars)
        clean_name = "".join(c if c.isalnum() else "_" for c in sensor_name)
        filename = f"{clean_name}_{timestamp}.csv"
        
        # Create file-like object
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
        sensor_name: str
    ) -> dict:
        """
        Complete workflow: Fetch → Parse → Convert → Push.
        
        This is the main method called by the scheduler every minute.
        It handles the entire data pipeline in one call.
        
        Args:
            ip_address: Local IP of the Purple Air sensor
            sensor_name: Name for logging and filename
            
        Returns:
            Result dict:
            {
                "status": "success" | "error",
                "sensor_name": "...",
                "reading": {...},        # If successful
                "upload_result": {...},  # If successful
                "error_type": "...",     # If error
                "error_message": "..."   # If error
            }
        """
        try:
            # Step 1: Fetch from sensor
            raw_data = await self.fetch_sensor_data(ip_address)
            
            # Step 2: Parse response
            reading = self.parse_sensor_response(raw_data)
            
            # Step 3: Convert to CSV
            csv_data = self.convert_to_csv(reading, include_header=True)
            
            # Step 4: Push to endpoint
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
                "error_message": f"Cannot connect to sensor at {ip_address}: {str(e)}"
            }
        except httpx.TimeoutException:
            return {
                "status": "error",
                "sensor_name": sensor_name,
                "error_type": "timeout",
                "error_message": f"Request to sensor at {ip_address} timed out"
            }
        except httpx.HTTPStatusError as e:
            return {
                "status": "error",
                "sensor_name": sensor_name,
                "error_type": "http_error",
                "error_message": f"HTTP error: {e.response.status_code}"
            }
        except Exception as e:
            return {
                "status": "error",
                "sensor_name": sensor_name,
                "error_type": "unknown_error",
                "error_message": str(e)
            }
    
    async def close(self):
        """Close the HTTP client. Call this on application shutdown."""
        await self.http_client.aclose()
