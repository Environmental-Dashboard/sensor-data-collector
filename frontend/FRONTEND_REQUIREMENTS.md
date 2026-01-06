# Frontend Requirements & API Documentation

## Overview

This document describes the requirements for building the frontend dashboard for the Sensor Data Collector system. The backend is complete and ready to use.

## What We're Building

A **professional sensor management dashboard** that allows users to:
- View all registered sensors
- Add new sensors
- Turn sensors on/off (start/stop data collection)
- View sensor status and last active time
- Delete sensors
- Manually trigger data fetches (for testing)

## Sensor Types

The dashboard should display **4 sensor groups** as cards/sections:

| Sensor Type | Status | Add Fields Required |
|-------------|--------|---------------------|
| **Purple Air** (Air Quality) | ✅ Working | `ip_address`, `name`, `location` |
| **Tempest** (Weather) | ✅ Working | `ip_address`, `name`, `location`, `device_id` |
| **Water Quality** | 🚧 Not Implemented | `name`, `location` (will show error) |
| **Mayfly** | 🚧 Not Implemented | `name`, `location` (will show error) |

---

## Dashboard Layout

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ HEADER                                                                       │
│   Logo + "Sensor Dashboard"              [Backend Status: Connected/Offline] │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────┐  ┌─────────────────────────────────────┐   │
│  │ 🌬️ AIR QUALITY              │  │ 🌤️ TEMPEST WEATHER                  │   │
│  │ Purple Air Sensors          │  │ Weather Stations                    │   │
│  │ 2/3 active                  │  │ 1/1 active                          │   │
│  ├─────────────────────────────┤  ├─────────────────────────────────────┤   │
│  │ [+ Add] [View All]          │  │ [+ Add] [View All]                  │   │
│  ├─────────────────────────────┤  ├─────────────────────────────────────┤   │
│  │ ┌───────────────────────┐   │  │ ┌─────────────────────────────────┐ │   │
│  │ │ Lab Room Sensor       │   │  │ │ Campus Weather Station         │ │   │
│  │ │ Location: Science 201 │   │  │ │ Location: Rooftop              │ │   │
│  │ │ IP: 192.168.1.100    │   │  │ │ IP: 192.168.1.150              │ │   │
│  │ │ Status: 🟢 Active     │   │  │ │ Status: 🟢 Active              │ │   │
│  │ │ Last: 2 min ago       │   │  │ │ Last: 1 min ago                │ │   │
│  │ │ [On/Off] [Fetch] [🗑️] │   │  │ │ [On/Off] [Fetch] [🗑️]          │ │   │
│  │ └───────────────────────┘   │  │ └─────────────────────────────────┘ │   │
│  │ ┌───────────────────────┐   │  └─────────────────────────────────────┘   │
│  │ │ Outdoor Monitor       │   │                                            │
│  │ │ ...                   │   │  ┌─────────────────────────────────────┐   │
│  │ └───────────────────────┘   │  │ 💧 WATER QUALITY                    │   │
│  └─────────────────────────────┘  │ Coming Soon                         │   │
│                                   └─────────────────────────────────────┘   │
│  ┌─────────────────────────────┐                                            │
│  │ 📊 MAYFLY DATALOGGERS       │                                            │
│  │ Coming Soon                 │                                            │
│  └─────────────────────────────┘                                            │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Default Functions for Each Sensor Group

Every sensor card should have these actions:

| Action | Description | API Call |
|--------|-------------|----------|
| **View Status** | Show current status (active/inactive/error) | `GET /api/sensors/{id}/status` |
| **Add Sensor** | Open modal to add new sensor | `POST /api/sensors/{type}` |
| **Delete Sensor** | Remove sensor (with confirmation) | `DELETE /api/sensors/{id}` |
| **View All** | Show all sensors in this group | `GET /api/sensors/{type}` |
| **Turn On** | Start data collection | `POST /api/sensors/{id}/turn-on` |
| **Turn Off** | Stop data collection | `POST /api/sensors/{id}/turn-off` |
| **Last Active** | Show when sensor last sent data | Included in sensor response |
| **Fetch Now** | Manually trigger data fetch | `POST /api/sensors/{id}/fetch-now` |

---

