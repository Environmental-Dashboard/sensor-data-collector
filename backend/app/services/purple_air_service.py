"""
Purple Air Sensor Service
=========================

Yo! This is the brains for Purple Air sensors.

WHAT THIS DOES:
--------------
1. Connects to Purple Air sensors on your local network
2. Grabs the air quality data (temperature, humidity, PM2.5, etc.)
3. Converts it to a CSV file
4. Uploads it to the cloud

HOW PURPLE AIR WORKS:
--------------------
Purple Air sensors have a local API. If your sensor is at IP 192.168.1.100,
you can get its data by going to: http://192.168.1.100/json

No password needed - as long as you're on the same network as the sensor!

THE DATA FLOW:
-------------
    Purple Air Sensor (192.168.1.100)
            |
            | GET /json
            v
    [This Service Gets JSON Data]
            |
            | Parse & Convert
            v
    [CSV File Created]
            |
            | POST with token
            v
    [oberlin.communityhub.cloud]

Author: Frank Kusi Appiah
"""

import httpx
import io
import logging
from datetime import datetime, timezone

from app.models import PurpleAirReading

logger = logging.getLogger(__name__)


# =============================================================================
# THE MAIN SERVICE CLASS
# =============================================================================

class PurpleAirService:
    """
    This class handles everything for Purple Air sensors.
    
    HOW TO USE:
    ----------
    # Create the service (done automatically at startup)
    service = PurpleAirService()
    
    # Fetch data and upload it
    result = await service.fetch_and_push(
        ip_address="10.17.192.162",
        sensor_name="Lab Sensor",
        upload_token="your-token-here"
    )
    
    # Check if it worked
    if result["status"] == "success":
        print("Data uploaded!")
        print(result["reading"])  # The actual data
    else:
        print("Something went wrong:", result["error_message"])
    """
    
    # The real upload URL - where data goes to be stored
    UPLOAD_URL = "https://oberlin.communityhub.cloud/api/data-hub/upload/csv"
    
    def __init__(self, request_timeout: float = 30.0):
        """
        Set up the service.
        
        Args:
            request_timeout: How long to wait for sensor/upload responses (seconds)
                            Default is 30 seconds - increase if your network is slow.
        """
        # This is our HTTP client - we use it to make web requests
        # We keep one around so connections can be reused (faster!)
        self.http_client = httpx.AsyncClient(timeout=request_timeout)
    
    
    async def fetch_sensor_data(self, ip_address: str) -> dict:
        """
        Get data from a Purple Air sensor.
        
        This connects to the sensor's local web server and grabs the JSON data.
        
        Args:
            ip_address: The sensor's IP on your network (like "10.17.192.162")
        
        Returns:
            A dictionary with all the sensor data
        
        Example return value:
            {
                "current_temp_f": 72,
                "current_humidity": 45,
                "pm2_5_cf_1": 12.5,
                "pm2.5_aqi": 52,
                ...
            }
        
        What could go wrong:
            - Sensor is off or unplugged
            - Wrong IP address
            - Sensor is on a different network
            - Firewall blocking the connection
        """
        # Purple Air sensors serve their data at /json
        url = f"http://{ip_address}/json"
        
        # Make the request
        response = await self.http_client.get(url)
        
        # Make sure it worked (raises error if not)
        response.raise_for_status()
        
        # Parse the JSON and return it
        return response.json()
    
    
    def parse_sensor_response(self, raw_data: dict) -> PurpleAirReading:
        """
        Take the raw JSON from the sensor and turn it into clean data.
        
        The sensor returns a LOT of data. We only care about certain fields.
        This function extracts what we need and puts it in a nice format.
        
        Args:
            raw_data: The raw JSON from fetch_sensor_data()
        
        Returns:
            A PurpleAirReading with just the data we care about
        """
        # Try to get the timestamp from the sensor
        # Purple Air uses a weird format: "2026/01/05T22:26:50z"
        timestamp_str = raw_data.get("DateTime")
        if timestamp_str:
            try:
                # Convert their format to standard format
                clean_ts = timestamp_str.replace("/", "-").replace("z", "+00:00")
                timestamp = datetime.fromisoformat(clean_ts)
            except ValueError:
                # If parsing fails, just use current time
                timestamp = datetime.now(timezone.utc)
        else:
            timestamp = datetime.now(timezone.utc)
        
        # Extract the values we care about
        # .get() returns 0 if the field is missing
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
    
    
    def convert_to_csv(self, reading: PurpleAirReading, include_header: bool = True) -> str:
        """
        Convert a reading to CSV format.
        
        CSV = Comma Separated Values
        It's a simple text format that spreadsheet programs can open.
        
        Format matches Community Hub requirements:
        - Header row with column names
        - Data rows (one per reading)
        - Unix line endings (\n)
        - No trailing newline
        
        Args:
            reading: The data to convert
            include_header: Add column names at the top? (usually yes)
        
        Returns:
            A string like:
            "Timestamp,Temperature (°F),Humidity (%),..."
            "2026-01-06T03:00:00,72,45,..."
        """
        lines = []
        
        if include_header:
            lines.append(PurpleAirReading.csv_header())
        
        lines.append(reading.to_csv_row())
        
        # Join with \n and ensure no trailing newline (matches Community Hub format)
        csv_content = "\n".join(lines)
        # Remove any trailing whitespace/newlines
        return csv_content.rstrip()
    
    
    async def push_to_endpoint(self, csv_data: str, sensor_name: str, upload_token: str) -> dict:
        """
        Upload the CSV data to the cloud.
        
        This sends the data to oberlin.communityhub.cloud where it gets stored.
        
        Args:
            csv_data: The CSV string to upload
            sensor_name: Used to name the file
            upload_token: Your authentication token (proves you're allowed to upload)
        
        Returns:
            Info about the upload:
            {
                "status": "success",
                "filename": "Lab_Sensor_20260106_030000.csv",
                "uploaded_at": "2026-01-06T03:00:01"
            }
        """
        # Validate CSV before upload
        if not csv_data or not csv_data.strip():
            error_msg = "CSV data is empty - cannot upload"
            logger.error(f"[{sensor_name}] {error_msg}")
            raise ValueError(error_msg)
        
        # Count rows (header + data)
        row_count = len([line for line in csv_data.split('\n') if line.strip()])
        csv_size = len(csv_data.encode('utf-8'))
        
        # Log CSV preview (first 500 chars) for debugging
        csv_preview = csv_data[:500] + "..." if len(csv_data) > 500 else csv_data
        logger.info(f"[{sensor_name}] Uploading CSV - Size: {csv_size} bytes, Rows: {row_count}")
        logger.info(f"[{sensor_name}] CSV content (full):\n{csv_data}")
        logger.debug(f"[{sensor_name}] CSV preview:\n{csv_preview}")
        
        # Set up the authentication header
        # The API expects "user-token" header (not Bearer token)
        headers = {
            "user-token": upload_token
        }
        
        # Create a filename with the sensor name and timestamp
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        # Clean the sensor name (remove spaces and special characters)
        clean_name = "".join(c if c.isalnum() else "_" for c in sensor_name)
        filename = f"{clean_name}_{timestamp}.csv"
        
        # Encode CSV as UTF-8 for upload
        csv_bytes = csv_data.encode("utf-8")
        
        # Verify file is not empty
        if len(csv_bytes) == 0:
            error_msg = "CSV bytes are empty after encoding"
            logger.error(f"[{sensor_name}] {error_msg}")
            raise ValueError(error_msg)
        
        # Log the actual bytes being sent (first 200 bytes)
        logger.debug(f"[{sensor_name}] CSV bytes (first 200): {csv_bytes[:200]}")
        logger.debug(f"[{sensor_name}] CSV bytes length: {len(csv_bytes)}")
        
        # Upload as RAW BODY (not multipart form data!)
        # Community Hub expects: Content-Type: text/csv with raw CSV in body
        upload_headers = {
            "user-token": upload_token,
            "Content-Type": "text/csv"
        }
        
        try:
            # Log request details
            logger.debug(f"[{sensor_name}] Uploading to: {self.UPLOAD_URL}")
            logger.debug(f"[{sensor_name}] File size: {len(csv_bytes)} bytes")
            
            response = await self.http_client.post(
                self.UPLOAD_URL,
                headers=upload_headers,
                content=csv_bytes  # Raw body, not multipart
            )
            response.raise_for_status()
            
            logger.info(f"[{sensor_name}] Upload successful - Status: {response.status_code}, File: {filename}")
            
            return {
                "status": "success",
                "filename": filename,
                "uploaded_at": datetime.now(timezone.utc).isoformat(),
                "csv_size_bytes": csv_size,
                "row_count": row_count
            }
        except httpx.HTTPStatusError as e:
            # Log detailed error information
            error_body = ""
            try:
                error_body = e.response.text[:500]  # First 500 chars of error response
            except:
                pass
            
            logger.error(
                f"[{sensor_name}] Upload failed - HTTP {e.response.status_code}\n"
                f"Response: {error_body}\n"
                f"CSV preview: {csv_preview}"
            )
            raise
        except Exception as e:
            logger.error(f"[{sensor_name}] Upload error: {str(e)}\nCSV preview: {csv_preview}")
            raise
    
    
    async def fetch_and_push(self, ip_address: str, sensor_name: str, upload_token: str) -> dict:
        """
        THE MAIN FUNCTION - Do everything in one call!
        
        This is what gets called every 60 seconds for each active sensor.
        It does the whole pipeline:
        1. Fetch data from sensor
        2. Parse the data
        3. Convert to CSV
        4. Upload to cloud
        
        Args:
            ip_address: Sensor's IP (like "10.17.192.162")
            sensor_name: What we call it (like "Lab Sensor")
            upload_token: Your cloud token
        
        Returns:
            If it worked:
            {
                "status": "success",
                "sensor_name": "Lab Sensor",
                "reading": {temperature: 72, humidity: 45, ...},
                "upload_result": {filename: "...", uploaded_at: "..."}
            }
            
            If it failed:
            {
                "status": "error",
                "sensor_name": "Lab Sensor",
                "error_type": "connection_error",
                "error_message": "Cannot connect to sensor at 10.17.192.162"
            }
        """
        try:
            # Step 1: Fetch from sensor
            raw_data = await self.fetch_sensor_data(ip_address)
            
            # Step 2: Parse the response
            reading = self.parse_sensor_response(raw_data)
            
            # Step 3: Convert to CSV
            csv_data = self.convert_to_csv(reading, include_header=True)
            
            # Step 4: Upload to cloud (returns CSV sample in result)
            upload_result = await self.push_to_endpoint(csv_data, sensor_name, upload_token)
            # Store CSV sample in upload result for diagnostics
            upload_result["csv_sample"] = csv_data[:500]  # First 500 chars
            
            # All good!
            return {
                "status": "success",
                "sensor_name": sensor_name,
                "reading": reading.model_dump(),
                "upload_result": upload_result
            }
            
        except httpx.ConnectError as e:
            # Couldn't connect to the sensor
            return {
                "status": "error",
                "sensor_name": sensor_name,
                "error_type": "connection_error",
                "error_message": f"Cannot connect to sensor at {ip_address}. Is it on? Is the IP right? Error: {str(e)}"
            }
        except httpx.TimeoutException:
            # Took too long
            return {
                "status": "error",
                "sensor_name": sensor_name,
                "error_type": "timeout",
                "error_message": f"Request to sensor at {ip_address} timed out. Network might be slow or sensor is unresponsive."
            }
        except httpx.HTTPStatusError as e:
            # Got a response but it was an error
            error_body = ""
            try:
                error_body = e.response.text[:500]
            except:
                pass
            
            error_msg = f"HTTP error {e.response.status_code}"
            if error_body:
                error_msg += f": {error_body}"
            else:
                error_msg += ". Check if the upload token is correct."
            
            logger.error(f"[{sensor_name}] Upload HTTP error: {error_msg}")
            
            return {
                "status": "error",
                "sensor_name": sensor_name,
                "error_type": "http_error",
                "error_message": error_msg,
                "http_status": e.response.status_code,
                "error_response": error_body
            }
        except Exception as e:
            # Something else went wrong
            return {
                "status": "error",
                "sensor_name": sensor_name,
                "error_type": "unknown_error",
                "error_message": str(e)
            }
    
    
    async def close(self):
        """
        Clean up when we're done.
        
        Called when the server shuts down.
        """
        await self.http_client.aclose()
