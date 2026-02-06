# Deployment to Production (Ethan's Machine) - Sleep Duration Feature

## Overview
Deploy the sleep duration control feature to production server via Cloudflare tunnel.

**Branch**: `optimize-sleep-cycle`  
**Production URL**: `https://sensor-dashboard.environmentaldashboard.org`  
**Backend Machine**: Ethan's computer (via Cloudflare tunnel)

---

## Prerequisites

- Access to Ethan's machine (Windows)
- Cloudflare tunnel configured and running
- Backend currently running on Ethan's machine
- Git repository access

---

## Part 1: Deploy Backend on Ethan's Machine

### Step 1: Connect to Ethan's Machine

**Option A: Remote Desktop**
```
Connect via RDP or TeamViewer to Ethan's Windows machine
```

**Option B: SSH (if configured)**
```bash
ssh ethan@sensor-dashboard.environmentaldashboard.org
```

### Step 2: Navigate to Project Directory

```powershell
cd C:\path\to\sensor-data-collector
# Or wherever the project is located on Ethan's machine
```

### Step 3: Pull Latest Changes

```powershell
# Check current branch
git branch

# Fetch latest changes
git fetch origin

# Checkout the feature branch
git checkout optimize-sleep-cycle

# Pull latest commits
git pull origin optimize-sleep-cycle

# Verify you have the latest commit
git log -1 --oneline
# Should show: "Fix authentication requirement in deployment docs..."
```

### Step 4: Verify Backend Changes

Check that the new files exist:

```powershell
# Check if new endpoint exists
type backend\app\routers\sensors.py | findstr "sleep-interval"

# Should show the new endpoint function
```

### Step 5: Stop Backend Service

**If using Windows Task Scheduler:**
```powershell
# Find running Python processes
Get-Process python | Where-Object {$_.Path -like "*sensor-data-collector*"}

# Stop the process (replace PID with actual process ID)
Stop-Process -Id <PID> -Force
```

**If using a service:**
```powershell
Stop-Service -Name "SensorBackend"
```

### Step 6: Restart Backend

**Using PowerShell script:**
```powershell
cd backend
.\start-backend.ps1
```

**Or manually:**
```powershell
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Step 7: Verify Backend is Running

```powershell
# Test health endpoint
curl http://localhost:8000/health

# Should return: {"status":"healthy","polling_interval":60}

# Test sensors endpoint
curl http://localhost:8000/api/sensors/

# Should return list of sensors
```

### Step 8: Verify Cloudflare Tunnel

```powershell
# Check if cloudflared is running
Get-Process cloudflared

# If not running, start it
cd cloudflared
.\start-tunnel.ps1

# Or manually
cloudflared tunnel run sensor-dashboard
```

### Step 9: Test New Endpoint Locally

Get the voltage meter sensor ID from the sensors list:

```powershell
# Get sensors and find voltage meter
curl http://localhost:8000/api/sensors/ | ConvertFrom-Json | Select-Object -ExpandProperty sensors | Where-Object {$_.sensor_type -eq "voltage_meter"}
```

**Expected sensor IDs:**
- Local dev: `dcd5f844-616f-4806-a807-3d442fdac4c6`
- Production (Ethan's machine): Check output above for actual production IDs

Test the new endpoint with the actual sensor ID:

```powershell
# Replace {SENSOR_ID} with actual UUID from above
$body = @{
    sleep_interval_minutes = 15
} | ConvertTo-Json

Invoke-WebRequest -Uri "http://localhost:8000/api/sensors/voltage-meter/{SENSOR_ID}/sleep-interval" `
    -Method POST `
    -ContentType "application/json" `
    -Body $body
```

Expected response:
```json
{
  "status": "ok",
  "sleep_interval_minutes": 15,
  "message": "Sleep interval set to 15 minutes. Will apply on next ESP32 wake cycle."
}
```

### Step 10: Test Via Cloudflare Tunnel

