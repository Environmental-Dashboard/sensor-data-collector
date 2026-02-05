# Option B: ESP32 Outbound POST to Backend

This document describes how to implement **Option B**: ESP32 wakes, reads voltage, POSTs to your backend at oberlin.communityhub.cloud (or your tunnel URL), then controls the relay and sleeps. You get remote monitoring on the dashboard.

---

## 1. Endpoint URL

Use **one** of these, depending on where the backend is reachable:

| Deployment | URL |
|------------|-----|
| **Backend exposed via Cloudflare tunnel** (recommended) | `https://<your-tunnel-host>/api/esp32/voltage` |
| **Backend hosted at Community Hub** | `https://oberlin.communityhub.cloud/api/esp32/voltage` |
| **Local testing** | `http://localhost:8000/api/esp32/voltage` |

Example for a tunnel host like `abc123.trycloudflare.com`:

```
https://abc123.trycloudflare.com/api/esp32/voltage
```

If you later deploy this FastAPI app under oberlin.communityhub.cloud, the path is:

```
https://oberlin.communityhub.cloud/api/esp32/voltage
```

---

## 2. Authentication

Send your **upload token** in a header. This is the same token you use when adding the voltage meter in the dashboard (from oberlin.communityhub.cloud).

| Header name | Value | Required |
|-------------|--------|----------|
| `user-token` | Your upload token (string) | **Yes** |

Example (curl):

```bash
curl -X POST "https://<your-backend-url>/api/esp32/voltage" \
  -H "Content-Type: application/json" \
  -H "user-token: YOUR_UPLOAD_TOKEN_HERE" \
  -d '{"sensor_id":"550e8400-e29b-41d4-a716-446655440000","voltage_v":12.45}'
```

Example (ESP32 / Arduino):

- Set a header: `user-token: <your_upload_token>`.
- No API key or Bearer token is required; `user-token` is the only auth.

---

## 3. JSON Payload Format

**Content-Type:** `application/json`

### Required fields

| Field | Type | Description |
|-------|------|-------------|
| `sensor_id` | string (UUID) | The voltage meter sensor ID from the dashboard (from when you added the device). |
| `voltage_v` | number | Battery voltage in volts (e.g. `12.45`). Allowed range: 0–20 V. |

### Optional fields (for dashboard display and CSV)

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `load_on` | boolean | `false` | Is the relay/load currently ON? |
| `auto_mode` | boolean | `true` | Is the relay in auto mode? |
| `v_cutoff` | number | `12.0` | Cutoff voltage (V). |
| `v_reconnect` | number | `12.9` | Reconnect voltage (V). |
| `calibration_factor` | number | `1.0` | ADC calibration factor. |
| `cycle_count` | integer | `0` | Total relay cycle count. |
| `turn_on_count_48h` | integer | `0` | Relay on-cycles in last 48 hours. |
| `uptime_ms` | integer | `0` | Device uptime in milliseconds. |

### Example minimal payload (ESP32)

```json
{
  "sensor_id": "550e8400-e29b-41d4-a716-446655440000",
  "voltage_v": 12.45
}
```

### Example full payload (recommended for best dashboard/CSV)

```json
{
  "sensor_id": "550e8400-e29b-41d4-a716-446655440000",
  "voltage_v": 12.45,
  "load_on": false,
  "auto_mode": true,
  "v_cutoff": 11.0,
  "v_reconnect": 12.6,
  "calibration_factor": 1.02,
  "cycle_count": 42,
  "turn_on_count_48h": 5,
  "uptime_ms": 123456
}
```

---

## 4. Response

**Success (200 OK):**

```json
{
  "status": "ok",
  "sensor_id": "550e8400-e29b-41d4-a716-446655440000",
  "voltage_v": 12.45,
  "uploaded_at": "2026-02-04T14:30:00.123456"
}
```

**Errors:**

- **401** – Missing or invalid `user-token` (wrong or not sent).
- **400** – Invalid `sensor_id` format or `voltage_v` out of range.
- **404** – `sensor_id` not found (wrong UUID or sensor deleted).
- **502** – Backend could not upload to Community Hub.

---

## 5. Flow Summary

1. **ESP32** wakes (e.g. from timer or deep sleep).
2. **ESP32** reads voltage (and optionally relay state, thresholds, etc.).
3. **ESP32** POSTs to `https://<your-backend>/api/esp32/voltage` with header `user-token: <upload_token>` and JSON body (at least `sensor_id`, `voltage_v`).
4. **Backend** checks auth, finds the voltage meter sensor, builds CSV, uploads to Community Hub, updates dashboard state.
5. **ESP32** can then control the relay (on/off/auto) and go back to sleep.

The dashboard will show the latest voltage and relay state from these POSTs.

---

## 6. Getting `sensor_id` and `upload_token`

1. In the dashboard, add a **Voltage Meter** (ESP32) with the device’s IP, location, and your **upload token**.
2. After adding, the dashboard shows the sensor’s **ID** (UUID). Use this as `sensor_id` in the POST body.
3. Use the same **upload token** you entered as the `user-token` header.

You can also read the sensor ID from the API: `GET /api/sensors/voltage-meter` and use the `id` field of the matching device.
