import type { Sensor, SensorListResponse, AddPurpleAirRequest, AddTempestRequest, AddVoltageMeterRequest } from './types';

// Use environment variable for API URL, fallback to localhost for development
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

async function api<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  try {
    const res = await fetch(`${API_URL}${endpoint}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });
    
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      let message = err.message || `Error: ${res.status} ${res.statusText}`;
      if (err.detail !== undefined) {
        if (Array.isArray(err.detail)) {
          message = err.detail.map((d: { msg?: string }) => (d && typeof d === 'object' && d.msg) || String(d)).join('. ');
        } else if (typeof err.detail === 'string') {
          message = err.detail;
        } else if (err.detail && typeof err.detail === 'object' && typeof (err.detail as { msg?: string }).msg === 'string') {
          message = (err.detail as { msg: string }).msg;
        }
      }
      throw new Error(message);
    }
    
    return res.json();
  } catch (error: any) {
    // Handle network errors (fetch failed completely)
    if (error.name === 'TypeError' && error.message.includes('fetch')) {
      const tip = API_URL.includes('http://localhost') 
        ? 'Check if the backend is running (e.g. run-continuously.ps1 or start-backend.ps1).'
        : 'Ensure the backend and Cloudflare tunnel are running on the server (e.g. SensorDataCollector scheduled task or run-continuously.ps1).';
      throw new Error(`Cannot connect to backend at ${API_URL}. ${tip}`);
    }
    // Re-throw if it's already an Error with a message
    if (error instanceof Error) {
      throw error;
    }
    // Otherwise wrap in Error
    throw new Error(String(error));
  }
}

// Health check
export const checkHealth = () => api<{ status: string }>('/health');

// Get all sensors
export const getAllSensors = () => api<SensorListResponse>('/api/sensors/');

// Get sensors by type
export const getPurpleAirSensors = () => api<SensorListResponse>('/api/sensors/purple-air');
export const getTempestSensors = () => api<SensorListResponse>('/api/sensors/tempest');
export const getWaterQualitySensors = () => api<SensorListResponse>('/api/sensors/water-quality');
export const getDOSensors = () => api<SensorListResponse>('/api/sensors/do-sensor');

// Add sensors
export const addPurpleAirSensor = (data: AddPurpleAirRequest) =>
  api<Sensor>('/api/sensors/purple-air', { method: 'POST', body: JSON.stringify(data) });

export const addTempestSensor = (data: AddTempestRequest) =>
  api<Sensor>('/api/sensors/tempest', { method: 'POST', body: JSON.stringify(data) });

export const addVoltageMeter = (data: AddVoltageMeterRequest) =>
  api<Sensor>('/api/sensors/voltage-meter', { method: 'POST', body: JSON.stringify(data) });

// Sensor actions
export const getSensor = (id: string) => api<Sensor>(`/api/sensors/${id}`);
export const deleteSensor = (id: string) => api<{ status: string }>(`/api/sensors/${id}`, { method: 'DELETE' });
export const getSensorStatus = (id: string) => api<any>(`/api/sensors/${id}/status`);
export const turnOnSensor = (id: string) => api<Sensor>(`/api/sensors/${id}/turn-on`, { method: 'POST' });
export const turnOffSensor = (id: string) => api<Sensor>(`/api/sensors/${id}/turn-off`, { method: 'POST' });
export const fetchNow = (id: string) => api<any>(`/api/sensors/${id}/fetch-now`, { method: 'POST' });

// Power mode (for Purple Air sensors with linked voltage meters)
export const setPowerMode = (id: string, mode: 'normal' | 'power_saving') =>
  api<Sensor>(`/api/sensors/${id}/power-mode?power_mode=${mode}`, { method: 'POST' });

// Polling frequency (in minutes, must be multiple of 5)
export const setPollingFrequency = (id: string, minutes: number) =>
  api<any>(`/api/sensors/${id}/frequency`, { method: 'POST', body: JSON.stringify({ minutes }) });

// Voltage Meter relay control (stores command; applied on next ESP32 wake)
export const setRelayMode = (voltageMeterId: string, mode: 'automatic' | 'force_on' | 'force_off') =>
  api<any>(`/api/sensors/voltage-meter/${voltageMeterId}/relay-mode`, { method: 'POST', body: JSON.stringify({ mode }) });

// Get last sent data for a sensor
export const getLastSentData = (id: string) =>
  api<{ sensor_id: string; last_csv_sample: string | null; last_upload_attempt: string | null }>(`/api/sensors/${id}/last-data`);

// Update sensor settings
export const updateSensor = (id: string, data: { name?: string; location?: string; ip_address?: string; linked_sensor_id?: string }) =>
  api<Sensor>(`/api/sensors/${id}`, { method: 'PUT', body: JSON.stringify(data) });

// Set voltage meter thresholds (v_cutoff, v_reconnect; applied on next ESP32 wake)
export const setThresholds = (id: string, v_cutoff: number, v_reconnect: number) =>
  api<any>(`/api/sensors/voltage-meter/${id}/thresholds`, { method: 'POST', body: JSON.stringify({ v_cutoff, v_reconnect }) });

// Calibrate voltage meter ADC
export const calibrateVoltageMeter = (id: string, targetVoltage: number) =>
  api<any>(`/api/sensors/voltage-meter/${id}/calibrate`, { method: 'POST', body: JSON.stringify({ target_voltage: targetVoltage }) });

// Set voltage meter sleep interval
export const setSleepInterval = (id: string, sleepIntervalMinutes: number) =>
  api<any>(`/api/sensors/voltage-meter/${id}/sleep-interval`, { method: 'POST', body: JSON.stringify({ sleep_interval_minutes: sleepIntervalMinutes }) });
