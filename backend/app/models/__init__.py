"""
Models Package
==============

This is where all our data models live.
Import from here instead of the individual files.

Example:
    from app.models import SensorType, AddPurpleAirSensorRequest
"""

from .sensor import (
    # What kind of sensors and their status
    SensorType,
    SensorStatus,
    
    # What the frontend sends us when adding sensors
    AddPurpleAirSensorRequest,
    AddTempestSensorRequest,
    AddWaterQualitySensorRequest,
    AddDOSensorRequest,
    UpdateSensorRequest,
    
    # What we send back to the frontend
    SensorResponse,
    SensorListResponse,
    FetchResultResponse,
    
    # The actual data from sensors
    PurpleAirReading,
    TempestReading,
)

__all__ = [
    "SensorType",
    "SensorStatus",
    "AddPurpleAirSensorRequest",
    "AddTempestSensorRequest",
    "AddWaterQualitySensorRequest",
    "AddDOSensorRequest",
    "UpdateSensorRequest",
    "SensorResponse",
    "SensorListResponse",
    "FetchResultResponse",
    "PurpleAirReading",
    "TempestReading",
]
