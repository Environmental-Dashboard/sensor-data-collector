' Sensor Data Collector - Hidden Startup Script
' This script runs both backend and tunnel completely hidden
' Place a shortcut to this in your Startup folder for auto-start

Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)

' Log startup
logFile = scriptDir & "\startup.log"
Set logStream = fso.OpenTextFile(logFile, 8, True)
logStream.WriteLine Now & " - Starting Sensor Data Collector..."
logStream.Close

' Start the backend server hidden (no window at all)
WshShell.Run "powershell -ExecutionPolicy Bypass -WindowStyle Hidden -NoProfile -File """ & scriptDir & "\start-backend.ps1""", 0, False

' Wait 3 seconds before starting tunnel
WScript.Sleep 3000

' Start the Cloudflare tunnel hidden (no window at all)
WshShell.Run "powershell -ExecutionPolicy Bypass -WindowStyle Hidden -NoProfile -File """ & scriptDir & "\start-tunnel.ps1""", 0, False

' Log completion
Set logStream = fso.OpenTextFile(logFile, 8, True)
logStream.WriteLine Now & " - Startup scripts launched"
logStream.Close
