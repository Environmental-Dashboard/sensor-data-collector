"""
Input Validation Utilities
===========================

Common validation functions for sensor data and user inputs.

Author: Frank Kusi Appiah
"""

import re
import ipaddress
from typing import Optional


def validate_ip_address(ip: str) -> bool:
    """
    Validate an IP address string.
    
    Args:
        ip: IP address string (e.g., "192.168.1.100")
        
    Returns:
        True if valid, False otherwise
    """
    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False


def validate_sensor_id(sensor_id: str) -> bool:
    """
    Validate a sensor ID (UUID format).
    
    Args:
        sensor_id: Sensor ID string (UUID)
        
    Returns:
        True if valid UUID format, False otherwise
    """
    uuid_pattern = re.compile(
        r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
        re.IGNORECASE
    )
    return bool(uuid_pattern.match(sensor_id))


def sanitize_filename(name: str) -> str:
    """
    Sanitize a filename by removing dangerous characters.
    
    Args:
        name: Original filename
        
    Returns:
        Sanitized filename safe for filesystem
    """
    # Remove or replace dangerous characters
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', name)
    # Remove leading/trailing dots and spaces
    sanitized = sanitized.strip('. ')
    # Limit length
    return sanitized[:255]


def validate_voltage(value: float, min_v: float = 0.0, max_v: float = 20.0) -> bool:
    """
    Validate a voltage value.
    
    Args:
        value: Voltage value
        min_v: Minimum allowed voltage
        max_v: Maximum allowed voltage
        
    Returns:
        True if valid, False otherwise
    """
    return min_v <= value <= max_v


def validate_polling_frequency(minutes: int) -> bool:
    """
    Validate polling frequency (must be positive and reasonable).
    
    Args:
        minutes: Polling frequency in minutes
        
    Returns:
        True if valid, False otherwise
    """
    return 1 <= minutes <= 1440  # 1 minute to 24 hours


def validate_device_id(device_id: str) -> bool:
    """
    Validate a device ID (alphanumeric, reasonable length).
    
    Args:
        device_id: Device ID string
        
    Returns:
        True if valid, False otherwise
    """
    if not device_id:
        return False
    # Allow alphanumeric and some special chars, reasonable length
    return bool(re.match(r'^[a-zA-Z0-9_-]{1,100}$', device_id))
