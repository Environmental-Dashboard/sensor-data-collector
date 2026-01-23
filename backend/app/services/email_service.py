"""
Email Notification Service
==========================

Sends email alerts when sensors have errors.

Author: Frank Kusi Appiah
"""

import smtplib
import logging
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone
from typing import Optional, List

logger = logging.getLogger(__name__)


# Datapoints for each sensor type
SENSOR_DATAPOINTS = {
    "purple_air": [
        ("Timestamp", "ISO 8601 datetime"),
        ("Temperature", "°F"),
        ("Humidity", "%"),
        ("Dewpoint", "°F"),
        ("Pressure", "hPa"),
        ("PM1.0", "µg/m³"),
        ("PM2.5", "µg/m³"),
        ("PM10.0", "µg/m³"),
        ("PM2.5 AQI", "index value"),
    ],
    "tempest": [
        ("Timestamp", "ISO 8601 datetime"),
        ("Temperature", "°F"),
        ("Humidity", "%"),
        ("Pressure", "mb"),
        ("Wind Speed", "mph"),
        ("Wind Gust", "mph"),
        ("Wind Direction", "degrees"),
        ("UV Index", "index value"),
        ("Solar Radiation", "W/m²"),
        ("Illuminance", "lux"),
        ("Rain Accumulated", "inches"),
        ("Precipitation Type", "0=none, 1=rain, 2=hail"),
        ("Lightning Strike Count", "count"),
        ("Lightning Distance", "miles"),
        ("Battery", "volts"),
    ],
    "voltage_meter": [
        ("Timestamp", "ISO 8601 datetime"),
        ("Voltage", "V"),
        ("Load On", "0/1 boolean"),
        ("Auto Mode", "0/1 boolean"),
        ("Cutoff Voltage", "V"),
        ("Reconnect Voltage", "V"),
        ("Calibration Factor", "multiplier"),
        ("Cycle Count", "count"),
        ("Cycles 48h", "count"),
        ("Uptime", "ms"),
    ],
}


