"""
ESP32 Inbound API Router
========================

Option B: ESP32 wakes, reads voltage, POSTs to backend, then controls relay and sleeps.
This router accepts outbound POSTs from ESP32 devices (e.g. battery cutoff monitors).

Endpoint:
  POST /api/esp32/voltage  - Report voltage reading; backend forwards to Community Hub.

Auth: Header `user-token: <upload_token>` (same token as when adding the voltage meter).
"""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException

from pydantic import BaseModel, Field

from app.utils.validation import validate_sensor_id, validate_voltage
from app.models import SensorType, SensorStatus
from app.routers.sensors import get_sensor_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/esp32", tags=["esp32"])


# -----------------------------------------------------------------------------
# Request/Response models
# -----------------------------------------------------------------------------


class Esp32VoltagePayload(BaseModel):
    """
    JSON body for POST /api/esp32/voltage.

    Required: sensor_id (UUID from dashboard), voltage_v.
    Optional: relay state and thresholds so the dashboard shows current state.
    """
    sensor_id: str = Field(..., description="Voltage meter sensor UUID (from dashboard when you added the device)")
    voltage_v: float = Field(..., description="Battery voltage in volts (e.g. 12.45)")
    load_on: bool = Field(default=False, description="Is relay/load currently ON?")
    auto_mode: bool = Field(default=True, description="Is relay in auto mode?")
    relay_mode: str = Field(default="automatic", description="Current relay mode on device: automatic | force_on | force_off")
    v_cutoff: float = Field(default=12.0, description="Cutoff voltage threshold (V)")
    v_reconnect: float = Field(default=12.6, description="Reconnect voltage threshold (V)")
    calibration_factor: float = Field(default=1.0, description="ADC calibration factor (backend clears pending calibration when this is reported after a target was set)")
    cycle_count: int = Field(default=0, description="Total relay cycle count")
    turn_on_count_48h: int = Field(default=0, description="Relay on-cycles in last 48h")
    uptime_ms: int = Field(default=0, description="Device uptime in milliseconds")


# -----------------------------------------------------------------------------
# Endpoint
# -----------------------------------------------------------------------------


@router.post("/voltage")
async def esp32_report_voltage(
    body: Esp32VoltagePayload,
    user_token: str | None = Header(None, alias="user-token"),
    manager=Depends(get_sensor_manager),
):
    """
    ESP32 reports a voltage reading (Option B: outbound POST from device).

    - Backend accepts the reading, forwards it to Community Hub as CSV, and
      updates the dashboard sensor state.
    - Use the same upload_token you used when adding this voltage meter.

    **Headers**
    - `user-token`: Your upload token (from oberlin.communityhub.cloud).

    **Body (JSON)**
    - sensor_id (required): UUID of the voltage meter sensor (from dashboard).
    - voltage_v (required): Battery voltage in volts.
    - load_on, auto_mode, v_cutoff, v_reconnect, etc. (optional): For display and CSV.
    """
    if not user_token or not user_token.strip():
        raise HTTPException(
            status_code=401,
            detail="Missing header: user-token (your upload token from oberlin.communityhub.cloud)",
        )

    if not validate_sensor_id(body.sensor_id):
        raise HTTPException(status_code=400, detail="Invalid sensor_id format")

    if not validate_voltage(body.voltage_v, min_v=0.0, max_v=20.0):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid voltage_v: {body.voltage_v}. Must be between 0 and 20 V.",
        )

    sensor = manager.get_sensor(body.sensor_id)
    if not sensor:
        raise HTTPException(status_code=404, detail="Sensor not found. Check sensor_id.")
    if sensor.sensor_type != SensorType.VOLTAGE_METER:
        raise HTTPException(status_code=400, detail="This endpoint is for voltage meter sensors only.")

    stored_token = manager.get_sensor_upload_token(body.sensor_id)
    if not stored_token or stored_token != user_token.strip():
        raise HTTPException(status_code=401, detail="Invalid user-token for this sensor")

    # Build status dict for CSV (same shape as get_status from ESP32)
    status = {
        "voltage_v": body.voltage_v,
        "load_on": body.load_on,
        "auto_mode": body.auto_mode,
        "v_cutoff": body.v_cutoff,
        "v_reconnect": body.v_reconnect,
        "calibration_factor": body.calibration_factor,
        "cycle_count": body.cycle_count,
        "turn_on_count_48h": body.turn_on_count_48h,
        "uptime_ms": body.uptime_ms,
    }

    vm_service = manager.voltage_meter_service
    header = vm_service.csv_header()
    row = vm_service.create_csv_row(status)
    csv_data = f"{header}\n{row}"

    try:
        upload_result = await vm_service.push_to_endpoint(
            csv_data, sensor.name, user_token.strip()
        )
    except Exception as e:
        logger.exception("ESP32 voltage upload to Community Hub failed")
        raise HTTPException(
            status_code=502,
            detail=f"Failed to upload to Community Hub: {e}",
        )

    # Update last known state (dashboard display) and set status to ACTIVE
    manager.update_sensor_field(body.sensor_id, "status", SensorStatus.ACTIVE)
    manager.update_sensor_field(body.sensor_id, "status_reason", None)
    manager.update_sensor_field(body.sensor_id, "last_error", None)
    manager.update_sensor_field(body.sensor_id, "battery_volts", body.voltage_v)
    manager.update_sensor_field(body.sensor_id, "load_on", body.load_on)
    manager.update_sensor_field(body.sensor_id, "auto_mode", body.auto_mode)
    manager.update_sensor_field(body.sensor_id, "last_active", datetime.now(timezone.utc))

    # If ESP32 reports a calibration_factor and we had a pending calibration_target, clear pending (calibration was applied)
    sensor_dict = manager.get_sensor_raw(body.sensor_id)
    if sensor_dict and sensor_dict.get("calibration_target") is not None and body.calibration_factor is not None:
        manager.update_sensor_field(body.sensor_id, "calibration_factor", body.calibration_factor)
        manager.update_sensor_field(body.sensor_id, "calibration_target", None)
        logger.info(f"[ESP32] {sensor.name} calibration applied, factor={body.calibration_factor}, pending cleared")

    # Build commands (desired state from dashboard) for ESP32 to apply on next cycle
    sensor_after = manager.get_sensor(body.sensor_id)
    relay_mode = getattr(sensor_after, "relay_mode", None) or "automatic"
    v_cutoff = sensor_after.v_cutoff if sensor_after.v_cutoff is not None else 12.0
    v_reconnect = sensor_after.v_reconnect if sensor_after.v_reconnect is not None else 12.6
    calibration_target = getattr(sensor_after, "calibration_target", None)
    sleep_interval_minutes = getattr(sensor_after, "sleep_interval_minutes", None) or 15

    logger.info(
        f"[ESP32] {sensor.name} voltage={body.voltage_v:.2f}V relay={'ON' if body.load_on else 'OFF'} -> cloud OK"
    )

    return {
        "status": "ok",
        "message": "Data received",
        "sensor_id": body.sensor_id,
        "voltage_v": body.voltage_v,
        "uploaded_at": upload_result.get("uploaded_at"),
        "commands": {
            "relay_mode": relay_mode,
            "v_cutoff": v_cutoff,
            "v_reconnect": v_reconnect,
            "calibration_target": calibration_target,
            "sleep_interval_minutes": sleep_interval_minutes,
        },
    }
