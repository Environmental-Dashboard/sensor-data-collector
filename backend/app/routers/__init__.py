"""
Routers Package
===============

Routers are like the reception desk - they direct incoming requests
to the right place.
"""

from .sensors import router as sensors_router, set_sensor_manager
from .esp32 import router as esp32_router

__all__ = [
    "sensors_router",
    "esp32_router",
    "set_sensor_manager",
]