def get_error_diagnosis(error_message: str, sensor_type: str) -> dict:
    """
    Analyze error message and provide diagnosis with fix suggestions.
    
    Returns:
        {
            "diagnosis": "What's likely wrong",
            "steps": ["Step 1", "Step 2", ...],
            "severity": "high" | "medium" | "low"
        }
    """
    error_lower = error_message.lower()
    
    # Connection errors
    if "cannot connect" in error_lower or "connection" in error_lower:
        if "timeout" in error_lower:
            return {
                "diagnosis": "The sensor is not responding within the expected time. This usually means the device is powered off, the network is slow, or the IP address is wrong.",
                "steps": [
                    "Check if the sensor has power (look for LED lights)",
                    "Verify the sensor is connected to the network (check ethernet/WiFi)",
                    "Ping the IP address from a computer on the same network",
                    "Confirm the IP address hasn't changed (check router DHCP leases)",
                    "If battery-powered, check if battery voltage is sufficient"
                ],
                "severity": "high"
            }
        else:
            return {
                "diagnosis": "Cannot establish a network connection to the sensor. The device may be offline, on a different network, or the IP address may be incorrect.",
                "steps": [
                    "Physically check if the sensor is powered on",
                    "Verify the sensor's IP address in your router's device list",
                    "Ensure your computer/server can reach the sensor's network",
                    "Try accessing the sensor directly via web browser: http://<ip-address>",
                    "Check if any firewall is blocking the connection"
                ],
                "severity": "high"
            }
    
    # Cloud/upload errors
    if "cloud" in error_lower or "upload" in error_lower or "502" in error_lower or "503" in error_lower or "504" in error_lower:
        return {
            "diagnosis": "The CommunityHub cloud service is temporarily unavailable or experiencing issues. Data collection continues locally but uploads are failing.",
            "steps": [
                "Wait 5-10 minutes and the system will retry automatically",
                "Check https://oberlin.communityhub.cloud status",
                "If issue persists, contact CommunityHub support",
                "Data will be uploaded once the service recovers"
            ],
            "severity": "medium"
        }
    
    # Authentication errors
    if "401" in error_lower or "403" in error_lower or "unauthorized" in error_lower or "forbidden" in error_lower:
        return {
            "diagnosis": "The upload token is invalid or expired. The sensor cannot authenticate with the cloud service.",
            "steps": [
                "Log into oberlin.communityhub.cloud and generate a new upload token",
                "Update the sensor's upload token in the dashboard",
                "Verify the token was copied correctly (no extra spaces)"
            ],
            "severity": "high"
        }
    
    # Data/parsing errors
    if "parse" in error_lower or "json" in error_lower or "data" in error_lower or "invalid" in error_lower:
        return {
            "diagnosis": "The sensor is responding but sending unexpected or malformed data. This could indicate a firmware issue or sensor malfunction.",
            "steps": [
                "Try restarting the sensor (power cycle)",
                "Check if sensor firmware needs updating",
                "Access the sensor directly to see if it's displaying data correctly",
                "If problem persists, the sensor hardware may need inspection"
            ],
            "severity": "medium"
        }
    
    # API/rate limit errors
    if "rate" in error_lower or "limit" in error_lower or "429" in error_lower:
        return {
            "diagnosis": "Too many requests are being made to the API. The polling frequency may be too aggressive.",
            "steps": [
                "Increase the polling interval for this sensor",
                "Wait 15 minutes for rate limits to reset",
                "Check if multiple systems are polling the same sensor"
            ],
            "severity": "low"
        }
    
    # Sensor-specific diagnostics
    if sensor_type == "purple_air":
        return {
            "diagnosis": "The Purple Air sensor encountered an error. This could be a network, power, or sensor hardware issue.",
            "steps": [
                "Check that the Purple Air sensor has power (solid green LED)",
                "Verify WiFi connection (blinking LED pattern)",
                "Try accessing http://<ip-address>/json directly",
                "Power cycle the sensor if unresponsive",
                "Check Purple Air's status page for known issues"
            ],
            "severity": "medium"
        }
    elif sensor_type == "tempest":
        return {
            "diagnosis": "The Tempest weather station or Hub encountered an error.",
            "steps": [
                "Check that the Tempest Hub has power and network",
                "Verify the Hub's LED is solid blue (connected)",
                "Check the Tempest device battery level in the WeatherFlow app",
                "Ensure the device_id is correct",
                "Try restarting the Hub"
            ],
            "severity": "medium"
        }
    elif sensor_type == "voltage_meter":
        return {
            "diagnosis": "The ESP32 voltage meter is not responding.",
            "steps": [
                "Check that the ESP32 has power",
                "Verify the ESP32's WiFi connection",
                "Try accessing http://<ip-address>/status.json directly",
                "Check if the ESP32 needs a firmware update or reset"
            ],
            "severity": "medium"
        }
    
    # Default/unknown error
    return {
        "diagnosis": "An unexpected error occurred with this sensor.",
        "steps": [
            "Check the sensor's physical status (power, network)",
            "Review the error message for specific details",
            "Try power cycling the sensor",
            "Check the dashboard logs for more information",
            "Contact support if the issue persists"
        ],
        "severity": "medium"
    }


