"""
Services Package
================

These are the "workers" that do the actual work.

- PurpleAirService: Talks to Purple Air sensors
- TempestService: Talks to Tempest weather stations
- SensorManager: The boss that manages all sensors
"""

from .purple_air_service import PurpleAirService
from .tempest_service import TempestService
from .sensor_manager import SensorManager

__all__ = [
    "PurpleAirService",
    "TempestService", 
    "SensorManager",
]
