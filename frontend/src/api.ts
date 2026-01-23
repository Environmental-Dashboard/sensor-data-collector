import type { Sensor, SensorListResponse, AddPurpleAirRequest, AddTempestRequest } from './types';

// Use environment variable for API URL, fallback to localhost for development
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Helper to extract a string error message from various error formats
function extractErrorMessage(err: any, statusCode: number): string {
  // If err is null/undefined, use status code
  if (!err) return `Error: ${statusCode}`;
  
  // If err.detail exists
  if (err.detail !== undefined) {
    if (typeof err.detail === 'string') return err.detail;
    if (typeof err.detail === 'object') {
      // FastAPI validation errors have detail as array
      if (Array.isArray(err.detail)) {
        return err.detail.map((e: any) => e.msg || String(e)).join(', ');
      }
      // Object with message
      if (err.detail.message) return err.detail.message;
      if (err.detail.msg) return err.detail.msg;
      return JSON.stringify(err.detail);
    }
    return String(err.detail);
  }
  
  // Other common error fields
  if (typeof err.message === 'string') return err.message;
  if (typeof err.error === 'string') return err.error;
  if (typeof err.error_message === 'string') return err.error_message;
  
  // If err is a string itself
  if (typeof err === 'string') return err;
  
  // Fallback
  return `Error: ${statusCode}`;
}

async function api<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(`${API_URL}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  });
  
  if (!res.ok) {
    const err = await res.json().catch(() => null);
    throw new Error(extractErrorMessage(err, res.status));
  }
  
  return res.json();
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

// Sensor actions
export const getSensor = (id: string) => api<Sensor>(`/api/sensors/${id}`);
export const deleteSensor = (id: string) => api<{ status: string }>(`/api/sensors/${id}`, { method: 'DELETE' });
export const getSensorStatus = (id: string) => api<any>(`/api/sensors/${id}/status`);
export const turnOnSensor = (id: string) => api<Sensor>(`/api/sensors/${id}/turn-on`, { method: 'POST' });
export const turnOffSensor = (id: string) => api<Sensor>(`/api/sensors/${id}/turn-off`, { method: 'POST' });
export const fetchNow = (id: string) => api<any>(`/api/sensors/${id}/fetch-now`, { method: 'POST' });