class EmailService:
    """
    Service for sending email notifications about sensor errors.
    
    Uses SMTP to send emails. Configure with environment variables:
    - SMTP_HOST: SMTP server hostname (default: smtp.gmail.com)
    - SMTP_PORT: SMTP server port (default: 587)
    - SMTP_USER: SMTP username/email
    - SMTP_PASSWORD: SMTP password or app password
    - ALERT_EMAIL: Email address to send alerts to (default: dashboards@oberlin.edu)
    """
    
    # New sensor notification recipients
    NEW_SENSOR_TO = ["gaurav@communityhub.cloud", "pratyush@communityhub.cloud"]
    NEW_SENSOR_CC = ["john.petersen@oberlin.edu", "cransom@oberlin.edu", "msimoya@oberlin.edu"]
    
    def __init__(self):
        """Initialize email service with configuration from environment."""
        self.smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USER", "")
        self.smtp_password = os.getenv("SMTP_PASSWORD", "")
        self.alert_email = os.getenv("ALERT_EMAIL", "dashboard@oberlin.edu")
        self.from_email = os.getenv("FROM_EMAIL", self.smtp_user or "sensor-dashboard@oberlin.edu")
        
        # Track sent alerts to avoid spam (sensor_id -> last_alert_time)
        self._last_alerts: dict[str, datetime] = {}
        # Minimum time between alerts for the same sensor (5 minutes)
        self.alert_cooldown_seconds = int(os.getenv("ALERT_COOLDOWN", "300"))
        
        # Check if email is configured
        self.is_configured = bool(self.smtp_user and self.smtp_password)
        if not self.is_configured:
            logger.warning(
                "Email service not configured. Set SMTP_USER and SMTP_PASSWORD "
                "environment variables to enable email alerts."
            )
    
    
    def _can_send_alert(self, sensor_id: str) -> bool:
        """Check if we can send an alert for this sensor (cooldown check)."""
        if sensor_id not in self._last_alerts:
            return True
        
        last_alert = self._last_alerts[sensor_id]
        elapsed = (datetime.now(timezone.utc) - last_alert).total_seconds()
        return elapsed >= self.alert_cooldown_seconds
    
    
    def _record_alert(self, sensor_id: str):
        """Record that an alert was sent for this sensor."""
        self._last_alerts[sensor_id] = datetime.now(timezone.utc)
    
    
    def send_sensor_error_alert(
        self,
        sensor_id: str,
        sensor_name: str,
        sensor_type: str,
        error_message: str,
        status: str,
        location: Optional[str] = None
    ) -> bool:
        """
        Send an email alert about a sensor error.
        
        Args:
            sensor_id: Unique sensor identifier
            sensor_name: Human-readable sensor name
            sensor_type: Type of sensor (purple_air, tempest, voltage_meter)
            error_message: The error that occurred
            status: Current sensor status
            location: Physical location of the sensor
            
        Returns:
            True if email was sent successfully, False otherwise
        """
        if not self.is_configured:
            logger.debug(f"Email not configured, skipping alert for {sensor_name}")
            return False
        
        # Check cooldown to avoid spam
        if not self._can_send_alert(sensor_id):
            logger.debug(f"Alert cooldown active for {sensor_name}, skipping")
            return False
        
        try:
            # Get diagnosis and fix steps
            diagnosis_info = get_error_diagnosis(error_message, sensor_type)
            diagnosis = diagnosis_info["diagnosis"]
            fix_steps = diagnosis_info["steps"]
            severity = diagnosis_info["severity"]
            
            # Create email
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"[ALERT] Sensor: {sensor_name} - {status.upper()}"
            msg["From"] = self.from_email
            msg["To"] = self.alert_email
            
            # Timestamp
            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            
            # Format fix steps for plain text
            steps_text = "\n".join(f"  {i+1}. {step}" for i, step in enumerate(fix_steps))
            
            # Plain text version
            text_content = f"""
Sensor Alert
============

Sensor: {sensor_name}
Type: {sensor_type}
Location: {location or 'Unknown'}
Status: {status.upper()}

ERROR
-----
{error_message}

DIAGNOSIS
---------
{diagnosis}

HOW TO FIX
----------
{steps_text}

Time: {timestamp}
Sensor ID: {sensor_id}

---
Sensor Data Collector Dashboard
https://ed-sensor-dashboard.vercel.app/
"""
            
            # Format fix steps for HTML
            steps_html = "".join(f"<li>{step}</li>" for step in fix_steps)
            
            # Severity color
            severity_colors = {
                "high": "#dc3545",
                "medium": "#ffc107", 
                "low": "#17a2b8"
            }
            severity_color = severity_colors.get(severity, "#dc3545")
            
            # HTML version
            html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 650px; margin: 0 auto; padding: 20px; }}
        .header {{ background: #dc3545; color: white; padding: 20px; border-radius: 8px 8px 0 0; }}
        .content {{ background: #f8f9fa; padding: 20px; border: 1px solid #dee2e6; }}
        .error-box {{ background: #fff; border-left: 4px solid #dc3545; padding: 15px; margin: 15px 0; }}
        .diagnosis-box {{ background: #fff; border-left: 4px solid {severity_color}; padding: 15px; margin: 15px 0; }}
        .fix-box {{ background: #fff; border: 1px solid #28a745; padding: 15px; margin: 15px 0; border-radius: 4px; }}
        .fix-box h4 {{ color: #28a745; margin-top: 0; }}
        .fix-box ol {{ margin: 0; padding-left: 20px; }}
        .fix-box li {{ margin: 8px 0; }}
        .footer {{ background: #e9ecef; padding: 15px; border-radius: 0 0 8px 8px; font-size: 12px; color: #6c757d; }}
        .label {{ font-weight: bold; color: #495057; }}
        .section-title {{ font-weight: bold; color: #495057; margin-bottom: 10px; font-size: 14px; text-transform: uppercase; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2>Sensor Alert</h2>
        </div>
        <div class="content">
            <p><span class="label">Sensor:</span> {sensor_name}</p>
            <p><span class="label">Type:</span> {sensor_type}</p>
            <p><span class="label">Location:</span> {location or 'Unknown'}</p>
            <p><span class="label">Status:</span> <strong style="color: #dc3545;">{status.upper()}</strong></p>
            
            <div class="error-box">
                <div class="section-title">Error</div>
                {error_message}
            </div>
            
            <div class="diagnosis-box">
                <div class="section-title">Diagnosis</div>
                {diagnosis}
            </div>
            
            <div class="fix-box">
                <h4>How to Fix</h4>
                <ol>
                    {steps_html}
                </ol>
            </div>
            
            <p><span class="label">Time:</span> {timestamp}</p>
            <p><span class="label">Sensor ID:</span> <code>{sensor_id}</code></p>
        </div>
        <div class="footer">
            <p>Sensor Data Collector Dashboard<br>
            <a href="https://ed-sensor-dashboard.vercel.app/">View Dashboard</a></p>
        </div>
    </div>
</body>
</html>
"""
            
            msg.attach(MIMEText(text_content, "plain"))
            msg.attach(MIMEText(html_content, "html"))
            
            # Send email
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
            
            # Record successful alert
            self._record_alert(sensor_id)
            logger.info(f"Alert email sent for sensor {sensor_name} to {self.alert_email}")
            return True
            
        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP authentication failed: {e}")
            return False
        except smtplib.SMTPException as e:
            logger.error(f"SMTP error sending alert: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to send alert email: {type(e).__name__}: {e}")
            return False
    
    
    def send_sensor_recovery_alert(
        self,
        sensor_id: str,
        sensor_name: str,
        sensor_type: str,
        location: Optional[str] = None
    ) -> bool:
        """
        Send an email when a sensor recovers from an error state.
        
        Args:
            sensor_id: Unique sensor identifier
            sensor_name: Human-readable sensor name
            sensor_type: Type of sensor
            location: Physical location of the sensor
            
        Returns:
            True if email was sent successfully, False otherwise
        """
        if not self.is_configured:
            return False
        
        # Check cooldown to avoid duplicate recovery emails
        recovery_key = f"{sensor_id}_recovery"
        if not self._can_send_alert(recovery_key):
            logger.debug(f"Recovery alert cooldown active for {sensor_name}, skipping")
            return False
        
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"[RECOVERED] Sensor: {sensor_name}"
            msg["From"] = self.from_email
            msg["To"] = self.alert_email
            
            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            
            text_content = f"""
Sensor Recovery
===============

Sensor: {sensor_name}
Type: {sensor_type}
Location: {location or 'Unknown'}
Status: ACTIVE

The sensor has recovered and is now working normally.

Time: {timestamp}

---
Sensor Data Collector Dashboard
"""
            
            html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: #28a745; color: white; padding: 20px; border-radius: 8px 8px 0 0; }}
        .content {{ background: #f8f9fa; padding: 20px; border: 1px solid #dee2e6; }}
        .footer {{ background: #e9ecef; padding: 15px; border-radius: 0 0 8px 8px; font-size: 12px; color: #6c757d; }}
        .label {{ font-weight: bold; color: #495057; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2>Sensor Recovered</h2>
        </div>
        <div class="content">
            <p><span class="label">Sensor:</span> {sensor_name}</p>
            <p><span class="label">Type:</span> {sensor_type}</p>
            <p><span class="label">Location:</span> {location or 'Unknown'}</p>
            <p><span class="label">Status:</span> <strong style="color: #28a745;">ACTIVE</strong></p>
            <p>The sensor has recovered and is now working normally.</p>
            <p><span class="label">Time:</span> {timestamp}</p>
        </div>
        <div class="footer">
            <p>Sensor Data Collector Dashboard<br>
            <a href="https://ed-sensor-dashboard.vercel.app/">View Dashboard</a></p>
        </div>
    </div>
</body>
</html>
"""
            
            msg.attach(MIMEText(text_content, "plain"))
            msg.attach(MIMEText(html_content, "html"))
            
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
            
            # Record the recovery alert to prevent duplicates
            self._record_alert(recovery_key)
            # Clear the error alert record so future errors will trigger new alerts
            self._last_alerts.pop(sensor_id, None)
            logger.info(f"Recovery email sent for sensor {sensor_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send recovery email: {type(e).__name__}: {e}")
            return False
    
    
    def send_status_report(self, sensors: list[dict]) -> bool:
        """
        Send a status report email with all sensor statuses.
        
        Args:
            sensors: List of sensor dictionaries with status info
            
        Returns:
            True if email was sent successfully, False otherwise
        """
        if not self.is_configured:
            logger.error("Email not configured, cannot send status report")
            return False
        
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"Sensor Status Report - {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC"
            msg["From"] = self.from_email
            msg["To"] = self.alert_email
            
            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            
            # Count statuses
            active_count = sum(1 for s in sensors if s.get("status") == "active")
            inactive_count = sum(1 for s in sensors if s.get("status") == "inactive")
            error_count = sum(1 for s in sensors if s.get("status") in ["error", "offline"])
            total = len(sensors)
            
            # Build sensor list for plain text
            sensor_lines = []
            for s in sensors:
                status = s.get("status", "unknown").upper()
                name = s.get("name", "Unknown")
                sensor_type = s.get("sensor_type", "unknown")
                location = s.get("location", "Unknown")
                last_error = s.get("last_error", "")
                
                status_marker = "[OK]" if status == "ACTIVE" else "[!]" if status == "INACTIVE" else "[X]"
                line = f"{status_marker} {name} ({sensor_type}) - {status}"
                if last_error and status != "ACTIVE":
                    line += f"\n   Error: {last_error}"
                sensor_lines.append(line)
            
            text_content = f"""
Sensor Status Report
====================

Generated: {timestamp}

Summary:
- Active: {active_count}/{total}
- Inactive: {inactive_count}/{total}
- Error/Offline: {error_count}/{total}

Sensors:
{chr(10).join(sensor_lines)}

---
Sensor Data Collector Dashboard
https://ed-sensor-dashboard.vercel.app/
"""
            
            # Build HTML sensor rows
            sensor_rows = ""
            for s in sensors:
                status = s.get("status", "unknown")
                name = s.get("name", "Unknown")
                sensor_type = s.get("sensor_type", "unknown")
                location = s.get("location", "Unknown")
                last_error = s.get("last_error", "")
                last_active = s.get("last_active", "")
                
                if status == "active":
                    status_color = "#28a745"
                elif status == "inactive":
                    status_color = "#ffc107"
                else:
                    status_color = "#dc3545"
                
                error_row = f'<div style="color: #dc3545; font-size: 12px; margin-top: 5px;">{last_error}</div>' if last_error and status != "active" else ""
                
                sensor_rows += f"""
                <tr>
                    <td style="padding: 12px; border-bottom: 1px solid #dee2e6;">
                        <strong>{name}</strong><br>
                        <span style="color: #6c757d; font-size: 12px;">{location}</span>
                        {error_row}
                    </td>
                    <td style="padding: 12px; border-bottom: 1px solid #dee2e6; text-transform: capitalize;">{sensor_type.replace('_', ' ')}</td>
                    <td style="padding: 12px; border-bottom: 1px solid #dee2e6;">
                        <span style="color: {status_color}; font-weight: bold;">{status.upper()}</span>
                    </td>
                </tr>
                """
            
            html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 700px; margin: 0 auto; padding: 20px; }}
        .header {{ background: #007bff; color: white; padding: 20px; border-radius: 8px 8px 0 0; }}
        .content {{ background: #f8f9fa; padding: 20px; border: 1px solid #dee2e6; }}
        .summary {{ display: flex; justify-content: space-around; margin: 20px 0; }}
        .stat {{ text-align: center; padding: 15px; background: white; border-radius: 8px; min-width: 100px; }}
        .stat-number {{ font-size: 24px; font-weight: bold; }}
        .stat-label {{ font-size: 12px; color: #6c757d; }}
        table {{ width: 100%; border-collapse: collapse; background: white; }}
        th {{ background: #e9ecef; padding: 12px; text-align: left; }}
        .footer {{ background: #e9ecef; padding: 15px; border-radius: 0 0 8px 8px; font-size: 12px; color: #6c757d; text-align: center; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2>Sensor Status Report</h2>
            <p style="margin: 0; opacity: 0.9;">{timestamp}</p>
        </div>
        <div class="content">
            <div class="summary">
                <div class="stat">
                    <div class="stat-number" style="color: #28a745;">{active_count}</div>
                    <div class="stat-label">Active</div>
                </div>
                <div class="stat">
                    <div class="stat-number" style="color: #ffc107;">{inactive_count}</div>
                    <div class="stat-label">Inactive</div>
                </div>
                <div class="stat">
                    <div class="stat-number" style="color: #dc3545;">{error_count}</div>
                    <div class="stat-label">Error</div>
                </div>
                <div class="stat">
                    <div class="stat-number">{total}</div>
                    <div class="stat-label">Total</div>
                </div>
            </div>
            
            <table>
                <thead>
                    <tr>
                        <th>Sensor</th>
                        <th>Type</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
                    {sensor_rows}
                </tbody>
            </table>
        </div>
        <div class="footer">
            <p>Sensor Data Collector Dashboard<br>
            <a href="https://ed-sensor-dashboard.vercel.app/">View Dashboard</a></p>
        </div>
    </div>
</body>
</html>
"""
            
            msg.attach(MIMEText(text_content, "plain"))
            msg.attach(MIMEText(html_content, "html"))
            
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
            
            logger.info(f"Status report email sent to {self.alert_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send status report: {type(e).__name__}: {e}")
            return False
    
    
    def send_new_sensor_notification(
        self,
        sensor_id: str,
        sensor_name: str,
        sensor_type: str,
        location: Optional[str] = None,
        ip_address: Optional[str] = None,
        upload_token: Optional[str] = None
    ) -> bool:
        """
        Send notification email when a new sensor is added.
        
        Sends to CommunityHub team with CC to Oberlin team.
        Lists datapoints and units, requests DataHub configuration.
        
        Args:
            sensor_id: Unique sensor identifier
            sensor_name: Human-readable sensor name
            sensor_type: Type of sensor (purple_air, tempest, voltage_meter)
            location: Physical location of the sensor
            ip_address: Sensor IP address
            upload_token: Upload token (partially masked for security)
            
        Returns:
            True if email was sent successfully, False otherwise
        """
        if not self.is_configured:
            logger.warning("Email not configured, skipping new sensor notification")
            return False
        
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"[NEW SENSOR] {sensor_name} - Please Configure on DataHub"
            msg["From"] = self.from_email
            msg["To"] = ", ".join(self.NEW_SENSOR_TO)
            msg["Cc"] = ", ".join(self.NEW_SENSOR_CC)
            
            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            
            # Get datapoints for this sensor type
            datapoints = SENSOR_DATAPOINTS.get(sensor_type, [])
            
            # Build datapoints table for plain text
            datapoint_lines = []
            for dp_name, dp_unit in datapoints:
                datapoint_lines.append(f"  - {dp_name}: {dp_unit}")
            datapoints_text = "\n".join(datapoint_lines) if datapoint_lines else "  (No datapoints defined)"
            
            # Mask upload token for security (show first 4 and last 4 chars)
            masked_token = ""
            if upload_token:
                if len(upload_token) > 8:
                    masked_token = f"{upload_token[:4]}...{upload_token[-4:]}"
                else:
                    masked_token = "****"
            
            # Format sensor type for display
            sensor_type_display = sensor_type.replace("_", " ").title()
            
            text_content = f"""
New Sensor Added - Configuration Request
=========================================

A new sensor has been added to the Oberlin Environmental Dashboard.
Please configure it to display on DataHub.

SENSOR DETAILS
--------------
Name: {sensor_name}
Type: {sensor_type_display}
Location: {location or 'Not specified'}
Sensor ID: {sensor_id}
Upload Token: {masked_token or 'Not provided'}
Added: {timestamp}

DATAPOINTS BEING SENT
---------------------
{datapoints_text}

ACTION REQUIRED
---------------
Please configure this sensor on DataHub so data can be visualized.

---
Sensor Data Collector Dashboard
https://ed-sensor-dashboard.vercel.app/
"""
            
            # Build HTML datapoints table
            datapoint_rows = ""
            for dp_name, dp_unit in datapoints:
                datapoint_rows += f"""
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{dp_name}</td>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><code>{dp_unit}</code></td>
                </tr>
                """
            
            html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 700px; margin: 0 auto; padding: 20px; }}
        .header {{ background: #17a2b8; color: white; padding: 20px; border-radius: 8px 8px 0 0; }}
        .content {{ background: #f8f9fa; padding: 20px; border: 1px solid #dee2e6; }}
        .section {{ background: white; padding: 15px; margin: 15px 0; border-radius: 4px; border: 1px solid #dee2e6; }}
        .section-title {{ font-weight: bold; color: #495057; margin-bottom: 10px; font-size: 14px; text-transform: uppercase; }}
        .footer {{ background: #e9ecef; padding: 15px; border-radius: 0 0 8px 8px; font-size: 12px; color: #6c757d; }}
        .label {{ font-weight: bold; color: #495057; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th {{ background: #e9ecef; padding: 10px; text-align: left; font-size: 12px; text-transform: uppercase; }}
        .action-box {{ background: #fff3cd; border: 1px solid #ffc107; padding: 15px; border-radius: 4px; margin: 15px 0; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2>New Sensor Added</h2>
            <p style="margin: 0; opacity: 0.9;">Configuration Request</p>
        </div>
        <div class="content">
            <p>A new sensor has been added to the Oberlin Environmental Dashboard. Please configure it to display on DataHub.</p>
            
            <div class="section">
                <div class="section-title">Sensor Details</div>
                <p><span class="label">Name:</span> {sensor_name}</p>
                <p><span class="label">Type:</span> {sensor_type_display}</p>
                <p><span class="label">Location:</span> {location or 'Not specified'}</p>
                <p><span class="label">Sensor ID:</span> <code>{sensor_id}</code></p>
                <p><span class="label">Upload Token:</span> <code>{masked_token or 'Not provided'}</code></p>
                <p><span class="label">Added:</span> {timestamp}</p>
            </div>
            
            <div class="section">
                <div class="section-title">Datapoints Being Sent</div>
                <table>
                    <thead>
                        <tr>
                            <th>Datapoint</th>
                            <th>Unit</th>
                        </tr>
                    </thead>
                    <tbody>
                        {datapoint_rows}
                    </tbody>
                </table>
            </div>
            
            <div class="action-box">
                <strong>Action Required:</strong> Please configure this sensor on DataHub so data can be visualized.
            </div>
        </div>
        <div class="footer">
            <p>Sensor Data Collector Dashboard<br>
            <a href="https://ed-sensor-dashboard.vercel.app/">View Dashboard</a></p>
        </div>
    </div>
</body>
</html>
"""
            
            msg.attach(MIMEText(text_content, "plain"))
            msg.attach(MIMEText(html_content, "html"))
            
            # Send to all recipients (To + Cc)
            all_recipients = self.NEW_SENSOR_TO + self.NEW_SENSOR_CC
            
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg, to_addrs=all_recipients)
            
            logger.info(f"New sensor notification sent for {sensor_name} to {', '.join(self.NEW_SENSOR_TO)}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send new sensor notification: {type(e).__name__}: {e}")
            return False
