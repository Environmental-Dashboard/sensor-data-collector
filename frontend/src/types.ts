// Sensor types
export type SensorType = 'purple_air' | 'tempest' | 'water_quality' | 'do_sensor' | 'voltage_meter';
export type SensorStatus = 'active' | 'inactive' | 'error' | 'offline' | 'sleeping' | 'waking';
export type PowerMode = 'normal' | 'power_saving';

// A sensor from the API
export interface Sensor {
  id: string;
  sensor_type: SensorType;
  name: string;
  location: string;
  ip_address: string | null;
  device_id: string | null;
  status: SensorStatus;
  status_reason: string | null;  // Why sensor is in this status (battery_low, wifi_error, cloud_error, etc.)
  is_active: boolean;
  last_active: string | null;
  last_error: string | null;
  created_at: string;
  battery_volts: number | null;  // Tempest/Voltage Meter battery voltage
  linked_sensor_id: string | null;  // For voltage meters - linked Purple Air sensor
  linked_sensor_name: string | null;  // For voltage meters - linked sensor name
  power_mode: PowerMode | null;  // For Purple Air - normal or power_saving
  polling_frequency: number | null;  // Polling frequency in seconds
}

// List response
export interface SensorListResponse {
  sensors: Sensor[];
  total: number;
}

// Add sensor requests
export interface AddPurpleAirRequest {
  ip_address: string;
  name: string;
  location: string;
  upload_token: string;
}

export interface AddTempestRequest {
  device_id: string;
  location: string;
  upload_token: string;
}

export interface AddWaterQualityRequest {
  device_id: string;
  ubidots_token: string;
  name: string;
  location: string;
  upload_token: string;
}

export interface AddVoltageMeterRequest {
  ip_address: string;
  name?: string;  // Optional - auto-generated if linked_sensor_id is provided
  location: string;
  upload_token: string;
  linked_sensor_id?: string;  // Optional - link to a Purple Air sensor
}