```powershell
# Test through public URL
$body = @{
    sleep_interval_minutes = 15
} | ConvertTo-Json

Invoke-WebRequest -Uri "https://sensor-dashboard.environmentaldashboard.org/api/sensors/voltage-meter/{SENSOR_ID}/sleep-interval" `
    -Method POST `
    -ContentType "application/json" `
    -Body $body
```

---

## Part 2: Deploy Frontend to Vercel

### Option A: Automatic Deployment (Recommended)

1. **Merge to main branch** (from your local machine):

```bash
# On your machine
cd /Users/MenardSimoya/Desktop/E-Dashboard/sensor-data-collector

# Checkout main
git checkout main

# Merge feature branch
git merge optimize-sleep-cycle

# Push to GitHub
git push origin main
```

2. **Vercel auto-deploys** from main branch
   - Monitor: https://vercel.com/menards-projects/frontend/deployments
   - Production URL: `https://sensor-dashboard.environmentaldashboard.org`
   - Deployment takes ~2-3 minutes

3. **Verify deployment**:
   - Check Vercel dashboard for successful deployment
   - Green checkmark = deployed successfully

### Option B: Manual Deployment (If auto-deploy fails)

```bash
# On your machine
cd frontend

# Install Vercel CLI if needed
npm install -g vercel

# Login to Vercel
vercel login

# Deploy to production
vercel --prod

# Follow prompts to confirm production deployment
```

### Step 11: Update Frontend Environment Variables (Vercel)

The frontend needs to point to the production backend URL.

1. Go to: https://vercel.com/menards-projects/frontend/settings/environment-variables

2. Update or add `VITE_API_URL`:
   - **Variable**: `VITE_API_URL`
   - **Value**: `https://sensor-dashboard.environmentaldashboard.org`
   - **Environment**: Production

3. **Redeploy** after updating env vars:
   - Go to Deployments tab
   - Click "Redeploy" on latest deployment

---

## Part 3: Get Production Sensor IDs

### Step 1: Access Production Dashboard

Navigate to: `https://sensor-dashboard.environmentaldashboard.org`

### Step 2: Find Voltage Meters

1. Look for voltage meter sensors in the dashboard
2. Click the ⋮ menu → "Edit Sensor"
3. Copy the Sensor ID (UUID format)

**Common Production Voltage Meters:**
- Check the dashboard for actual voltage meters
- Look for sensors with type "Voltage Meter"
- Note their IDs and names

### Step 3: Document Sensor IDs

Create a reference list:

```
Production Voltage Meter Sensor IDs:
─────────────────────────────────────
1. Name: _________________
   ID: _________________
   Location: _________________

2. Name: _________________
   ID: _________________
   Location: _________________

3. Name: _________________
   ID: _________________
   Location: _________________
```

**Example from your local dev:**
- Name: Voltmeter-test
- ID: `dcd5f844-616f-4806-a807-3d442fdac4c6`
- Location: AJLC_002

---

## Part 4: Test Production Frontend

### Step 1: Access Dashboard

Open: `https://sensor-dashboard.environmentaldashboard.org`

### Step 2: Verify Menu Option Appears

1. Find a voltage meter sensor
2. Click the ⋮ menu (three dots)
3. **Verify you see**: "🌙 Set Sleep Duration"

### Step 3: Test Sleep Duration Feature

1. Click "Set Sleep Duration"
2. Modal should open
3. Verify contents:
   - Input field with current interval
   - Quick-select buttons: 5min, 15min, 30min, 1h, 2h, 6h
   - "Current: X minutes" text
   - Cancel and "Set Duration" buttons

### Step 4: Set a Test Value

1. Click "5 min" quick-select button (for quick testing)
2. Click "Set Duration"
3. **Verify**:
   - Success toast appears: "Sleep interval set to 5 minutes — will apply on next device check-in"
   - Modal closes
   - No errors in browser console (F12)

### Step 5: Verify Backend Received Update

On Ethan's machine:

```powershell
# Check backend logs
# Should show POST request to /api/sensors/voltage-meter/{id}/sleep-interval

# Or query the sensor directly
curl http://localhost:8000/api/sensors/ | ConvertFrom-Json | 
  Select-Object -ExpandProperty sensors | 
  Where-Object {$_.sensor_type -eq "voltage_meter"} |
  Select-Object name, sleep_interval_minutes
```

Should show `sleep_interval_minutes: 5`

---

## Part 5: Update ESP32 Firmware with Production Credentials

### Step 1: Locate Firmware File

File: `/Users/MenardSimoya/Desktop/E-Dashboard/sensor-data-collector/ESP32_Battery_Monitor_v2.1.ino`

### Step 2: Update Configuration for Production

Open the firmware and update these lines:

```cpp
// WiFi Credentials
const char* WIFI_SSID = "ObieConnect";  // Or production WiFi SSID
const char* WIFI_PASS = "your_actual_password";

// API Configuration - PRODUCTION
const char* API_ENDPOINT = "https://sensor-dashboard.environmentaldashboard.org/api/esp32/voltage";

// Sensor Credentials - GET FROM PRODUCTION DASHBOARD
const char* SENSOR_ID = "PRODUCTION_SENSOR_UUID_HERE";  // ← Replace with actual production sensor ID
const char* UPLOAD_TOKEN = "PRODUCTION_UPLOAD_TOKEN_HERE";  // ← Get from dashboard when adding sensor
```

### Step 3: Get Production Sensor Credentials

**To add a new voltage meter or get existing credentials:**

1. Go to: `https://sensor-dashboard.environmentaldashboard.org`
2. Click "Add Sensor" → "Voltage Meter"
3. Fill in details:
   - Name: e.g., "Purple Air Voltmeter 002"
   - Location: e.g., "AJLC_002"
   - **Leave IP address blank** (POST-only mode)
4. Click "Add Sensor"
5. **Copy the credentials shown**:
   - `sensor_id`: UUID (e.g., `3601f5be-0db8-45b1-9429-00e8053c4852`)
   - `upload_token`: (e.g., `P72mNb8QuixpWRv3zEKnLf456tM9X1`)

### Step 4: Update Firmware with Credentials

Replace in firmware:

```cpp
const char* SENSOR_ID = "3601f5be-0db8-45b1-9429-00e8053c4852";  // ← Your actual production sensor ID
const char* UPLOAD_TOKEN = "P72mNb8QuixpWRv3zEKnLf456tM9X1";  // ← Your actual upload token
```

### Step 5: Upload Firmware to ESP32

1. Open Arduino IDE
2. Load `ESP32_Battery_Monitor_v2.1.ino`
3. Select board: "ESP32 Dev Module"
4. Select port: (your USB port)
5. Click "Upload"
6. Wait for upload to complete (~30-60 seconds)

### Step 6: Monitor First Boot

1. Open Serial Monitor (115200 baud)
2. Watch for output:

```
========================================
  Battery Monitor v2.1
  Power Optimized + Dashboard Control
========================================
...
[4] Communicating with backend...
Posting data to backend...
URL: https://sensor-dashboard.environmentaldashboard.org/api/esp32/voltage
HTTP Response: 200
Response: {"status":"ok",...,"commands":{"sleep_interval_minutes":15,...}}
Processing commands from backend...
  No changes needed (or shows sleep interval update)
Communication successful!
...
Sleeping for 15 minutes...
```

### Step 7: Verify in Dashboard

1. Go to: `https://sensor-dashboard.environmentaldashboard.org`
2. Find your voltage meter
3. **Verify**:
   - Status changes from "inactive" to "active"
   - Voltage reading appears
   - Last active timestamp updates
   - Sleep interval shows 15 minutes (or your set value)

---

## Part 6: End-to-End Testing

### Test 1: Change Sleep Interval from Dashboard

