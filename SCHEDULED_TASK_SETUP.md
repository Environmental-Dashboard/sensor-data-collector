# Windows Scheduled Task Setup

This guide shows you how to set up a Windows Scheduled Task that runs your backend and tunnel continuously, even when you're not logged in.

## Method 1: Automated Setup (Recommended)

### Step 1: Run PowerShell as Administrator

1. Press `Win + X`
2. Select "Windows PowerShell (Admin)" or "Terminal (Admin)"
3. Click "Yes" when prompted by UAC

### Step 2: Navigate to Project Directory

```powershell
cd c:\Users\ethan\sensor_data_collector
```

### Step 3: Run Setup Script

```powershell
powershell -ExecutionPolicy Bypass -File setup-scheduled-task.ps1
```

The script will:
- Create a scheduled task named "SensorDataCollector"
- Configure it to run at Windows startup
- Set it to run as SYSTEM (works even when not logged in)
- Enable automatic restart if it fails
- Start the task immediately (if you choose)

## Method 2: Manual Setup via Task Scheduler GUI

### Step 1: Open Task Scheduler

1. Press `Win + R`
2. Type `taskschd.msc` and press Enter

### Step 2: Create Basic Task

1. Click "Create Basic Task..." in the right panel
2. Name: `SensorDataCollector`
3. Description: `Runs backend and tunnel continuously`
4. Click "Next"

### Step 3: Set Trigger

1. Select "When the computer starts"
2. Click "Next"

### Step 4: Set Action

1. Select "Start a program"
2. Click "Next"
3. Program/script: `powershell.exe`
4. Add arguments: `-ExecutionPolicy Bypass -NoProfile -File "c:\Users\ethan\sensor_data_collector\backend\run-continuously.ps1"`
5. Start in: `c:\Users\ethan\sensor_data_collector`
6. Click "Next"

### Step 5: Configure Settings

1. Check "Open the Properties dialog for this task when I click Finish"
2. Click "Finish"

### Step 6: Advanced Settings

In the Properties dialog:

1. **General Tab:**
   - Check "Run whether user is logged on or not"
   - Check "Run with highest privileges"
   - Configure for: Windows 10/11

2. **Triggers Tab:**
   - Edit the trigger
   - Check "Enabled"
   - Advanced settings: Check "Repeat task every" → 1 hour (optional, for redundancy)

3. **Actions Tab:**
   - Verify the action is correct

4. **Conditions Tab:**
   - Uncheck "Start the task only if the computer is on AC power"
   - Check "Start the task only if the following network connection is available"

5. **Settings Tab:**
   - Check "Allow task to be run on demand"
   - Check "Run task as soon as possible after a scheduled start is missed"
   - Check "If the task fails, restart every" → 1 minute
   - Set "Attempt to restart up to" → 3 times
   - Check "If the running task does not end when requested, force it to stop"

6. Click "OK" and enter your password if prompted

## Managing the Task

### Start the Task

```powershell
Start-ScheduledTask -TaskName "SensorDataCollector"
```

### Stop the Task

```powershell
Stop-ScheduledTask -TaskName "SensorDataCollector"
```

### Check Status

```powershell
Get-ScheduledTask -TaskName "SensorDataCollector"
```

### View Task History

1. Open Task Scheduler
2. Find "SensorDataCollector" in the task list
3. Click "History" tab at bottom

### Remove the Task

```powershell
Unregister-ScheduledTask -TaskName "SensorDataCollector" -Confirm:$false
```

## Logs

The continuous runner script logs to:
- `backend\continuous.log` - Main monitoring log
- `backend\backend.log` - Backend server log
- `backend\tunnel.log` - Tunnel log

## What It Does

The `run-continuously.ps1` script:
1. Starts the backend server
2. Waits for backend to be ready
3. Starts the Cloudflare tunnel
4. Monitors both processes every 30 seconds
5. Automatically restarts if either process stops

### Automatic Port Cleanup

The `start-backend.ps1` script automatically handles port conflicts:
- **Detects and kills** processes using port 8000
- **Filters invalid PIDs** (like PID 0)
- **Ignores TIME_WAIT connections** (harmless, clear automatically)
- **Verifies processes exist** before attempting to kill them
- **Uses multiple cleanup methods** (Stop-Process, taskkill)
- **Proceeds even with warnings** - attempts to start uvicorn if cleanup isn't perfect

