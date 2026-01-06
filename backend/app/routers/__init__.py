"""
Routers Package
===============
FastAPI routers for the API endpoints.
"""

from .sensors import router as sensors_router, set_sensor_manager
from .test_upload import router as test_upload_router

__all__ = [
    "sensors_router",
    "test_upload_router",
    "set_sensor_manager",
]

"""===============
FastAPI routers for the API endpoints.
"""

from .sensors import router as sensors_router, set_sensor_manager
from .test_upload import router as test_upload_router

__all__ = [
    "sensors_router",
    "test_upload_router",
    "set_sensor_manager",
]