1. Dashboard → Voltage Meter → ⋮ → "Set Sleep Duration"
2. Set to **5 minutes** (for quick testing)
3. Click "Set Duration"
4. Success toast appears

### Test 2: ESP32 Receives New Interval

1. **Wait for current sleep cycle to complete** (check ESP32 Serial Monitor)
2. ESP32 wakes up (~15 minutes from last wake, based on old interval)
3. **Serial Monitor should show**:
   ```
   Processing commands from backend...
     Sleep interval: 15 -> 5 minutes
   Sleeping for 5 minutes...
   ```

### Test 3: Verify New Interval Applied

1. **Wait 5 minutes** (not 15!)
2. ESP32 should wake up again
3. Serial Monitor shows new cycle
4. Dashboard timestamp updates (~5 minutes after previous update)

### Test 4: Test Persistence

1. **Power cycle the ESP32** (disconnect/reconnect USB or battery)
2. Watch Serial Monitor on restart
3. Should show:
   ```
   Settings loaded from NVS:
     Wake interval: 5 min  ← Should show 5, not 15
   ```
4. Confirms setting persists across power cycles

---

## Part 7: Rollback Plan (If Issues Occur)

### Backend Rollback

On Ethan's machine:

```powershell
cd C:\path\to\sensor-data-collector

# Checkout previous stable branch
git checkout main

# Restart backend
cd backend
.\start-backend.ps1
```

### Frontend Rollback

1. Go to Vercel: https://vercel.com/menards-projects/frontend/deployments
2. Find previous successful deployment
3. Click "..." → "Redeploy"
4. Select "Redeploy with current configuration"

### ESP32 Rollback

Upload previous firmware version (v2.0) without sleep interval command processing.

---

## Verification Checklist

### Backend (Ethan's Machine)
- [ ] Git pulled latest changes from `optimize-sleep-cycle`
- [ ] Backend restarted successfully
- [ ] Health endpoint responds: `curl http://localhost:8000/health`
- [ ] New endpoint works: POST `/api/sensors/voltage-meter/{id}/sleep-interval`
- [ ] Cloudflare tunnel running
- [ ] Public URL accessible: `https://sensor-dashboard.environmentaldashboard.org`

### Frontend (Vercel)
- [ ] Deployed to production (auto or manual)
- [ ] Environment variable `VITE_API_URL` set correctly
- [ ] Dashboard loads: `https://sensor-dashboard.environmentaldashboard.org`
- [ ] "Set Sleep Duration" menu item visible for voltage meters
- [ ] Modal opens and displays correctly
- [ ] Success toast appears when setting duration
- [ ] No console errors (F12)

### ESP32 Firmware
- [ ] Firmware v2.1 uploaded
- [ ] Production credentials configured (SENSOR_ID, UPLOAD_TOKEN)
- [ ] API_ENDPOINT points to production URL
- [ ] Serial Monitor shows successful POST (HTTP 200)
- [ ] ESP32 receives commands from backend
- [ ] Sleep interval updates as expected
- [ ] Dashboard shows active status and voltage readings

### Integration
- [ ] Dashboard → Set sleep interval → ESP32 receives command
- [ ] ESP32 applies new interval on next wake
- [ ] New interval persists across ESP32 power cycles
- [ ] Dashboard timestamp updates match new sleep interval
- [ ] All features work together (relay control, thresholds, calibration, sleep interval)

---

## Production Sensor IDs Reference

**Fill in after deployment:**

### Voltage Meters on Production

| Name | Sensor ID | Location | Upload Token | Notes |
|------|-----------|----------|--------------|-------|
| Example | `3601f5be-...` | AJLC_002 | `P72mNb8...` | Purple Air voltmeter |
| ______ | __________ | ________ | _________ | _____ |
| ______ | __________ | ________ | _________ | _____ |

**To get sensor info from production:**

```powershell
# On Ethan's machine
curl http://localhost:8000/api/sensors/ | ConvertFrom-Json | 
  Select-Object -ExpandProperty sensors | 
  Where-Object {$_.sensor_type -eq "voltage_meter"} |
  Format-Table name, id, location -AutoSize
```