This means you rarely need to manually free port 8000 - the script handles it automatically.

## Troubleshooting

### Task Not Running

1. Check Task Scheduler → History tab for errors
2. Verify the script path is correct
3. Check that PowerShell execution policy allows scripts:
   ```powershell
   Get-ExecutionPolicy
   ```
   If it's "Restricted", run:
   ```powershell
   Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
   ```

### Backend Not Starting

1. **Check logs in order:**
   - `backend\continuous.log` - Main monitoring log (shows startup attempts)
   - `backend\backend.log` - Backend server log (shows detailed startup process)
   - `backend\uvicorn_error.log` - Uvicorn error output (if created)
   - `backend\uvicorn_output.log` - Uvicorn standard output (if created)

2. **Verify Python virtual environment exists:**
   ```powershell
   Test-Path backend\venv\Scripts\python.exe
   ```
   Should return `True`. If `False`, create it:
   ```powershell
   cd backend
   python -m venv venv
   ```

3. **Check for port 8000 conflicts:**
   ```powershell
   Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | Select-Object State, OwningProcess
   ```
   If port is in use, the script will attempt to free it automatically. If it fails:
   ```powershell
   # Find and kill processes on port 8000
   $procs = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique
   $procs | Where-Object { $_ -gt 0 } | ForEach-Object { Stop-Process -Id $_ -Force }
   ```

4. **Verify backend is actually running:**
   ```powershell
   # Check if port 8000 is listening
   Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -TimeoutSec 2
   ```
   Should return status 200. If it times out, backend isn't running.

5. **Common issues:**
   - **Port 8000 blocked:** The script now handles this automatically, but if it persists, manually kill blocking processes (see step 3)
   - **TIME_WAIT connections:** These are harmless and will clear automatically - the script ignores them
   - **Process dies immediately:** Check `uvicorn_error.log` for Python import errors or configuration issues
   - **Python not found:** Verify venv path is correct in `start-backend.ps1`

### Tunnel Not Starting

1. Check `backend\tunnel.log` for errors
2. Verify `cloudflared` is installed and in PATH:
   ```powershell
   cloudflared --version
   ```
   If not installed, download from: https://github.com/cloudflare/cloudflared/releases
3. Test manually: `cloudflared tunnel --url http://localhost:8000`
4. Verify backend is running before tunnel starts (check `backend\continuous.log`)

### Frontend Not Connecting to Backend

1. **Check tunnel URL:**
   ```powershell
   Get-Content backend\tunnel_url.txt
   ```
   Should show a URL like `https://xxxxx.trycloudflare.com`

2. **Verify Vercel environment variable:**
   - Go to https://vercel.com → Your Project → Settings → Environment Variables
   - Check that `VITE_API_URL` matches the tunnel URL from step 1
   - If different, the tunnel script should update it automatically, but you can set it manually

3. **Test tunnel directly:**
   ```powershell
   $tunnelUrl = Get-Content backend\tunnel_url.txt
   Invoke-WebRequest -Uri "$tunnelUrl/health" -UseBasicParsing
   ```
   Should return status 200

4. **Check CORS configuration:**
   - Verify `backend\app\main.py` includes `https://ed-sensor-dashboard.vercel.app` in `CORS_ORIGINS`
   - Restart backend if CORS was changed

5. **Force Vercel redeploy:**
   ```powershell
   cd frontend
   npx vercel --prod
   ```

6. **Check browser console:**
   - Open https://ed-sensor-dashboard.vercel.app
   - Open Developer Tools (F12) → Console
   - Look for CORS errors or connection errors

### Task Runs But Services Don't Start

1. Check if running as SYSTEM user (may have different PATH)
2. Use full paths in scripts instead of relative paths
3. Check Windows Event Viewer for system errors

## Benefits of Scheduled Task vs Startup Folder

✅ Runs even when not logged in  
✅ Automatic restart on failure  
✅ Better monitoring and logging  
✅ Can run as SYSTEM (highest privileges)  
✅ More reliable than Startup folder method
