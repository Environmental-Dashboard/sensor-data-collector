# Frontend Requirements 🎨

Hey! So you're building the frontend for this sensor dashboard. Let me break it down for you.

## What We're Building

A dashboard where users can:
- See all their sensors
- Add new ones
- Turn them on/off
- Check if they're working
- Delete ones they don't need

It's basically a control panel for environmental sensors.

## The Backend is Ready!

I've already built the whole backend. It's running and works great. You just need to make HTTP calls to it and display the data nicely.

**Test it yourself:**
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Then open http://localhost:8000/docs - you'll see all the endpoints you can use!

---

## The Dashboard Layout

Here's what I'm thinking. Four sensor groups, each as a card:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│  SENSOR DASHBOARD                               [🟢 Backend Connected]       │
│                                                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────┐    ┌───────────────────────────────────┐   │
│  │ 🌬️ AIR QUALITY              │    │ 🌤️ WEATHER                        │   │
│  │ Purple Air Sensors          │    │ Tempest Stations                  │   │
│  │                             │    │                                   │   │
│  │ [+ Add Sensor]              │    │ [+ Add Sensor]                    │   │
│  │                             │    │                                   │   │
│  │ ┌─────────────────────────┐ │    │ ┌─────────────────────────────┐   │   │
│  │ │ Lab Sensor              │ │    │ │ Campus Weather              │   │   │
│  │ │ 📍 Science Building     │ │    │ │ 📍 Rooftop                  │   │   │
│  │ │ 🌐 10.17.192.162        │ │    │ │ 🌐 192.168.1.150            │   │   │
│  │ │ 🟢 Active               │ │    │ │ 🟢 Active                   │   │   │
│  │ │ Last: 2 min ago         │ │    │ │ Last: 1 min ago             │   │   │
│  │ │                         │ │    │ │                             │   │   │
│  │ │ [Turn Off] [Fetch] [🗑️] │ │    │ │ [Turn Off] [Fetch] [🗑️]     │   │   │
│  │ └─────────────────────────┘ │    │ └─────────────────────────────┘   │   │
│  └─────────────────────────────┘    └───────────────────────────────────┘   │
│                                                                              │
│  ┌─────────────────────────────┐    ┌───────────────────────────────────┐   │
│  │ 💧 WATER QUALITY            │    │ 📊 MAYFLY                         │   │
│  │ Coming Soon!                │    │ Coming Soon!                      │   │
│  └─────────────────────────────┘    └───────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## What Each Button Does

### For Each Sensor Group Card

| Button | What It Does |
|--------|--------------|
| **+ Add Sensor** | Opens a form to add a new sensor |

### For Each Individual Sensor

| Button | What It Does |
|--------|--------------|
| **Turn On** | Starts collecting data (every 60 seconds) |
| **Turn Off** | Stops collecting data |
| **Fetch** | Grabs data right now (for testing) |
| **🗑️ Delete** | Removes the sensor (ask for confirmation first!) |

---

## The API - How to Talk to the Backend

### Base URL

When developing locally:
```
http://localhost:8000
```

Store this in an environment variable so it's easy to change later:
```
VITE_API_URL=http://localhost:8000
```

### Endpoints You'll Use

#### Check if Backend is Running

```
GET /health
```

Response:
```json
{
  "status": "healthy",
  "polling_interval": 60
}
```

Call this every 30 seconds to show "🟢 Connected" or "🔴 Disconnected" in the header.

---

#### Get All Sensors

```
GET /api/sensors/
```

Response:
```json
{
  "sensors": [
    {
      "id": "abc-123-def",
      "sensor_type": "purple_air",
      "name": "Lab Sensor",
      "location": "Science Building",
      "ip_address": "10.17.192.162",
      "status": "active",
      "is_active": true,
      "last_active": "2026-01-06T03:00:00Z",
      "last_error": null
    }
  ],
  "total": 1
}
```

Use this to populate the dashboard.

---

#### Get Sensors by Type

```
GET /api/sensors/purple-air
GET /api/sensors/tempest
GET /api/sensors/water-quality
GET /api/sensors/mayfly
```

Same response format, just filtered.

---

#### Add a Purple Air Sensor

```
POST /api/sensors/purple-air
Content-Type: application/json

{
  "ip_address": "10.17.192.162",
  "name": "Lab Sensor",
  "location": "Science Building Room 201",
  "upload_token": "user's-cloud-token"
}
```

**All fields are required!**

Response: The created sensor object.

Errors:
- `400` if IP is invalid or already exists
- `422` if fields are missing

---

#### Add a Tempest Sensor

```
POST /api/sensors/tempest
Content-Type: application/json

{
  "ip_address": "192.168.1.150",
  "name": "Campus Weather",
  "location": "Rooftop Observatory",
  "device_id": "12345",
  "upload_token": "user's-cloud-token"
}
```