**To get sensor from dashboard:**
1. Dashboard → Voltage Meter → ⋮ → "Edit Sensor"
2. Sensor ID shown in modal
3. Upload token shown when first created (store securely!)

---

## Troubleshooting

### Issue: Backend endpoint returns 404

**Symptoms:**
```
curl https://sensor-dashboard.environmentaldashboard.org/api/sensors/voltage-meter/{id}/sleep-interval
{"detail":"Not Found"}
```

**Solution:**
1. Verify backend pulled latest code: `git log -1 --oneline`
2. Restart backend service
3. Check Cloudflare tunnel is running: `Get-Process cloudflared`

### Issue: ESP32 gets 404 when POSTing

**Symptoms:**
```
HTTP Response: 404
{"detail":"Sensor not found. Check sensor_id."}
```

**Solution:**
1. Verify sensor ID exists in production
2. Check upload token matches
3. Ensure sensor was created on production (not just local dev)

### Issue: ESP32 not receiving new sleep interval

**Symptoms:**
- Dashboard shows sleep interval changed
- ESP32 still using old interval

**Solution:**
1. Wait for current sleep cycle to complete
2. Changes apply on **next wake**, not immediately
3. Check Serial Monitor for "Processing commands" message
4. Verify `sleep_interval_minutes` in POST response

### Issue: Frontend menu blank or "Set Sleep Duration" missing

**Symptoms:**
- Menu shows blank when clicking ⋮
- Or "Set Sleep Duration" option not visible

**Solution:**
1. Hard refresh: Ctrl+Shift+R (Windows) or Cmd+Shift+R (Mac)
2. Clear browser cache
3. Check browser console (F12) for JavaScript errors
4. Verify Vercel deployment succeeded
5. Check if frontend is using correct backend URL

---

## Success Criteria

✅ Backend deployed and running on Ethan's machine  
✅ New endpoint accessible via Cloudflare tunnel  
✅ Frontend deployed to Vercel with "Set Sleep Duration" feature  
✅ ESP32 firmware uploaded with production credentials  
✅ ESP32 successfully POSTs to production backend  
✅ Dashboard can set sleep interval for voltage meters  
✅ ESP32 receives and applies new sleep interval  
✅ New interval persists across ESP32 power cycles  
✅ Dashboard updates reflect new sleep interval timing  

---

## Contact & Support

**Deployment Date**: _________________  
**Deployed By**: Menard Simoya  
**Backend Location**: Ethan's Machine (Cloudflare Tunnel)  
**Production URL**: https://sensor-dashboard.environmentaldashboard.org  
**Feature**: Remote Sleep Duration Control for ESP32 Voltage Meters  
**Version**: Backend/Frontend (same), ESP32 Firmware v2.1  

**For issues:**
1. Check this deployment guide
2. Review DEPLOYMENT_SLEEP_DURATION.md for detailed troubleshooting
3. Check backend logs on Ethan's machine
4. Review Vercel deployment logs
5. Monitor ESP32 Serial output

---

## Next Steps After Deployment

1. **Monitor for 24 hours**
   - Check dashboard regularly
   - Verify ESP32 check-ins at expected intervals
   - Watch for any errors in backend logs

2. **Test with different intervals**
   - Try 5 min, 15 min, 30 min, 1 hour
   - Verify each works as expected

3. **Deploy to remaining ESP32 devices**
   - Update firmware on all voltage meters
   - Use production credentials for each

4. **Document sensor IDs**
   - Keep record of all production sensor IDs
   - Store upload tokens securely

5. **Merge to main** (if not already done)
   ```bash
   git checkout main
   git merge optimize-sleep-cycle
   git push origin main
   ```

6. **Tag release** (optional)
   ```bash
   git tag -a v2.1.0 -m "Add sleep duration control feature"
   git push origin v2.1.0
   ```
