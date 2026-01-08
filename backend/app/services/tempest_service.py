"""
Tempest Weather Station Service

Connects to the WeatherFlow Tempest Cloud API via WebSocket to receive
real-time weather data and push it to the Community Hub.

API Documentation: https://weatherflow.github.io/Tempest/api/
WebSocket Reference: https://weatherflow.github.io/Tempest/api/ws.html

Authentication:
- Get your Personal Access Token from https://tempestwx.com/settings/tokens
- One token works for all your Tempest devices
"""

import asyncio
import json
import io
from datetime import datetime, timezone
from typing import Callable, Optional
import httpx

try:
    import websockets
except ImportError:
    websockets = None


from app.models import TempestReading


class TempestService:
    """
    Service for receiving real-time data from Tempest weather stations.
    
    Uses WebSocket connection to WeatherFlow cloud to listen for data.
    When data arrives, it's immediately parsed and uploaded to Community Hub.
    """
    
    WEBSOCKET_URL = "wss://ws.weatherflow.com/swd/data"
    REST_API_URL = "https://swd.weatherflow.com/swd/rest"
    UPLOAD_URL = "https://oberlin.communityhub.cloud/api/data-hub/upload/csv"
    
    def __init__(self, request_timeout: float = 30.0):
        self.http_client = httpx.AsyncClient(timeout=request_timeout)
        self._listeners: dict[str, asyncio.Task] = {}  # device_id -> task
        self._stop_events: dict[str, asyncio.Event] = {}  # device_id -> stop event
    
    def start_listener(
        self,
        device_id: str,
        api_token: str,
        upload_token: str,
        sensor_name: str,
        on_data_callback: Callable
    ):
        """
        Start listening for real-time data from a Tempest device via cloud WebSocket.
        
        Args:
            device_id: The Tempest device ID (e.g., "205498")
            api_token: Personal Access Token from https://tempestwx.com/settings/tokens
            upload_token: Token for uploading to Community Hub
            sensor_name: Friendly name for the sensor
            on_data_callback: Async callback function(device_id, result_dict)
        """
        if websockets is None:
            print(f"ERROR: websockets library not installed. Run: pip install websockets")
            return
        
        if device_id in self._listeners and not self._listeners[device_id].done():
            print(f"Listener for Tempest device {device_id} already running.")
            return
        
        print(f"Starting cloud WebSocket listener for Tempest device: {device_id}")
        
        # Create stop event for this device
        stop_event = asyncio.Event()
        self._stop_events[device_id] = stop_event
        
        # Start the listener task
        task = asyncio.create_task(
            self._websocket_listener(
                device_id=device_id,
                api_token=api_token,
                upload_token=upload_token,
                sensor_name=sensor_name,
                on_data_callback=on_data_callback,
                stop_event=stop_event
            )
        )
        self._listeners[device_id] = task
    
    def stop_listener(self, device_id: str):
        """Stop the WebSocket listener for a specific device."""
        if device_id in self._stop_events:
            self._stop_events[device_id].set()
        
        if device_id in self._listeners:
            self._listeners[device_id].cancel()
            del self._listeners[device_id]
            print(f"Stopped WebSocket listener for Tempest device: {device_id}")
        
        if device_id in self._stop_events:
            del self._stop_events[device_id]
    
    async def _websocket_listener(
        self,
        device_id: str,
        api_token: str,
        upload_token: str,
        sensor_name: str,
        on_data_callback: Callable,
        stop_event: asyncio.Event
    ):
        """
        Internal WebSocket listener that connects to WeatherFlow cloud.
        
        Reconnects automatically if connection is lost.
        """
        ws_url = f"{self.WEBSOCKET_URL}?token={api_token}"
        
        while not stop_event.is_set():
            try:
                print(f"Connecting to Tempest cloud for device {device_id}...")
                
                async with websockets.connect(ws_url, ping_interval=30) as ws:
                    print(f"Connected! Subscribing to device {device_id}...")
                    
                    # Send listen_start message
                    listen_msg = {
                        "type": "listen_start",
                        "device_id": int(device_id),
                        "id": f"sensor-collector-{device_id}"
                    }
                    await ws.send(json.dumps(listen_msg))
                    print(f"Subscribed to Tempest device {device_id}. Waiting for data...")
                    
                    # Listen for messages
                    while not stop_event.is_set():
                        try:
                            # Wait for message with timeout so we can check stop_event
                            message = await asyncio.wait_for(ws.recv(), timeout=5.0)
                            data = json.loads(message)
                            
                            msg_type = data.get("type", "")
                            
                            # Handle observation data (obs_st = station observation)
                            if msg_type == "obs_st":
                                print(f"Received observation from Tempest {device_id}")
                                await self._process_and_push(
                                    raw_data=data,
                                    device_id=device_id,
                                    sensor_name=sensor_name,
                                    upload_token=upload_token,
                                    on_data_callback=on_data_callback
                                )
                            
                            # Handle acknowledgment
                            elif msg_type == "ack":
                                print(f"Tempest {device_id}: Subscription acknowledged")
                            
                            # Handle connection ready
                            elif msg_type == "connection_opened":
                                print(f"Tempest {device_id}: Connection opened")
                            
                        except asyncio.TimeoutError:
                            # No message received, just continue (allows checking stop_event)
                            continue
                        except asyncio.CancelledError:
                            print(f"Tempest {device_id}: Listener cancelled")
                            return
                            
            except websockets.exceptions.ConnectionClosed as e:
                print(f"Tempest {device_id}: Connection closed ({e}). Reconnecting in 10s...")
                await asyncio.sleep(10)
            except Exception as e:
                print(f"Tempest {device_id}: Error ({e}). Reconnecting in 10s...")
                await asyncio.sleep(10)
        
        print(f"Tempest {device_id}: Listener stopped")
    
    async def _process_and_push(
        self,
        raw_data: dict,
        device_id: str,
        sensor_name: str,
        upload_token: str,
        on_data_callback: Callable
    ):
        """Parse observation data and push to Community Hub."""
        try:
            reading = self.parse_sensor_response(raw_data)
            csv_data = self.convert_to_csv(reading, include_header=True)
            upload_result = await self.push_to_endpoint(csv_data, sensor_name, upload_token)
            
            result = {
                "status": "success",
                "sensor_name": sensor_name,
                "reading": reading.model_dump(),
                "upload_result": upload_result
            }
            
            print(f"Tempest {device_id}: Data uploaded successfully")
            await on_data_callback(device_id, result)
            
        except httpx.HTTPStatusError as e:
            result = {
                "status": "error",
                "sensor_name": sensor_name,
                "error_type": "upload_error",
                "error_message": f"Upload failed: HTTP {e.response.status_code}"
            }
            await on_data_callback(device_id, result)
        except Exception as e:
            result = {
                "status": "error",
                "sensor_name": sensor_name,
                "error_type": "processing_error",
                "error_message": str(e)
            }
            await on_data_callback(device_id, result)
    
    def parse_sensor_response(self, raw_data: dict) -> TempestReading:
        """
        Parse raw Tempest observation data into a clean format.
        
        obs_st format (indices):
        0:  timestamp (epoch seconds)
        1:  wind_lull (m/s) - minimum wind in interval
        2:  wind_avg (m/s) - average wind speed
        3:  wind_gust (m/s) - maximum wind in interval
        4:  wind_direction (degrees)
        5:  wind_sample_interval (seconds)
        6:  station_pressure (MB)
        7:  air_temperature (°C)
        8:  relative_humidity (%)
        9:  illuminance (lux)
        10: uv_index
        11: solar_radiation (W/m²)
        12: rain_accumulated (mm) - since last report
        13: precipitation_type (0=none, 1=rain, 2=hail, 3=mix)
        14: lightning_strike_avg_distance (km)
        15: lightning_strike_count
        16: battery (volts)
        17: report_interval (minutes)
        
        Reference: https://weatherflow.github.io/Tempest/api/
        """
        obs = raw_data.get("obs", [[]])[0]
        
        if not obs or len(obs) < 17:
            return TempestReading(timestamp=datetime.now(timezone.utc))
        
        # Extract ALL values with safe defaults
        epoch = obs[0] if len(obs) > 0 else 0
        wind_lull_ms = obs[1] if len(obs) > 1 else 0
        wind_avg_ms = obs[2] if len(obs) > 2 else 0
        wind_gust_ms = obs[3] if len(obs) > 3 else 0
        wind_direction = obs[4] if len(obs) > 4 else 0
        # obs[5] = wind_sample_interval (not needed)
        pressure_mb = obs[6] if len(obs) > 6 else 0
        temp_c = obs[7] if len(obs) > 7 else 0
        humidity = obs[8] if len(obs) > 8 else 0
        illuminance = obs[9] if len(obs) > 9 else 0
        uv_index = obs[10] if len(obs) > 10 else 0
        solar_radiation = obs[11] if len(obs) > 11 else 0
        rain_mm = obs[12] if len(obs) > 12 else 0
        precip_type = obs[13] if len(obs) > 13 else 0
        lightning_distance_km = obs[14] if len(obs) > 14 else 0
        lightning_count = obs[15] if len(obs) > 15 else 0
        battery = obs[16] if len(obs) > 16 else 0
        report_interval = obs[17] if len(obs) > 17 else 1
        
        # Convert units
        temp_f = (temp_c * 9/5) + 32 if temp_c else 0
        wind_lull_mph = wind_lull_ms * 2.237 if wind_lull_ms else 0
        wind_avg_mph = wind_avg_ms * 2.237 if wind_avg_ms else 0
        wind_gust_mph = wind_gust_ms * 2.237 if wind_gust_ms else 0
        pressure_inhg = pressure_mb * 0.02953 if pressure_mb else 0
        rain_inches = rain_mm * 0.03937 if rain_mm else 0
        lightning_distance_mi = lightning_distance_km * 0.621371 if lightning_distance_km else 0
        
        # Timestamp in UTC
        timestamp = datetime.fromtimestamp(epoch, tz=timezone.utc) if epoch else datetime.now(timezone.utc)
        
        return TempestReading(
            timestamp=timestamp,
            # Temperature & Humidity
            temperature_c=round(float(temp_c), 2),
            temperature_f=round(temp_f, 2),
            humidity_percent=round(float(humidity), 1),
            # Wind
            wind_avg_ms=round(float(wind_avg_ms), 2),
            wind_avg_mph=round(wind_avg_mph, 2),
            wind_gust_ms=round(float(wind_gust_ms), 2),
            wind_gust_mph=round(wind_gust_mph, 2),
            wind_lull_ms=round(float(wind_lull_ms), 2),
            wind_lull_mph=round(wind_lull_mph, 2),
            wind_direction_deg=int(wind_direction),
            # Pressure
            pressure_mb=round(float(pressure_mb), 2),
            pressure_inhg=round(pressure_inhg, 3),
            # Solar & UV
            uv_index=round(float(uv_index), 2),
            solar_radiation_wm2=round(float(solar_radiation), 1),
            illuminance_lux=round(float(illuminance), 0),
            # Precipitation
            rain_mm=round(float(rain_mm), 2),
            rain_inches=round(rain_inches, 4),
            precip_type=int(precip_type),
            # Lightning
            lightning_count=int(lightning_count),
            lightning_avg_distance_km=round(float(lightning_distance_km), 1),
            lightning_avg_distance_mi=round(lightning_distance_mi, 1),
            # Device
            battery_volts=round(float(battery), 2),
            report_interval_min=int(report_interval)
        )
    
    def convert_to_csv(self, reading: TempestReading, include_header: bool = True) -> str:
        """Convert reading to CSV format."""
        lines = []
        if include_header:
            lines.append(TempestReading.csv_header())
        lines.append(reading.to_csv_row())
        return "\n".join(lines)
    
    async def push_to_endpoint(self, csv_data: str, sensor_name: str, upload_token: str) -> dict:
        """Upload CSV data to Community Hub."""
        headers = {"user-token": upload_token}
        
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
    
    async def test_connection(self, device_id: str, api_token: str) -> dict:
        """
        Test connection to Tempest API by fetching latest observation via REST.
        
        This is used to validate credentials before adding a sensor.
        """
        url = f"{self.REST_API_URL}/observations/?device_id={device_id}&token={api_token}"
        
        try:
            response = await self.http_client.get(url)
            response.raise_for_status()
            data = response.json()
            
            # Check if we got valid data
            if data.get("status", {}).get("status_code") == 0:
                return {"status": "success", "message": "Connection successful"}
            else:
                return {
                    "status": "error",
                    "message": data.get("status", {}).get("status_message", "Unknown error")
                }
        except httpx.HTTPStatusError as e:
            return {"status": "error", "message": f"HTTP {e.response.status_code}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    async def close(self):
        """Clean up all listeners and connections."""
        # Stop all listeners
        for device_id in list(self._listeners.keys()):
            self.stop_listener(device_id)
        
        await self.http_client.aclose()
