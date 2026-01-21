"""
Water Quality Sensor Service
============================

This service fetches water quality data from Ubidots IoT platform.

To get your credentials:
1. Go to https://freeboardtech.iot.ubidots.com/
2. Log in with your account
3. Find your device ID and API token

Author: Sensor Dashboard Team
"""

import httpx
import io
import logging
from datetime import datetime, timezone
from typing import Optional

from app.models import WaterQualityReading

logger = logging.getLogger(__name__)


class WaterQualityService:
    """Handles fetching water quality data from Ubidots."""
    
    UBIDOTS_API_URL = "https://industrial.api.ubidots.com/api/v2.0"
    UPLOAD_URL = "https://oberlin.communityhub.cloud/api/data-hub/upload/csv"
    
    def __init__(self, request_timeout: float = 30.0):
        self.http_client = httpx.AsyncClient(timeout=request_timeout)
    
    async def fetch_device_info(self, device_id: str, ubidots_token: str) -> dict:
        """Get device information from Ubidots."""
        url = f"{self.UBIDOTS_API_URL}/devices/{device_id}/"
        headers = {"X-Auth-Token": ubidots_token}
        response = await self.http_client.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    
    async def fetch_variables(self, device_id: str, ubidots_token: str) -> list:
        """Get all variables (sensor readings) for a device."""
        url = f"{self.UBIDOTS_API_URL}/devices/{device_id}/variables"
        headers = {"X-Auth-Token": ubidots_token}
        response = await self.http_client.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        return data.get("results", [])
    
    def parse_variables_to_reading(self, variables: list) -> WaterQualityReading:
        """Convert Ubidots variables to a WaterQualityReading."""
        var_lookup = {}
        latest_timestamp = None
        
        for var in variables:
            label = var.get("label", "")
            last_value = var.get("lastValue", {})
            if last_value:
                var_lookup[label] = last_value.get("value")
                ts = last_value.get("timestamp")
                if ts and (latest_timestamp is None or ts > latest_timestamp):
                    latest_timestamp = ts
        
        if latest_timestamp:
            timestamp = datetime.fromtimestamp(latest_timestamp / 1000, tz=timezone.utc)
        else:
            timestamp = datetime.now(timezone.utc)
        
        return WaterQualityReading(
            timestamp=timestamp,
            water_temp_c=float(var_lookup.get("wtemp", 0) or 0),
            dissolved_oxygen_mgl=float(var_lookup.get("do", 0) or 0),
            dissolved_oxygen_sat=float(var_lookup.get("dosat", 0) or 0),
            specific_conductivity=float(var_lookup.get("spcond", 0) or 0),
            turbidity_ntu=float(var_lookup.get("turb", 0) or 0),
            water_level_m=float(var_lookup.get("distance", 0) or 0),
            battery_voltage=float(var_lookup.get("vbat", 0) or 0),
            enclosure_temp_c=float(var_lookup.get("enctemp", 0) or 0),
            enclosure_humidity=float(var_lookup.get("encrh", 0) or 0),
        )
    
    def convert_to_csv(self, reading: WaterQualityReading, include_header: bool = True) -> str:
        """Convert a reading to CSV format."""
        lines = []
        if include_header:
            lines.append(WaterQualityReading.csv_header())
        lines.append(reading.to_csv_row())
        return "\n".join(lines)
    
    async def push_to_endpoint(self, csv_data: str, sensor_name: str, upload_token: str) -> dict:
        """Upload the CSV data to the community hub cloud."""
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
        logger.debug(f"[{sensor_name}] CSV preview:\n{csv_preview}")
        
        headers = {"user-token": upload_token}
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        clean_name = "".join(c if c.isalnum() else "_" for c in sensor_name)
        filename = f"WQ_{clean_name}_{timestamp}.csv"
        
        csv_bytes = csv_data.encode("utf-8")
        
        # Upload as RAW BODY (not multipart form data!)
        # Community Hub expects: Content-Type: text/csv with raw CSV in body
        upload_headers = {
            "user-token": upload_token,
            "Content-Type": "text/csv"
        }
        
        try:
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
                error_body = e.response.text[:500]
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
    
    async def fetch_and_push(self, device_id: str, ubidots_token: str, sensor_name: str, upload_token: str) -> dict:
        """Fetch from Ubidots and upload to cloud."""
        try:
            variables = await self.fetch_variables(device_id, ubidots_token)
            if not variables:
                return {"status": "error", "sensor_name": sensor_name, "error_type": "no_data", "error_message": "No variables found"}
            
            reading = self.parse_variables_to_reading(variables)
            csv_data = self.convert_to_csv(reading, include_header=True)
            upload_result = await self.push_to_endpoint(csv_data, sensor_name, upload_token)
            
            return {"status": "success", "sensor_name": sensor_name, "reading": reading.model_dump(), "upload_result": upload_result}
        except httpx.HTTPStatusError as e:
            error_body = ""
            try:
                error_body = e.response.text[:500]
            except:
                pass
            
            if e.response.status_code == 401:
                error_msg = "Invalid Ubidots token"
            elif e.response.status_code == 404:
                error_msg = "Device not found"
            else:
                error_msg = f"HTTP error {e.response.status_code}"
                if error_body:
                    error_msg += f": {error_body}"
            
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
            return {"status": "error", "sensor_name": sensor_name, "error_type": "unknown_error", "error_message": str(e)}
    
    async def test_connection(self, device_id: str, ubidots_token: str) -> dict:
        """Test if we can connect to a device."""
        try:
            device_info = await self.fetch_device_info(device_id, ubidots_token)
            variables = await self.fetch_variables(device_id, ubidots_token)
            return {
                "status": "success",
                "device_name": device_info.get("name", "Unknown"),
                "variables_count": len(variables),
                "is_active": device_info.get("isActive", False)
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    async def close(self):
        """Clean up when done."""
        await self.http_client.aclose()
