# Deployment Instructions: Sleep Duration Control Feature

## Overview
This deployment adds remote sleep duration control for ESP32 voltage meters, allowing users to configure the deep sleep interval (1-1440 minutes) from the dashboard instead of hardcoding it in firmware.

**Branch**: `optimize-sleep-cycle`  
**Commit**: `50ba264` - "Add remote sleep duration control for ESP32 voltage meters"

---

## Prerequisites
- Backend running Python 3.8+ with FastAPI
- Frontend built with React + Vite
- ESP32 voltage meters with Arduino framework
- Access to production server (`sensor-dashboard.environmentaldashboard.org`)

---

## Part 1: Backend Deployment (Production Server)

### Option A: If Running on Ethan's Machine or Remote Server

1. **SSH into the production server** (or access it locally):
   ```bash
   ssh user@sensor-dashboard.environmentaldashboard.org
   ```

2. **Navigate to the project directory**:
   ```bash
   cd /path/to/sensor-data-collector
   ```

3. **Pull the latest changes**:
   ```bash
   git fetch origin
   git checkout optimize-sleep-cycle
   git pull origin optimize-sleep-cycle
   ```

4. **Verify Python dependencies** (should be unchanged, but check):
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

5. **Restart the backend service**:
   
   **If using systemd service:**
   ```bash
   sudo systemctl restart sensor-backend
   sudo systemctl status sensor-backend
   ```
   
   **If using Windows Task Scheduler (PowerShell):**
   ```powershell
   # Stop any running backend processes
   Get-Process -Name python | Where-Object {$_.Path -like "*sensor-data-collector*"} | Stop-Process
   
   # Restart using your start script
   cd C:\path\to\sensor-data-collector\backend
   .\start-backend.ps1
   ```
   
   **If running manually:**
   ```bash
   # Stop current process (Ctrl+C or kill PID)
   cd backend
   python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

6. **Verify backend is running**:
   ```bash
   curl http://localhost:8000/api/sensors
   ```
   Should return sensor list without errors.

7. **Test the new endpoint**:
   ```bash
   curl -X POST http://localhost:8000/api/sensors/voltage-meter/{SENSOR_ID}/sleep-interval \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer YOUR_JWT_TOKEN" \
     -d '{"sleep_interval_minutes": 15}'
   ```
   Should return: `{"status": "ok", "sleep_interval_minutes": 15, ...}`

---

## Part 2: Frontend Deployment (Vercel)

### Option A: Automatic Deployment via Git Push

1. **Merge to main branch** (if not already):
   ```bash
   git checkout main
   git merge optimize-sleep-cycle
   git push origin main
   ```

2. **Vercel will auto-deploy** (check your Vercel dashboard)
   - Monitor: https://vercel.com/your-project/deployments
   - Production URL: `sensor-dashboard.environmentaldashboard.org`

### Option B: Manual Deployment

1. **Navigate to frontend directory**:
   ```bash
   cd frontend
   ```

2. **Install dependencies** (if needed):
   ```bash
   npm install
   ```

3. **Build for production**:
   ```bash
   npm run build
   ```

4. **Deploy to Vercel**:
   ```bash
   vercel --prod
   ```

5. **Verify deployment**:
   ```bash
   curl https://sensor-dashboard.environmentaldashboard.org/
   ```

---

## Part 3: ESP32 Firmware Upload

### Step 1: Prepare Firmware

1. **Locate the firmware file**:
   - File: `/Users/MenardSimoya/Desktop/E-Dashboard/sensor-data-collector/ESP32_Battery_Monitor_v2.1.ino`

2. **Open in Arduino IDE** or **PlatformIO**

3. **Update WiFi credentials** in the code:
   ```cpp
   const char* WIFI_SSID = "YourWiFiSSID";
   const char* WIFI_PASS = "YourWiFiPassword";
   ```

4. **Verify API endpoint** (should point to production):
   ```cpp
   const char* API_ENDPOINT = "https://sensor-dashboard.environmentaldashboard.org/api/esp32/voltage";
   ```

5. **Update sensor credentials** (from dashboard when you added the device):
   ```cpp
   const char* SENSOR_ID = "your-sensor-uuid-here";
   const char* UPLOAD_TOKEN = "your-upload-token-here";
   ```

### Step 2: Upload Firmware

1. **Connect ESP32** via USB cable

2. **Select board and port** in Arduino IDE:
   - Board: "ESP32 Dev Module"
   - Port: (select your COM port or /dev/ttyUSB0)

3. **Compile and upload**:
   - Click "Upload" button (→ arrow icon)
   - Wait for compilation and upload (~30-60 seconds)

4. **Open Serial Monitor** (Tools → Serial Monitor):
   - Baud rate: 115200
   - Watch the boot sequence

### Step 3: Verify First Boot

Expected Serial Monitor output:
```
========================================
  Battery Monitor v2.1
  Power Optimized + Dashboard Control
========================================
Restored relay state: ON
Settings loaded from NVS:
  Calibration factor: 1.0000
  Wake interval: 15 min
  V_cutoff: 12.00 V
  V_reconnect: 12.60 V
  Relay mode: automatic

[1] Reading voltage...
Battery: 12.45 V (factor: 1.0000)

[2] Connecting WiFi...
Connected! IP: 192.168.1.123

[3] Syncing time...
Time: 2026-02-04 14:30

