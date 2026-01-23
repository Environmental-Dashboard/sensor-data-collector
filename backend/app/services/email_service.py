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
from typing import Optional

logger = logging.getLogger(__name__)


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
            # Create email
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"🚨 Sensor Alert: {sensor_name} - {status.upper()}"
            msg["From"] = self.from_email
            msg["To"] = self.alert_email
            
            # Timestamp
            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            
            # Plain text version
            text_content = f"""
Sensor Alert
============

Sensor: {sensor_name}
Type: {sensor_type}
Location: {location or 'Unknown'}
Status: {status.upper()}

Error: {error_message}

Time: {timestamp}
Sensor ID: {sensor_id}

---
Sensor Data Collector Dashboard
https://ed-sensor-dashboard.vercel.app/
"""
            
            # HTML version
            html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: #dc3545; color: white; padding: 20px; border-radius: 8px 8px 0 0; }}
        .content {{ background: #f8f9fa; padding: 20px; border: 1px solid #dee2e6; }}
        .error-box {{ background: #fff; border-left: 4px solid #dc3545; padding: 15px; margin: 15px 0; }}
        .footer {{ background: #e9ecef; padding: 15px; border-radius: 0 0 8px 8px; font-size: 12px; color: #6c757d; }}
        .label {{ font-weight: bold; color: #495057; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2>🚨 Sensor Alert</h2>
        </div>
        <div class="content">
            <p><span class="label">Sensor:</span> {sensor_name}</p>
            <p><span class="label">Type:</span> {sensor_type}</p>
            <p><span class="label">Location:</span> {location or 'Unknown'}</p>
            <p><span class="label">Status:</span> <strong style="color: #dc3545;">{status.upper()}</strong></p>
            
            <div class="error-box">
                <span class="label">Error:</span><br>
                {error_message}
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
            msg["Subject"] = f"✅ Sensor Recovered: {sensor_name}"
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
            <h2>✅ Sensor Recovered</h2>
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
            msg["Subject"] = f"📊 Sensor Status Report - {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC"
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
                
                status_emoji = "✅" if status == "ACTIVE" else "⚠️" if status == "INACTIVE" else "❌"
                line = f"{status_emoji} {name} ({sensor_type}) - {status}"
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
                    status_icon = "✅"
                elif status == "inactive":
                    status_color = "#ffc107"
                    status_icon = "⚠️"
                else:
                    status_color = "#dc3545"
                    status_icon = "❌"
                
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
                        <span style="color: {status_color}; font-weight: bold;">{status_icon} {status.upper()}</span>
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
            <h2>📊 Sensor Status Report</h2>
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
