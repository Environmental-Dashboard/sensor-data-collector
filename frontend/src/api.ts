import type { Sensor, SensorListResponse, AddPurpleAirRequest, AddTempestRequest } from './types';

// Use environment variable for API URL, fallback to localhost for development
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

async function api<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(`${API_URL}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  });
  
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Error: ${res.status}`);
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