[4] Communicating with backend...
Posting data to backend...
Payload: {"sensor_id":"...","voltage_v":12.45,...}
HTTP Response: 200
Response: {"status":"ok",...}
Communication successful!

[5] Applying relay logic...
Load state: ON

[6] Entering deep sleep...
Sleeping for 15 minutes...
========================================
```

---

## Part 4: Testing the Feature

### Test 1: Access Dashboard

1. Navigate to: `https://sensor-dashboard.environmentaldashboard.org`
2. Log in with your credentials
3. Locate your voltage meter in the sensor list

### Test 2: Set Sleep Duration

1. **Click the three-dot menu** (⋮) on your voltage meter card
2. **Select "Set Sleep Duration"** (moon icon)
3. **Modal should open** showing:
   - Current sleep interval (e.g., "Current: 15 minutes")
   - Input field for custom duration
   - Quick-select buttons: 5min, 15min, 30min, 1h, 2h, 6h

### Test 3: Change Sleep Duration

1. **Click "5 min"** quick-select button
2. **Click "Set Duration"**
3. **Verify success toast**: "Sleep interval set to 5 minutes — will apply on next device check-in"

### Test 4: Verify ESP32 Receives Command

1. **Monitor ESP32 Serial Monitor** (keep it connected via USB)
2. **Wait for next wake cycle** (should be ~15 minutes initially, then 5 minutes after change)
3. **Look for this output**:
   ```
   Processing commands from backend...
     Sleep interval: 15 -> 5 minutes
   ```

### Test 5: Confirm New Interval Applied

1. **Wait 5 minutes** (instead of previous 15)
2. **ESP32 should wake** and POST data again
3. **Check Serial Monitor**:
   ```
   Sleeping for 5 minutes...
   ```
4. **Check dashboard** - timestamp should update every 5 minutes

### Test 6: Test Range Validation

1. Try setting **0 minutes** → should reject (minimum 1)
2. Try setting **2000 minutes** → should reject (maximum 1440 = 24 hours)
3. Try setting **30 minutes** → should accept

---

## Part 5: Migration of Existing Sensors

Existing voltage meters will automatically receive default values on next backend restart:

```python
# Automatically applied by sensor_manager.py:
sleep_interval_minutes: 15  # Default: 15 minutes
```

No manual database migration needed - the backend handles this transparently.

---

## Rollback Plan

If issues occur:

### Backend Rollback
```bash
cd /path/to/sensor-data-collector
git checkout main  # or previous stable branch
# Restart backend service
```

### Frontend Rollback
```bash
cd frontend
git checkout main
npm run build
vercel --prod
```

### ESP32 Rollback
- Upload previous firmware version (v2.0)
- ESP32 will continue using last saved `wake_interval` from NVS

---

## Monitoring

### Check Backend Logs
```bash
tail -f /path/to/backend/logs/app.log
```

Look for:
- `POST /api/sensors/voltage-meter/{id}/sleep-interval` requests
- `POST /api/esp32/voltage` responses with `sleep_interval_minutes`

### Check ESP32 Logs
Monitor Serial output for:
- `Sleep interval: X -> Y minutes` (command received)
- `Sleeping for Y minutes...` (new interval applied)

### Check Dashboard
- Voltage meter cards should update at new intervals
- No "Device not reachable" errors for POST-only devices

---

## Troubleshooting

### Issue: Sleep Duration modal doesn't appear
- **Cause**: Frontend not deployed or cached
- **Fix**: Hard refresh (Ctrl+Shift+R) or clear browser cache

### Issue: ESP32 not receiving new sleep interval
- **Cause**: Backend not restarted or ESP32 not connecting
- **Fix**: 
  1. Verify backend is running: `curl http://localhost:8000/api/sensors`
  2. Check ESP32 Serial Monitor for WiFi connection
  3. Verify `sleep_interval_minutes` in POST response

### Issue: ESP32 still using old interval
- **Cause**: Change takes effect on *next* wake cycle
- **Fix**: Wait for current sleep cycle to complete (check Serial Monitor timestamp)

### Issue: Backend returns 404 on sleep-interval endpoint
- **Cause**: Backend code not updated
- **Fix**: 
  ```bash
  git pull origin optimize-sleep-cycle
  # Restart backend
  ```

---

## Success Criteria

✅ Backend endpoint `/api/sensors/voltage-meter/{id}/sleep-interval` returns 200 OK  
✅ Frontend shows "Set Sleep Duration" option in voltage meter menu  
✅ Modal opens with input and quick-select buttons  
✅ Success toast appears after setting duration  
✅ ESP32 Serial Monitor shows "Sleep interval: X -> Y minutes"  
✅ ESP32 wakes at new interval (visible in dashboard timestamp updates)  
✅ New interval persists across ESP32 power cycles (stored in NVS)  

---

## Summary of Changes

| Component | Files Changed | Lines Added |
|-----------|--------------|-------------|
| Backend | 4 files | ~40 lines |
| Frontend | 3 files | ~120 lines |
| ESP32 Firmware | 1 file (new v2.1) | ~30 lines modified |

**Total**: 7 files, 160+ lines of new functionality

---

## Contact

If you encounter issues during deployment:
1. Check this document's troubleshooting section
2. Review commit `50ba264` for detailed changes
3. Check backend/frontend logs for error messages

**Deployed by**: Menard Simoya  
**Date**: February 4, 2026  
**Feature**: Remote Sleep Duration Control for ESP32 Voltage Meters
