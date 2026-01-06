# API Documentation

Complete API reference for the Sensor Data Collector backend.

---

## Table of Contents

- [Overview](#overview)
- [Authentication](#authentication)
- [Base URL](#base-url)
- [Response Format](#response-format)
- [Error Handling](#error-handling)
- [Endpoints](#endpoints)
  - [Health & Info](#health--info)
  - [Sensor Management](#sensor-management)
  - [Sensor Control](#sensor-control)
  - [Sensor Type Specific](#sensor-type-specific)
  - [Test Endpoints](#test-endpoints)
- [Data Models](#data-models)
- [CSV Formats](#csv-formats)
- [Examples](#examples)

---

## Overview

The Sensor Data Collector provides a RESTful API for managing environmental sensors. All endpoints return JSON responses and follow standard HTTP status codes.

**Interactive Documentation:**
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- OpenAPI Schema: `http://localhost:8000/openapi.json`

---

## Authentication

### Sensor Management Endpoints
Currently **no authentication required** for sensor management. Add your own authentication middleware as needed.

### Test Upload Endpoint
Requires Bearer token authentication:

```http
Authorization: Bearer test-sensor-api-key-12345
```

---

## Base URL

**Development:**
```
http://localhost:8000
```

**Production (via Cloudflare Tunnel):**
```
https://your-tunnel-url.trycloudflare.com
```

---

## Response Format

### Success Response
```json
{
  "id": "uuid",
  "sensor_type": "purple_air",
  "name": "Lab Sensor",
  "location": "Science Building",
  "status": "active",
  "is_active": true,
  "last_active": "2026-01-05T12:00:00+00:00",
  "last_error": null,
  "created_at": "2026-01-05T10:00:00+00:00"
}
```

### Error Response
```json
{
  "detail": "Sensor not found"
}
```

---

## Error Handling

### HTTP Status Codes

| Code | Meaning | Description |
|------|---------|-------------|
| 200 | OK | Request successful |
| 400 | Bad Request | Invalid input data |
| 404 | Not Found | Resource doesn't exist |
| 422 | Unprocessable Entity | Validation error |
| 500 | Internal Server Error | Server error |
| 501 | Not Implemented | Feature not yet available |

### Common Error Responses

**404 Not Found:**
```json
{
  "detail": "Sensor not found"
}
```

**400 Bad Request:**
```json
{
  "detail": "Invalid IP address format. Expected: xxx.xxx.xxx.xxx"
}
```

**422 Validation Error:**
```json
{
  "detail": [
    {
      "loc": ["body", "ip_address"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

---

## Endpoints

### Health & Info

#### `GET /`
Get API information and endpoint list.

**Response:**
```json
{
  "name": "Sensor Data Collector API",
  "version": "1.0.0",
  "documentation": {
    "swagger": "/docs",
    "redoc": "/redoc"
  },
  "endpoints": {
    "all_sensors": "GET /api/sensors",
    "...": "..."
  }
}
```

#### `GET /health`
Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "polling_interval": 60,
  "external_endpoint": "https://example.com/upload"
}
```

---

### Sensor Management

#### `GET /api/sensors`
List all sensors, optionally filtered by type.

**Query Parameters:**
- `sensor_type` (optional): Filter by type (`purple_air`, `tempest`, `water_quality`, `mayfly`)

**Example Request:**
```bash
curl http://localhost:8000/api/sensors
curl http://localhost:8000/api/sensors?sensor_type=purple_air
```

**Response:**
```json
{
  "sensors": [
    {
      "id": "123e4567-e89b-12d3-a456-426614174000",
      "sensor_type": "purple_air",
      "name": "Lab Sensor",
      "location": "Science Building",
      "ip_address": "192.168.1.100",
      "device_id": null,
      "status": "active",
      "is_active": true,
      "last_active": "2026-01-05T12:00:00+00:00",
      "last_error": null,
      "created_at": "2026-01-05T10:00:00+00:00"
    }
  ],
  "total": 1
}
```

---

#### `GET /api/sensors/{sensor_id}`
Get a specific sensor by ID.

**Path Parameters:**
- `sensor_id`: UUID of the sensor

**Example Request:**
```bash
curl http://localhost:8000/api/sensors/123e4567-e89b-12d3-a456-426614174000
```

**Response:** Single sensor object (see GET /api/sensors response)

---

#### `DELETE /api/sensors/{sensor_id}`
Delete a sensor. This will:
- Stop any active polling
- Remove the sensor from registry
- Cannot be undone

**Path Parameters:**
- `sensor_id`: UUID of the sensor

**Example Request:**
```bash
curl -X DELETE http://localhost:8000/api/sensors/123e4567-e89b-12d3-a456-426614174000
```

**Response:**
```json
{
  "status": "deleted",
  "sensor_id": "123e4567-e89b-12d3-a456-426614174000"
}
```

---

### Sensor Control

#### `POST /api/sensors/{sensor_id}/turn-on`
Start data collection for a sensor. Creates a scheduled job that:
- Runs every 60 seconds (configurable)
- Fetches data from sensor via local IP
- Converts to CSV
- Uploads to external endpoint

**Path Parameters:**
- `sensor_id`: UUID of the sensor

**Example Request:**
```bash
curl -X POST http://localhost:8000/api/sensors/123e4567-e89b-12d3-a456-426614174000/turn-on
```

**Response:** Updated sensor object with `is_active: true`

---

#### `POST /api/sensors/{sensor_id}/turn-off`
Stop data collection for a sensor. Removes the scheduled job. Sensor remains registered.

**Path Parameters:**
- `sensor_id`: UUID of the sensor

**Example Request:**
```bash
curl -X POST http://localhost:8000/api/sensors/123e4567-e89b-12d3-a456-426614174000/turn-off
```

**Response:** Updated sensor object with `is_active: false`

---

#### `POST /api/sensors/{sensor_id}/fetch-now`
Manually trigger a data fetch. Useful for testing without waiting for scheduled poll.

**Path Parameters:**
- `sensor_id`: UUID of the sensor

**Example Request:**
```bash
curl -X POST http://localhost:8000/api/sensors/123e4567-e89b-12d3-a456-426614174000/fetch-now
```

**Success Response:**
```json
{
  "status": "success",
  "sensor_name": "Lab Sensor",
  "reading": {
    "timestamp": "2026-01-05T12:00:00+00:00",
    "temperature_f": 72.5,
    "humidity_percent": 45.0,
    "...": "..."
  },
  "upload_result": {
    "status": "success",
    "filename": "Lab_Sensor_20260105_120000.csv",
    "uploaded_at": "2026-01-05T12:00:01+00:00"
  }
}
```

**Error Response:**
```json
{
  "status": "error",
  "sensor_name": "Lab Sensor",
  "error_type": "connection_error",
  "error_message": "Cannot connect to sensor at 192.168.1.100"
}
```

---

#### `GET /api/sensors/{sensor_id}/status`
Get detailed status information for a sensor.

**Path Parameters:**
- `sensor_id`: UUID of the sensor

**Example Request:**
```bash
curl http://localhost:8000/api/sensors/123e4567-e89b-12d3-a456-426614174000/status
```

**Response:**
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "name": "Lab Sensor",
  "status": "active",
  "is_active": true,
  "last_active": "2026-01-05T12:00:00+00:00",
  "last_error": null
}
```

---

### Sensor Type Specific

#### `POST /api/sensors/purple-air`
Add a new Purple Air sensor.

**Request Body:**
```json
{
  "ip_address": "192.168.1.100",
  "name": "Lab Sensor",
  "location": "Science Building Room 201"
}
```

**Field Requirements:**
- `ip_address`: Valid IPv4 address (e.g., "192.168.1.100")
- `name`: 1-100 characters
- `location`: 1-200 characters

**Example Request:**
```bash
curl -X POST http://localhost:8000/api/sensors/purple-air \
  -H "Content-Type: application/json" \
  -d '{
    "ip_address": "192.168.1.100",
    "name": "Lab Sensor",
    "location": "Science Building Room 201"
  }'
```

**Response:** Full sensor object (see GET /api/sensors response)

---

#### `GET /api/sensors/purple-air`
List all Purple Air sensors.

**Example Request:**
```bash
curl http://localhost:8000/api/sensors/purple-air
```

**Response:** List of Purple Air sensors with total count

---

#### `POST /api/sensors/tempest`
Add a new Tempest weather station.

**Request Body:**
```json
{
  "ip_address": "192.168.1.150",
  "name": "Campus Weather",
  "location": "Rooftop Observatory",
  "device_id": "12345"
}
```

**Field Requirements:**
- `ip_address`: Valid IPv4 address
- `name`: 1-100 characters
- `location`: 1-200 characters
- `device_id`: Tempest device ID (from WeatherFlow app)

**Example Request:**
```bash
curl -X POST http://localhost:8000/api/sensors/tempest \
  -H "Content-Type: application/json" \
  -d '{
    "ip_address": "192.168.1.150",
    "name": "Campus Weather",
    "location": "Rooftop Observatory",
    "device_id": "12345"
  }'
```

**Response:** Full sensor object

---

#### `GET /api/sensors/tempest`
List all Tempest weather stations.

---

#### `POST /api/sensors/water-quality`
Add water quality sensor (NOT YET IMPLEMENTED).

**Response:** 501 Not Implemented

---

#### `GET /api/sensors/water-quality`
List water quality sensors. Returns empty list until implemented.

---

#### `POST /api/sensors/mayfly`
Add Mayfly datalogger (NOT YET IMPLEMENTED).

**Response:** 501 Not Implemented

---

#### `GET /api/sensors/mayfly`
List Mayfly dataloggers. Returns empty list until implemented.

---

### Test Endpoints

#### `POST /api/test/upload/csv`
Test CSV upload endpoint. Mimics external endpoint for local testing.

**Authentication:** Required
```
Authorization: Bearer test-sensor-api-key-12345
```

**Request:**
- Content-Type: `multipart/form-data`
- Field: `file` (CSV file)

**Example Request:**
```bash
curl -X POST http://localhost:8000/api/test/upload/csv \
  -H "Authorization: Bearer test-sensor-api-key-12345" \
  -F "file=@test.csv"
```

**Response:**
```json
{
  "status": "success",
  "filename": "test.csv",
  "size": 128,
  "content_type": "text/csv",
  "first_100_chars": "Timestamp,Value\n2026-01-05...",
  "message": "File received successfully"
}
```

---

#### `GET /api/test/health`
Get test endpoint information.

**Response:**
```json
{
  "status": "ok",
  "test_endpoint": "/api/test/upload/csv",
  "test_token": "test-sensor-api-key-12345",
  "note": "This is for testing only"
}
```

---

## Data Models

### SensorResponse
```typescript
{
  id: string;                    // UUID
  sensor_type: string;           // "purple_air" | "tempest" | "water_quality" | "mayfly"
  name: string;
  location: string;
  ip_address?: string;           // Optional, for network sensors
  device_id?: string;            // Optional, for Tempest
  status: string;                // "active" | "inactive" | "error" | "offline"
  is_active: boolean;            // Whether polling is enabled
  last_active?: string;          // ISO 8601 timestamp
  last_error?: string;           // Error message if status is "error"
  created_at: string;            // ISO 8601 timestamp
}
```

### SensorListResponse
```typescript
{
  sensors: SensorResponse[];
  total: number;
}
```

### FetchResultResponse
```typescript
{
  status: "success" | "error";
  sensor_name: string;
  reading?: {                    // Present on success
    timestamp: string;
    // ... sensor-specific fields
  };
  upload_result?: {              // Present on success
    status: string;
    filename: string;
    uploaded_at: string;
  };
  error_type?: string;           // Present on error
  error_message?: string;        // Present on error
}
```

---

## CSV Formats

### Purple Air CSV
```csv
Timestamp,Temperature (°F),Humidity (%),Dewpoint (°F),Pressure (hPa),PM1.0 :cf_1( µg/m³),PM2.5 :cf_1( µg/m³),PM10.0 :cf_1( µg/m³),PM2.5 AQI
2026-01-05T22:26:50+00:00,40,62,28,985.09,15.82,26.49,33.05,82
```

### Tempest CSV
```csv
Timestamp,Temperature (°F),Humidity (%),Pressure (mb),Wind Speed (mph),Wind Gust (mph),Wind Direction (°),Rain (in),UV Index,Solar Radiation (W/m²),Lightning Count
2026-01-05T22:26:50+00:00,72.5,45.2,1013.25,5.2,8.1,180,0.0,3.5,450,0
```

---

## Examples

### Complete Workflow

```bash
# 1. Check API health
curl http://localhost:8000/health

# 2. Add a Purple Air sensor
RESPONSE=$(curl -X POST http://localhost:8000/api/sensors/purple-air \
  -H "Content-Type: application/json" \
  -d '{
    "ip_address": "192.168.1.100",
    "name": "Lab Sensor",
    "location": "Science Building"
  }')

# Extract sensor ID (requires jq)
SENSOR_ID=$(echo $RESPONSE | jq -r '.id')

# 3. Turn on the sensor
curl -X POST http://localhost:8000/api/sensors/$SENSOR_ID/turn-on

# 4. Check status
curl http://localhost:8000/api/sensors/$SENSOR_ID/status

# 5. Manual fetch to test
curl -X POST http://localhost:8000/api/sensors/$SENSOR_ID/fetch-now

# 6. List all sensors
curl http://localhost:8000/api/sensors

# 7. Turn off when done
curl -X POST http://localhost:8000/api/sensors/$SENSOR_ID/turn-off

# 8. Delete sensor
curl -X DELETE http://localhost:8000/api/sensors/$SENSOR_ID
```

### Error Handling Example

```python
import httpx
import sys

async def add_sensor():
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:8000/api/sensors/purple-air",
                json={
                    "ip_address": "192.168.1.100",
                    "name": "Test Sensor",
                    "location": "Test Lab"
                }
            )
            response.raise_for_status()
            sensor = response.json()
            print(f"✅ Sensor added: {sensor['id']}")
            return sensor
            
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 400:
            print(f"❌ Bad request: {e.response.json()['detail']}")
        elif e.response.status_code == 422:
            print(f"❌ Validation error: {e.response.json()['detail']}")
        else:
            print(f"❌ HTTP error: {e}")
        sys.exit(1)
        
    except httpx.ConnectError:
        print("❌ Cannot connect to API server")
        sys.exit(1)
```

---

## Rate Limiting

Currently **no rate limiting** is implemented. Add your own rate limiting middleware if needed for production use.

---

## Versioning

API version: **1.0.0**

The API currently does not use versioned paths. Future versions may introduce `/v2/` prefixes if breaking changes are needed.

---

## Support

For questions about the API:
1. Check the interactive docs at `/docs`
2. Review this documentation
3. Open an issue on GitHub
4. Check the main README.md

---

**Last Updated:** January 2026