## API Reference

### Base URL

Development: `http://localhost:8000`

Production: Your Cloudflare Tunnel URL (e.g., `https://your-tunnel.trycloudflare.com`)

Set this as an environment variable: `VITE_API_URL` (or your framework's equivalent)

---

### Endpoints

#### 1. Health Check

```
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "polling_interval": 60,
  "external_endpoint": "http://localhost:8000/api/test/upload/csv"
}
```

Use this to show "Backend Connected" or "Backend Disconnected" in the header.

---

#### 2. List All Sensors

```
GET /api/sensors
GET /api/sensors?sensor_type=purple_air
```

**Query Parameters:**
- `sensor_type` (optional): `purple_air`, `tempest`, `water_quality`, `mayfly`

**Response:**
```json
{
  "sensors": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "sensor_type": "purple_air",
      "name": "Lab Room Sensor",
      "location": "Science Building Room 201",
      "ip_address": "192.168.1.100",
      "device_id": null,
      "status": "active",
      "is_active": true,
      "last_active": "2026-01-05T22:30:00+00:00",
      "last_error": null,
      "created_at": "2026-01-05T20:00:00+00:00"
    }
  ],
  "total": 1
}
```

---

#### 3. List Sensors by Type

```
GET /api/sensors/purple-air
GET /api/sensors/tempest
GET /api/sensors/water-quality
GET /api/sensors/mayfly
```

Same response format as above, filtered by type.

---

#### 4. Get Single Sensor

```
GET /api/sensors/{sensor_id}
```

**Response:** Single sensor object (same format as list item)

---

#### 5. Add Purple Air Sensor

```
POST /api/sensors/purple-air
Content-Type: application/json

{
  "ip_address": "192.168.1.100",
  "name": "Lab Room Sensor",
  "location": "Science Building Room 201"
}
```

**Required Fields:**
- `ip_address`: Valid IPv4 address (e.g., "192.168.1.100")
- `name`: String, 1-100 characters
- `location`: String, 1-200 characters

**Response:** Created sensor object

**Errors:**
- `400`: Invalid IP format or duplicate IP

---

#### 6. Add Tempest Weather Sensor

```
POST /api/sensors/tempest
Content-Type: application/json

{
  "ip_address": "192.168.1.150",
  "name": "Campus Weather Station",
  "location": "Rooftop Observatory",
  "device_id": "12345"
}
```

**Required Fields:**
- `ip_address`: IP of the Tempest Hub
- `name`: String
- `location`: String
- `device_id`: Tempest device ID (from WeatherFlow app)

---

#### 7. Delete Sensor

```
DELETE /api/sensors/{sensor_id}
```

**Response:**
```json
{
  "status": "deleted",
  "sensor_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

---

#### 8. Get Sensor Status

```
GET /api/sensors/{sensor_id}/status
```

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Lab Room Sensor",
  "status": "active",
  "is_active": true,
  "last_active": "2026-01-05T22:30:00+00:00",
  "last_error": null
}
```

**Status Values:**
- `active`: Sensor is polling and sending data
- `inactive`: Registered but not polling
- `error`: Last poll failed
- `offline`: Sensor unreachable

---

#### 9. Turn On Sensor

```
POST /api/sensors/{sensor_id}/turn-on
```

Starts the polling job. Sensor will fetch data every 60 seconds.

**Response:** Updated sensor object with `is_active: true`

---

#### 10. Turn Off Sensor

```
POST /api/sensors/{sensor_id}/turn-off
```

Stops the polling job.

**Response:** Updated sensor object with `is_active: false`

---

#### 11. Manual Fetch (Fetch Now)

```
POST /api/sensors/{sensor_id}/fetch-now
```

Triggers an immediate data fetch. Useful for testing.

**Response (Success):**
```json
{
  "status": "success",
  "sensor_name": "Lab Room Sensor",
  "reading": {
    "timestamp": "2026-01-05T22:30:00+00:00",
    "temperature_f": 72.5,
    "humidity_percent": 45.2,
    "dewpoint_f": 52.1,
    "pressure_hpa": 1013.25,
    "pm1_0_cf1": 5.2,
    "pm2_5_cf1": 12.4,
    "pm10_0_cf1": 18.7,
    "pm2_5_aqi": 52
  },
  "upload_result": {
    "status": "success",
    "filename": "Lab_Room_Sensor_20260105_223000.csv",
    "uploaded_at": "2026-01-05T22:30:01+00:00"
  }
}
```

**Response (Error):**
```json
{
  "status": "error",
  "sensor_name": "Lab Room Sensor",
  "error_type": "connection_error",
  "error_message": "Cannot connect to sensor at 192.168.1.100"
}
```

---

## TypeScript Interfaces

Here are the TypeScript types you'll need:

```typescript
// Sensor types
type SensorType = 'purple_air' | 'tempest' | 'water_quality' | 'mayfly';
type SensorStatus = 'active' | 'inactive' | 'error' | 'offline';

// Sensor object
interface Sensor {
  id: string;
  sensor_type: SensorType;
  name: string;
  location: string;
  ip_address: string | null;
  device_id: string | null;
  status: SensorStatus;
  is_active: boolean;
  last_active: string | null;  // ISO timestamp
  last_error: string | null;
  created_at: string;  // ISO timestamp
}

// List response
interface SensorListResponse {
  sensors: Sensor[];
  total: number;
}

// Add Purple Air request
interface AddPurpleAirRequest {
  ip_address: string;
  name: string;
  location: string;
}

// Add Tempest request
interface AddTempestRequest {
  ip_address: string;
  name: string;
  location: string;
  device_id: string;
}

// Fetch result
interface FetchResult {
  status: 'success' | 'error';
  sensor_name: string;
  reading?: Record<string, unknown>;
  upload_result?: {
    status: string;
    filename: string;
    uploaded_at: string;
  };
  error_type?: string;
  error_message?: string;
}
```

---

## How to Test If It Works

### 1. Start the Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

You should see:
```
🚀 SENSOR DATA COLLECTOR - Starting Backend
✅ Services initialized
📖 API Documentation: http://localhost:8000/docs
```

### 2. Test with curl or the Swagger UI

Open http://localhost:8000/docs in your browser to see interactive API documentation.

Or test with curl:

```bash
# Check health
curl http://localhost:8000/health

# Add a Purple Air sensor
curl -X POST http://localhost:8000/api/sensors/purple-air \
  -H "Content-Type: application/json" \
  -d '{"ip_address": "192.168.1.100", "name": "Test Sensor", "location": "Office"}'

# List all sensors
curl http://localhost:8000/api/sensors

# Turn on a sensor (replace {id} with actual ID from add response)
curl -X POST http://localhost:8000/api/sensors/{id}/turn-on

# Manual fetch
curl -X POST http://localhost:8000/api/sensors/{id}/fetch-now

# Turn off
curl -X POST http://localhost:8000/api/sensors/{id}/turn-off

# Delete
curl -X DELETE http://localhost:8000/api/sensors/{id}
```

### 3. Test the Upload Endpoint

```bash
# Check test endpoint health (shows the API key to use)
curl http://localhost:8000/api/test/health

# Upload a CSV file
curl -X POST http://localhost:8000/api/test/upload/csv \
  -H "Authorization: Bearer test-sensor-api-key-12345" \
  -F "file=@test.csv"
```

---

## Frontend Environment Variables

Set these in your frontend:

```
VITE_API_URL=http://localhost:8000
```

For production with Cloudflare Tunnel:
```
VITE_API_URL=https://your-tunnel-url.trycloudflare.com
```

---

## UI/UX Recommendations

1. **Connection Status**: Poll `/health` every 30 seconds to show backend status
2. **Auto-refresh**: Refresh sensor lists every 30-60 seconds when on the page
3. **Loading States**: Show spinners during API calls
4. **Error Handling**: Display error messages from API responses
5. **Confirmation Dialogs**: Confirm before delete and turn-off actions
6. **Status Badges**: Color-code status (green=active, gray=inactive, red=error)
7. **Timestamps**: Format "last_active" as relative time ("2 minutes ago")

---

## Questions?

The backend code is fully documented. Check:
- `backend/app/main.py` - Application setup and configuration
- `backend/app/routers/sensors.py` - All API endpoints
- `backend/app/models/sensor.py` - All data models
- `backend/app/services/` - Business logic

Interactive API docs at: http://localhost:8000/docs


## Overview

This document describes the requirements for building the frontend dashboard for the Sensor Data Collector system. The backend is complete and ready to use.

## What We're Building

A **professional sensor management dashboard** that allows users to:
- View all registered sensors
- Add new sensors
- Turn sensors on/off (start/stop data collection)
- View sensor status and last active time
- Delete sensors
- Manually trigger data fetches (for testing)

## Sensor Types

The dashboard should display **4 sensor groups** as cards/sections:

| Sensor Type | Status | Add Fields Required |
|-------------|--------|---------------------|
| **Purple Air** (Air Quality) | ✅ Working | `ip_address`, `name`, `location` |
| **Tempest** (Weather) | ✅ Working | `ip_address`, `name`, `location`, `device_id` |
| **Water Quality** | 🚧 Not Implemented | `name`, `location` (will show error) |
| **Mayfly** | 🚧 Not Implemented | `name`, `location` (will show error) |

---

## Dashboard Layout

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ HEADER                                                                       │
│   Logo + "Sensor Dashboard"              [Backend Status: Connected/Offline] │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────┐  ┌─────────────────────────────────────┐   │
│  │ 🌬️ AIR QUALITY              │  │ 🌤️ TEMPEST WEATHER                  │   │
│  │ Purple Air Sensors          │  │ Weather Stations                    │   │
│  │ 2/3 active                  │  │ 1/1 active                          │   │
│  ├─────────────────────────────┤  ├─────────────────────────────────────┤   │
│  │ [+ Add] [View All]          │  │ [+ Add] [View All]                  │   │
│  ├─────────────────────────────┤  ├─────────────────────────────────────┤   │
│  │ ┌───────────────────────┐   │  │ ┌─────────────────────────────────┐ │   │
│  │ │ Lab Room Sensor       │   │  │ │ Campus Weather Station         │ │   │
│  │ │ Location: Science 201 │   │  │ │ Location: Rooftop              │ │   │
│  │ │ IP: 192.168.1.100    │   │  │ │ IP: 192.168.1.150              │ │   │
│  │ │ Status: 🟢 Active     │   │  │ │ Status: 🟢 Active              │ │   │
│  │ │ Last: 2 min ago       │   │  │ │ Last: 1 min ago                │ │   │
│  │ │ [On/Off] [Fetch] [🗑️] │   │  │ │ [On/Off] [Fetch] [🗑️]          │ │   │
│  │ └───────────────────────┘   │  │ └─────────────────────────────────┘ │   │
│  │ ┌───────────────────────┐   │  └─────────────────────────────────────┘   │
│  │ │ Outdoor Monitor       │   │                                            │
│  │ │ ...                   │   │  ┌─────────────────────────────────────┐   │
│  │ └───────────────────────┘   │  │ 💧 WATER QUALITY                    │   │
│  └─────────────────────────────┘  │ Coming Soon                         │   │
│                                   └─────────────────────────────────────┘   │
│  ┌─────────────────────────────┐                                            │
│  │ 📊 MAYFLY DATALOGGERS       │                                            │
│  │ Coming Soon                 │                                            │
│  └─────────────────────────────┘                                            │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Default Functions for Each Sensor Group

Every sensor card should have these actions:

| Action | Description | API Call |
|--------|-------------|----------|
| **View Status** | Show current status (active/inactive/error) | `GET /api/sensors/{id}/status` |
| **Add Sensor** | Open modal to add new sensor | `POST /api/sensors/{type}` |
| **Delete Sensor** | Remove sensor (with confirmation) | `DELETE /api/sensors/{id}` |
| **View All** | Show all sensors in this group | `GET /api/sensors/{type}` |
| **Turn On** | Start data collection | `POST /api/sensors/{id}/turn-on` |
| **Turn Off** | Stop data collection | `POST /api/sensors/{id}/turn-off` |
| **Last Active** | Show when sensor last sent data | Included in sensor response |
| **Fetch Now** | Manually trigger data fetch | `POST /api/sensors/{id}/fetch-now` |

---

## API Reference

### Base URL

Development: `http://localhost:8000`

Production: Your Cloudflare Tunnel URL (e.g., `https://your-tunnel.trycloudflare.com`)

Set this as an environment variable: `VITE_API_URL` (or your framework's equivalent)

---

### Endpoints

#### 1. Health Check

```
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "polling_interval": 60,
  "external_endpoint": "http://localhost:8000/api/test/upload/csv"
}
```

Use this to show "Backend Connected" or "Backend Disconnected" in the header.

---

#### 2. List All Sensors

```
GET /api/sensors
GET /api/sensors?sensor_type=purple_air
```

**Query Parameters:**
- `sensor_type` (optional): `purple_air`, `tempest`, `water_quality`, `mayfly`

**Response:**
```json
{
  "sensors": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "sensor_type": "purple_air",
      "name": "Lab Room Sensor",
      "location": "Science Building Room 201",
      "ip_address": "192.168.1.100",
      "device_id": null,
      "status": "active",
      "is_active": true,
      "last_active": "2026-01-05T22:30:00+00:00",
      "last_error": null,
      "created_at": "2026-01-05T20:00:00+00:00"
    }
  ],
  "total": 1
}
```

---

#### 3. List Sensors by Type

```
GET /api/sensors/purple-air
GET /api/sensors/tempest
GET /api/sensors/water-quality
GET /api/sensors/mayfly
```

Same response format as above, filtered by type.

---

#### 4. Get Single Sensor

```
GET /api/sensors/{sensor_id}
```

**Response:** Single sensor object (same format as list item)

---

#### 5. Add Purple Air Sensor

```
POST /api/sensors/purple-air
Content-Type: application/json

{
  "ip_address": "192.168.1.100",
  "name": "Lab Room Sensor",
  "location": "Science Building Room 201"
}
```

**Required Fields:**
- `ip_address`: Valid IPv4 address (e.g., "192.168.1.100")
- `name`: String, 1-100 characters
- `location`: String, 1-200 characters

**Response:** Created sensor object

**Errors:**
- `400`: Invalid IP format or duplicate IP

---

#### 6. Add Tempest Weather Sensor

```
POST /api/sensors/tempest
Content-Type: application/json

{
  "ip_address": "192.168.1.150",
  "name": "Campus Weather Station",
  "location": "Rooftop Observatory",
  "device_id": "12345"
}
```

**Required Fields:**
- `ip_address`: IP of the Tempest Hub
- `name`: String
- `location`: String
- `device_id`: Tempest device ID (from WeatherFlow app)

---

#### 7. Delete Sensor

```
DELETE /api/sensors/{sensor_id}
```

**Response:**
```json
{
  "status": "deleted",
  "sensor_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

---

#### 8. Get Sensor Status

```
GET /api/sensors/{sensor_id}/status
```

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Lab Room Sensor",
  "status": "active",
  "is_active": true,
  "last_active": "2026-01-05T22:30:00+00:00",
  "last_error": null
}
```

**Status Values:**
- `active`: Sensor is polling and sending data
- `inactive`: Registered but not polling
- `error`: Last poll failed
- `offline`: Sensor unreachable

---

#### 9. Turn On Sensor

```
POST /api/sensors/{sensor_id}/turn-on
```

Starts the polling job. Sensor will fetch data every 60 seconds.

**Response:** Updated sensor object with `is_active: true`

---

#### 10. Turn Off Sensor

```
POST /api/sensors/{sensor_id}/turn-off
```

Stops the polling job.

**Response:** Updated sensor object with `is_active: false`

---

#### 11. Manual Fetch (Fetch Now)

```
POST /api/sensors/{sensor_id}/fetch-now
```

Triggers an immediate data fetch. Useful for testing.

**Response (Success):**
```json
{
  "status": "success",
  "sensor_name": "Lab Room Sensor",
  "reading": {
    "timestamp": "2026-01-05T22:30:00+00:00",
    "temperature_f": 72.5,
    "humidity_percent": 45.2,
    "dewpoint_f": 52.1,
    "pressure_hpa": 1013.25,
    "pm1_0_cf1": 5.2,
    "pm2_5_cf1": 12.4,
    "pm10_0_cf1": 18.7,
    "pm2_5_aqi": 52
  },
  "upload_result": {
    "status": "success",
    "filename": "Lab_Room_Sensor_20260105_223000.csv",
    "uploaded_at": "2026-01-05T22:30:01+00:00"
  }
}
```

**Response (Error):**
```json
{
  "status": "error",
  "sensor_name": "Lab Room Sensor",
  "error_type": "connection_error",
  "error_message": "Cannot connect to sensor at 192.168.1.100"
}
```

---

## TypeScript Interfaces

Here are the TypeScript types you'll need:

```typescript
// Sensor types
type SensorType = 'purple_air' | 'tempest' | 'water_quality' | 'mayfly';
type SensorStatus = 'active' | 'inactive' | 'error' | 'offline';

// Sensor object
interface Sensor {
  id: string;
  sensor_type: SensorType;
  name: string;
  location: string;
  ip_address: string | null;
  device_id: string | null;
  status: SensorStatus;
  is_active: boolean;
  last_active: string | null;  // ISO timestamp
  last_error: string | null;
  created_at: string;  // ISO timestamp
}

// List response
interface SensorListResponse {
  sensors: Sensor[];
  total: number;
}

// Add Purple Air request
interface AddPurpleAirRequest {
  ip_address: string;
  name: string;
  location: string;
}

// Add Tempest request
interface AddTempestRequest {
  ip_address: string;
  name: string;
  location: string;
  device_id: string;
}

// Fetch result
interface FetchResult {
  status: 'success' | 'error';
  sensor_name: string;
  reading?: Record<string, unknown>;
  upload_result?: {
    status: string;
    filename: string;
    uploaded_at: string;
  };
  error_type?: string;
  error_message?: string;
}
```

---

## How to Test If It Works

### 1. Start the Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

You should see:
```
🚀 SENSOR DATA COLLECTOR - Starting Backend
✅ Services initialized
📖 API Documentation: http://localhost:8000/docs
```

### 2. Test with curl or the Swagger UI

Open http://localhost:8000/docs in your browser to see interactive API documentation.

Or test with curl:

```bash
# Check health
curl http://localhost:8000/health

# Add a Purple Air sensor
curl -X POST http://localhost:8000/api/sensors/purple-air \
  -H "Content-Type: application/json" \
  -d '{"ip_address": "192.168.1.100", "name": "Test Sensor", "location": "Office"}'

# List all sensors
curl http://localhost:8000/api/sensors

# Turn on a sensor (replace {id} with actual ID from add response)
curl -X POST http://localhost:8000/api/sensors/{id}/turn-on

# Manual fetch
curl -X POST http://localhost:8000/api/sensors/{id}/fetch-now

# Turn off
curl -X POST http://localhost:8000/api/sensors/{id}/turn-off

# Delete
curl -X DELETE http://localhost:8000/api/sensors/{id}
```

### 3. Test the Upload Endpoint

```bash
# Check test endpoint health (shows the API key to use)
curl http://localhost:8000/api/test/health

# Upload a CSV file
curl -X POST http://localhost:8000/api/test/upload/csv \
  -H "Authorization: Bearer test-sensor-api-key-12345" \
  -F "file=@test.csv"
```

---

## Frontend Environment Variables

Set these in your frontend:

```
VITE_API_URL=http://localhost:8000
```

For production with Cloudflare Tunnel:
```
VITE_API_URL=https://your-tunnel-url.trycloudflare.com
```

---

## UI/UX Recommendations

1. **Connection Status**: Poll `/health` every 30 seconds to show backend status
2. **Auto-refresh**: Refresh sensor lists every 30-60 seconds when on the page
3. **Loading States**: Show spinners during API calls
4. **Error Handling**: Display error messages from API responses
5. **Confirmation Dialogs**: Confirm before delete and turn-off actions
6. **Status Badges**: Color-code status (green=active, gray=inactive, red=error)
7. **Timestamps**: Format "last_active" as relative time ("2 minutes ago")

---

## Questions?

The backend code is fully documented. Check:
- `backend/app/main.py` - Application setup and configuration
- `backend/app/routers/sensors.py` - All API endpoints
- `backend/app/models/sensor.py` - All data models
- `backend/app/services/` - Business logic

Interactive API docs at: http://localhost:8000/docs

