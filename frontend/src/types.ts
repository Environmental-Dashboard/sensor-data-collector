// Sensor types
export type SensorType = 'purple_air' | 'tempest' | 'water_quality' | 'do_sensor';
export type SensorStatus = 'active' | 'inactive' | 'error' | 'offline';

// A sensor from the API
export interface Sensor {
  id: string;
  sensor_type: SensorType;
  name: string;
  location: string;
  ip_address: string | null;
  device_id: string | null;
  status: SensorStatus;
  is_active: boolean;
  last_active: string | null;
  last_error: string | null;
  created_at: string;
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
  ip_address: string;
  name: string;
  location: string;
  device_id: string;
  upload_token: string;
}

export interface AddWaterQualityRequest {
  device_id: string;
  ubidots_token: string;
  name: string;
  location: string;
  upload_token: string;
}