Note: Tempest needs `device_id` which Purple Air doesn't.

---

#### Turn On a Sensor

```
POST /api/sensors/{id}/turn-on
```

Response: The updated sensor with `is_active: true`

This starts the automatic polling. Every 60 seconds, it'll fetch data and upload.

---

#### Turn Off a Sensor

```
POST /api/sensors/{id}/turn-off
```

Response: The updated sensor with `is_active: false`

---

#### Manual Fetch (the "Fetch Now" button)

```
POST /api/sensors/{id}/fetch-now
```

Response if it worked:
```json
{
  "status": "success",
  "sensor_name": "Lab Sensor",
  "reading": {
    "timestamp": "2026-01-06T03:00:00Z",
    "temperature_f": 72,
    "humidity_percent": 45,
    "pm2_5_aqi": 52
  },
  "upload_result": {
    "status": "success",
    "filename": "Lab_Sensor_20260106_030000.csv"
  }
}
```

Response if it failed:
```json
{
  "status": "error",
  "error_message": "Cannot connect to sensor. Is it on?"
}
```

---

#### Get Sensor Status

```
GET /api/sensors/{id}/status
```

Response:
```json
{
  "id": "abc-123",
  "name": "Lab Sensor",
  "status": "active",
  "is_active": true,
  "last_active": "2026-01-06T03:00:00Z",
  "last_error": null
}
```

---

#### Delete a Sensor

```
DELETE /api/sensors/{id}
```

Response:
```json
{
  "status": "deleted",
  "sensor_id": "abc-123"
}
```

**Show a confirmation dialog before calling this!**

---

## TypeScript Types

Here are the types you'll need:

```typescript
// What type of sensor
type SensorType = 'purple_air' | 'tempest' | 'water_quality' | 'mayfly';

// Is it working?
type SensorStatus = 'active' | 'inactive' | 'error' | 'offline';

// A sensor object
interface Sensor {
  id: string;
  sensor_type: SensorType;
  name: string;
  location: string;
  ip_address: string | null;
  device_id: string | null;  // Only for Tempest
  status: SensorStatus;
  is_active: boolean;
  last_active: string | null;  // ISO timestamp
  last_error: string | null;
  created_at: string;
}

// Response from list endpoints
interface SensorListResponse {
  sensors: Sensor[];
  total: number;
}

// Adding a Purple Air sensor
interface AddPurpleAirRequest {
  ip_address: string;
  name: string;
  location: string;
  upload_token: string;
}

// Adding a Tempest sensor
interface AddTempestRequest {
  ip_address: string;
  name: string;
  location: string;
  device_id: string;
  upload_token: string;
}
```

---

## Form Fields for Adding Sensors

### Purple Air Form

| Field | Type | Required | Placeholder |
|-------|------|----------|-------------|
| IP Address | text | Yes | `192.168.1.100` |
| Name | text | Yes | `Lab Sensor` |
| Location | text | Yes | `Science Building Room 201` |
| Upload Token | password | Yes | `Your token from communityhub` |

### Tempest Form

Same as above, plus:

| Field | Type | Required | Placeholder |
|-------|------|----------|-------------|
| Device ID | text | Yes | `12345` |

---

## Status Colors

| Status | Color | Meaning |
|--------|-------|---------|
| `active` | 🟢 Green | Sensor is collecting data |
| `inactive` | ⚪ Gray | Sensor is off (not collecting) |
| `error` | 🔴 Red | Last attempt failed |
| `offline` | ⚫ Black | Can't reach the sensor |

---

## Things to Keep in Mind

1. **Refresh the list** after adding/deleting/toggling sensors

2. **Show loading states** when making API calls

3. **Handle errors nicely** - show the error message from the API

4. **Confirm before delete** - accidents happen!

5. **Format timestamps** - "2 minutes ago" is nicer than "2026-01-06T03:08:42Z"

6. **The token is sensitive** - don't display it after the sensor is created

7. **Water Quality and Mayfly aren't implemented yet** - the buttons should either be disabled or show "Coming Soon"

---

## Testing Your Frontend

1. Start the backend:
   ```bash
   cd backend
   source venv/bin/activate
   uvicorn app.main:app --reload --port 8000
   ```

2. Add a sensor through your UI

3. Turn it on

4. Click "Fetch Now" to test

5. Check the status - did it work?

6. Try turning it off and deleting it

If everything works, you're golden! 🎉

---

## Questions?

The backend code is super well-documented. Check out:
- `backend/app/routers/sensors.py` - all the endpoints
- `backend/app/models/sensor.py` - all the data structures
- `backend/app/services/sensor_manager.py` - how everything works

Or just hit http://localhost:8000/docs for the interactive API docs.

Good luck! You got this! 💪
