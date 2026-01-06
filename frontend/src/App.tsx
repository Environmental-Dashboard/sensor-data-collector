import { useState, useEffect, useCallback } from 'react';
import {
  Activity, Wind, CloudSun, Droplets, Database,
  Plus, Power, PowerOff, Play, Trash2, X,
  Wifi, WifiOff, Clock, Globe, CheckCircle, XCircle, Loader2
} from 'lucide-react';
import type { Sensor, SensorType, AddPurpleAirRequest, AddTempestRequest } from './types';
import * as api from './api';

// Format relative time
function timeAgo(timestamp: string | null): string {
  if (!timestamp) return 'Never';
  const diff = Date.now() - new Date(timestamp).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'Just now';
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return new Date(timestamp).toLocaleDateString();
}

// Toast type
interface Toast {
  id: string;
  type: 'success' | 'error';
  message: string;
}

export default function App() {
  const [connected, setConnected] = useState(false);
  const [loading, setLoading] = useState(true);
  const [sensors, setSensors] = useState<Sensor[]>([]);
  const [modalType, setModalType] = useState<SensorType | null>(null);
  const [toasts, setToasts] = useState<Toast[]>([]);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  // Toast helpers
  const showToast = useCallback((type: 'success' | 'error', message: string) => {
    const id = Date.now().toString();
    setToasts(prev => [...prev, { id, type, message }]);
    setTimeout(() => setToasts(prev => prev.filter(t => t.id !== id)), 4000);
  }, []);

  // Fetch all sensors
  const fetchSensors = useCallback(async () => {
    try {
      const res = await api.getAllSensors();
      setSensors(res.sensors);
    } catch (e) {
      console.error('Failed to fetch sensors:', e);
    }
  }, []);

  // Health check
  const checkConnection = useCallback(async () => {
    try {
      await api.checkHealth();
      setConnected(true);
    } catch {
      setConnected(false);
    }
  }, []);

  // Initial load
  useEffect(() => {
    const init = async () => {
      await checkConnection();
      await fetchSensors();
      setLoading(false);
    };
    init();
    
    // Poll health every 30s
    const interval = setInterval(checkConnection, 30000);
    return () => clearInterval(interval);
  }, [checkConnection, fetchSensors]);

  // Sensor actions
  const handleTurnOn = async (sensor: Sensor) => {
    setActionLoading(sensor.id);
    try {
      await api.turnOnSensor(sensor.id);
      showToast('success', `${sensor.name} is now active!`);
      fetchSensors();
    } catch (e: any) {
      showToast('error', e.message);
    }
    setActionLoading(null);
  };

  const handleTurnOff = async (sensor: Sensor) => {
    setActionLoading(sensor.id);
    try {
      await api.turnOffSensor(sensor.id);
      showToast('success', `${sensor.name} stopped`);
      fetchSensors();
    } catch (e: any) {
      showToast('error', e.message);
    }
    setActionLoading(null);
  };

  const handleFetchNow = async (sensor: Sensor) => {
    setActionLoading(sensor.id);
    try {
      const result = await api.fetchNow(sensor.id);
      if (result.status === 'success') {
        showToast('success', `Data fetched from ${sensor.name}!`);
      } else {
        showToast('error', result.error_message || 'Fetch failed');
      }
      fetchSensors();
    } catch (e: any) {
      showToast('error', e.message);
    }
    setActionLoading(null);
  };

  const handleDelete = async (sensor: Sensor) => {
    if (!confirm(`Delete "${sensor.name}"? This cannot be undone.`)) return;
    setActionLoading(sensor.id);
    try {
      await api.deleteSensor(sensor.id);
      showToast('success', `${sensor.name} deleted`);
      fetchSensors();
    } catch (e: any) {
      showToast('error', e.message);
    }
    setActionLoading(null);
  };

  const handleAddSensor = async (data: AddPurpleAirRequest | AddTempestRequest) => {
    try {
      if (modalType === 'purple_air') {
        await api.addPurpleAirSensor(data as AddPurpleAirRequest);
      } else if (modalType === 'tempest') {
        await api.addTempestSensor(data as AddTempestRequest);
      }
      showToast('success', 'Sensor added!');
      setModalType(null);
      fetchSensors();
    } catch (e: any) {
      throw e;
    }
  };

  // Filter sensors by type
  const getSensorsByType = (type: SensorType) => sensors.filter(s => s.sensor_type === type);

  if (loading) {
    return (
      <div className="app" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '100vh' }}>
        <Loader2 size={40} style={{ animation: 'spin 1s linear infinite' }} />
        <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
      </div>
    );
  }

  return (
    <div className="app">
      {/* Header */}
      <header className="header">
        <div className="logo">
          <div className="logo-icon">
            <Activity size={24} color="white" />
          </div>
          <h1>Sensor Dashboard</h1>
        </div>
        <div className={`connection ${connected ? '' : 'offline'}`}>
          <span className="dot" />
          {connected ? <Wifi size={16} /> : <WifiOff size={16} />}
          {connected ? 'Connected' : 'Disconnected'}
        </div>
      </header>

      {/* Main */}
      <main className="main">
        <div className="grid">
          {/* Purple Air */}
          <SensorGroup
            type="purple_air"
            title="Air Quality"
            subtitle="Purple Air Sensors"
            icon={<Wind size={24} />}
            sensors={getSensorsByType('purple_air')}
            onAdd={() => setModalType('purple_air')}
            onTurnOn={handleTurnOn}
            onTurnOff={handleTurnOff}
            onFetchNow={handleFetchNow}
            onDelete={handleDelete}
            actionLoading={actionLoading}
          />

          {/* Tempest */}
          <SensorGroup
            type="tempest"
            title="Weather"
            subtitle="Tempest Stations"
            icon={<CloudSun size={24} />}
            sensors={getSensorsByType('tempest')}
            onAdd={() => setModalType('tempest')}
            onTurnOn={handleTurnOn}
            onTurnOff={handleTurnOff}
            onFetchNow={handleFetchNow}
            onDelete={handleDelete}
            actionLoading={actionLoading}
          />

          {/* Water Quality */}
          <div className="group-card water-quality">
            <div className="group-header">
              <div className="group-info">
                <div className="group-icon"><Droplets size={24} /></div>
                <div className="group-title">
                  <h2>Water Quality</h2>
                  <p>Water Sensors</p>
                </div>
              </div>
            </div>
            <div className="coming-soon">
              <div className="coming-soon-icon">🚧</div>
              <p>Coming Soon!</p>
            </div>
          </div>

          {/* Mayfly */}
          <div className="group-card mayfly">
            <div className="group-header">
              <div className="group-info">
                <div className="group-icon"><Database size={24} /></div>
                <div className="group-title">
                  <h2>Mayfly</h2>
                  <p>Data Loggers</p>
                </div>
              </div>
            </div>
            <div className="coming-soon">
              <div className="coming-soon-icon">🚧</div>
              <p>Coming Soon!</p>
            </div>
          </div>
        </div>
      </main>

      {/* Add Modal */}
      {modalType && (
        <AddSensorModal
          type={modalType}
          onClose={() => setModalType(null)}
          onSubmit={handleAddSensor}
        />
      )}

      {/* Toasts */}
      <div className="toast-container">
        {toasts.map(toast => (
          <div key={toast.id} className={`toast ${toast.type}`}>
            <span className="toast-icon">
              {toast.type === 'success' ? <CheckCircle size={20} /> : <XCircle size={20} />}
            </span>
            <span className="toast-message">{toast.message}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// Sensor Group Component
interface SensorGroupProps {
  type: SensorType;
  title: string;
  subtitle: string;
  icon: React.ReactNode;
  sensors: Sensor[];
  onAdd: () => void;
  onTurnOn: (s: Sensor) => void;
  onTurnOff: (s: Sensor) => void;
  onFetchNow: (s: Sensor) => void;
  onDelete: (s: Sensor) => void;
  actionLoading: string | null;
}

function SensorGroup({ type, title, subtitle, icon, sensors, onAdd, onTurnOn, onTurnOff, onFetchNow, onDelete, actionLoading }: SensorGroupProps) {
  const activeCount = sensors.filter(s => s.is_active).length;

  return (
    <div className={`group-card ${type.replace('_', '-')}`}>
      <div className="group-header">
        <div className="group-info">
          <div className="group-icon">{icon}</div>
          <div className="group-title">
            <h2>{title}</h2>
            <p>{subtitle}</p>
          </div>
        </div>
        <div className="group-count">{activeCount}/{sensors.length} active</div>
      </div>

      <div className="group-actions">
        <button className="btn btn-primary" onClick={onAdd}>
          <Plus size={16} /> Add Sensor
        </button>
      </div>

      <div className="sensor-list">
        {sensors.length === 0 ? (
          <div className="sensor-empty">No sensors yet. Click "Add Sensor" to get started!</div>
        ) : (
          sensors.map(sensor => (
            <SensorItem
              key={sensor.id}
              sensor={sensor}
              onTurnOn={() => onTurnOn(sensor)}
              onTurnOff={() => onTurnOff(sensor)}
              onFetchNow={() => onFetchNow(sensor)}
              onDelete={() => onDelete(sensor)}
              loading={actionLoading === sensor.id}
            />
          ))
        )}
      </div>
    </div>
  );
}

// Sensor Item Component
interface SensorItemProps {
  sensor: Sensor;
  onTurnOn: () => void;
  onTurnOff: () => void;
  onFetchNow: () => void;
  onDelete: () => void;
  loading: boolean;
}

function SensorItem({ sensor, onTurnOn, onTurnOff, onFetchNow, onDelete, loading }: SensorItemProps) {
  return (
    <div className="sensor-item">
      <div className="sensor-head">
        <div>
          <div className="sensor-name">{sensor.name}</div>
          <div className="sensor-location">{sensor.location}</div>
        </div>
        <div className={`sensor-status ${sensor.status}`}>
          {sensor.status === 'active' && <Power size={12} />}
          {sensor.status === 'inactive' && <PowerOff size={12} />}
          {sensor.status === 'error' && <XCircle size={12} />}
          {sensor.status}
        </div>
      </div>

      <div className="sensor-meta">
        {sensor.ip_address && (
          <span><Globe size={12} /> <code>{sensor.ip_address}</code></span>
        )}
        <span><Clock size={12} /> {timeAgo(sensor.last_active)}</span>
      </div>

      {sensor.last_error && (
        <div className="sensor-error">{sensor.last_error}</div>
      )}

      <div className="sensor-actions">
        {sensor.is_active ? (
          <button className="btn btn-danger" onClick={onTurnOff} disabled={loading}>
            <PowerOff size={14} /> Turn Off
          </button>
        ) : (
          <button className="btn btn-success" onClick={onTurnOn} disabled={loading}>
            <Power size={14} /> Turn On
          </button>
        )}
        <button className="btn" onClick={onFetchNow} disabled={loading}>
          <Play size={14} /> Fetch
        </button>
        <button className="btn btn-icon btn-danger" onClick={onDelete} disabled={loading}>
          <Trash2 size={14} />
        </button>
      </div>
    </div>
  );
}

// Add Sensor Modal
interface AddSensorModalProps {
  type: SensorType;
  onClose: () => void;
  onSubmit: (data: any) => Promise<void>;
}

function AddSensorModal({ type, onClose, onSubmit }: AddSensorModalProps) {
  const [ip, setIp] = useState('');
  const [name, setName] = useState('');
  const [location, setLocation] = useState('');
  const [token, setToken] = useState('');
  const [deviceId, setDeviceId] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!ip || !name || !location || !token) {
      setError('All fields are required');
      return;
    }

    if (type === 'tempest' && !deviceId) {
      setError('Device ID is required for Tempest');
      return;
    }

    setLoading(true);
    try {
      if (type === 'purple_air') {
        await onSubmit({ ip_address: ip, name, location, upload_token: token });
      } else {
        await onSubmit({ ip_address: ip, name, location, device_id: deviceId, upload_token: token });
      }
    } catch (e: any) {
      setError(e.message);
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal">
        <div className="modal-header">
          <h2>Add {type === 'purple_air' ? 'Purple Air' : 'Tempest'} Sensor</h2>
          <button className="modal-close" onClick={onClose}><X size={20} /></button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="modal-body">
            {error && <div className="form-error">{error}</div>}

            <div className="form-group">
              <label className="form-label">IP Address</label>
              <input
                type="text"
                className="form-input mono"
                placeholder="192.168.1.100"
                value={ip}
                onChange={e => setIp(e.target.value)}
                disabled={loading}
              />
            </div>

            <div className="form-group">
              <label className="form-label">Sensor Name</label>
              <input
                type="text"
                className="form-input"
                placeholder="Lab Sensor"
                value={name}
                onChange={e => setName(e.target.value)}
                disabled={loading}
              />
            </div>

            <div className="form-group">
              <label className="form-label">Location</label>
              <input
                type="text"
                className="form-input"
                placeholder="Science Building Room 201"
                value={location}
                onChange={e => setLocation(e.target.value)}
                disabled={loading}
              />
            </div>

            {type === 'tempest' && (
              <div className="form-group">
                <label className="form-label">Device ID</label>
                <input
                  type="text"
                  className="form-input mono"
                  placeholder="12345"
                  value={deviceId}
                  onChange={e => setDeviceId(e.target.value)}
                  disabled={loading}
                />
              </div>
            )}

            <div className="form-group">
              <label className="form-label">Upload Token</label>
              <input
                type="password"
                className="form-input"
                placeholder="Your token from communityhub"
                value={token}
                onChange={e => setToken(e.target.value)}
                disabled={loading}
              />
            </div>
          </div>

          <div className="modal-footer">
            <button type="button" className="btn" onClick={onClose} disabled={loading}>Cancel</button>
            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? <Loader2 size={16} style={{ animation: 'spin 1s linear infinite' }} /> : <Plus size={16} />}
              Add Sensor
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

