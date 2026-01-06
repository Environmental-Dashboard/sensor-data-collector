' Sensor Data Collector - Hidden Startup Script
' Double-click this file to start backend and tunnel without showing windows

Set WshShell = CreateObject("WScript.Shell")
scriptDir = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)

' Start the backend server hidden
WshShell.Run "powershell -ExecutionPolicy Bypass -WindowStyle Hidden -File """ & scriptDir & "\start-backend.ps1""", 0, False

' Wait 5 seconds for backend to start
WScript.Sleep 5000

' Start the Cloudflare tunnel hidden
WshShell.Run "powershell -ExecutionPolicy Bypass -WindowStyle Hidden -File """ & scriptDir & "\start-tunnel.ps1""", 0, False
