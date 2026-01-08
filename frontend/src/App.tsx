import { useState, useEffect, useCallback } from 'react';
import {
  Wind, CloudSun, Droplets, Database,
  Plus, Power, PowerOff, Play, Trash2, X,
  Wifi, WifiOff, Clock, Globe, CheckCircle, XCircle, Loader2,
  Sun, Moon, Battery
} from 'lucide-react';
import type { Sensor, SensorType, AddPurpleAirRequest, AddTempestRequest } from './types';
import * as api from './api';
import iconImage from './images/icon.png';

// Theme hook
function useTheme() {
  const [theme, setTheme] = useState<'light' | 'dark'>(() => {
    // Check if we're in a browser environment
    if (typeof window === 'undefined') return 'light';
    return document.documentElement.classList.contains('dark') ? 'dark' : 'light';
  });

  const toggleTheme = useCallback(() => {
    setTheme(prev => {
      const newTheme = prev === 'light' ? 'dark' : 'light';
      
      // Update DOM
      if (newTheme === 'dark') {
        document.documentElement.classList.add('dark');
      } else {
        document.documentElement.classList.remove('dark');
      }
      
      // Persist preference
      localStorage.setItem('theme', newTheme);
      
      // Update theme-color meta tag for mobile browsers
      const metaThemeColor = document.querySelector('meta[name="theme-color"]');
      if (metaThemeColor) {
        metaThemeColor.setAttribute('content', newTheme === 'dark' ? '#0a0a0a' : '#ffffff');
      }
      
      return newTheme;
    });
  }, []);

  return { theme, toggleTheme };
}

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

// Tab configuration
const tabs = [
  { id: 'purple_air' as SensorType, label: 'Air Quality', icon: Wind, color: 'purple' },
  { id: 'tempest' as SensorType, label: 'Weather', icon: CloudSun, color: 'cyan' },
  { id: 'water_quality' as SensorType, label: 'Water Quality', icon: Droplets, color: 'blue' },
  { id: 'do_sensor' as SensorType, label: 'DO Sensor', icon: Database, color: 'amber' },
];

// Toast type
interface Toast {
  id: string;
  type: 'success' | 'error';
  message: string;
}

export default function App() {
  const { theme, toggleTheme } = useTheme();
  const [connected, setConnected] = useState(false);
  const [loading, setLoading] = useState(true);
  const [sensors, setSensors] = useState<Sensor[]>([]);
  const [activeTab, setActiveTab] = useState<SensorType>('purple_air');
  const [modalOpen, setModalOpen] = useState(false);
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
      const msg = typeof e.message === 'string' ? e.message : 'Failed to turn on sensor';
      showToast('error', msg);
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
      const msg = typeof e.message === 'string' ? e.message : 'Failed to turn off sensor';
      showToast('error', msg);
    }
    setActionLoading(null);
  };

  const handleFetchNow = async (sensor: Sensor) => {
    setActionLoading(sensor.id);
    try {
      const result = await api.fetchNow(sensor.id);
      if (result.status === 'success') {
        showToast('success', `✓ ${sensor.name} is active and working!`);
      } else if (result.status === 'info') {
        // Tempest auto-push info message
        const msg = typeof result.message === 'string' ? result.message : 'Sensor is working';
        showToast('success', msg);
      } else {
        // Handle error - make sure we get a string
        const errorMsg = typeof result.error_message === 'string' 
          ? result.error_message 
          : (typeof result.message === 'string' ? result.message : 'Ping failed');
        showToast('error', errorMsg);
      }
      fetchSensors();
    } catch (e: any) {
      const errorMsg = typeof e.message === 'string' ? e.message : 'An error occurred';
      showToast('error', errorMsg);
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
      const msg = typeof e.message === 'string' ? e.message : 'Failed to delete sensor';
      showToast('error', msg);
    }
    setActionLoading(null);
  };

  const handleAddSensor = async (data: AddPurpleAirRequest | AddTempestRequest) => {
    try {
      if (activeTab === 'purple_air') {
        await api.addPurpleAirSensor(data as AddPurpleAirRequest);
      } else if (activeTab === 'tempest') {
        await api.addTempestSensor(data as AddTempestRequest);
      }
      showToast('success', 'Sensor added!');
      setModalOpen(false);
      fetchSensors();
    } catch (e: any) {
      throw e;
    }
  };

  // Get sensors for current tab
  const currentSensors = sensors.filter(s => s.sensor_type === activeTab);
  const activeCount = currentSensors.filter(s => s.is_active).length;
  const currentTab = tabs.find(t => t.id === activeTab)!;
  const isImplemented = activeTab === 'purple_air' || activeTab === 'tempest';

  if (loading) {
    return (
      <div className="app loading-screen">
        <Loader2 size={40} className="spinner" />
      </div>
    );
  }

  return (
    <div className="app">
      {/* Header */}
      <header className="header">
        <div className="logo">
          <div className="logo-icon">
            <img src={iconImage} alt="Sensor Dashboard" style={{ width: '100%', height: '100%', objectFit: 'contain' }} />
          </div>
          <h1>Sensor Dashboard</h1>
        </div>
        <div className="header-right">
          {/* Theme Toggle */}
          <button 
            className="theme-toggle" 
            onClick={toggleTheme}
            aria-label={`Switch to ${theme === 'light' ? 'dark' : 'light'} mode`}
            title={`Switch to ${theme === 'light' ? 'dark' : 'light'} mode`}
          >
            {theme === 'light' ? <Moon size={18} /> : <Sun size={18} />}
          </button>
          
          {/* Connection Status */}
          <div className={`connection ${connected ? '' : 'offline'}`}>
            <span className="dot" />
            {connected ? <Wifi size={16} /> : <WifiOff size={16} />}
            {connected ? 'Connected' : 'Disconnected'}
          </div>
        </div>
      </header>

      {/* Tabs */}
      <nav className="tabs">
        {tabs.map(tab => {
          const Icon = tab.icon;
          const count = sensors.filter(s => s.sensor_type === tab.id).length;
          const active = sensors.filter(s => s.sensor_type === tab.id && s.is_active).length;
          return (
            <button
              key={tab.id}
              className={`tab ${activeTab === tab.id ? 'active' : ''} ${tab.color}`}
              onClick={() => setActiveTab(tab.id)}
            >
              <Icon size={20} />
              <span className="tab-label">{tab.label}</span>
              {count > 0 && (
                <span className="tab-count">{active}/{count}</span>
              )}
            </button>
          );
        })}
      </nav>

      {/* Content */}
      <main className="main">
        <div className="content-card">
          {/* Content Header */}
          <div className={`content-header ${currentTab.color}`}>
            <div className="content-header-left">
              <div className="content-icon">
                <currentTab.icon size={28} />
              </div>
              <div>
                <h2>{currentTab.label}</h2>
                <p>{activeCount} of {currentSensors.length} sensors active</p>
              </div>
            </div>
            {isImplemented && (
              <button className="btn btn-primary" onClick={() => setModalOpen(true)}>
                <Plus size={18} />
                Add Sensor
              </button>
            )}
          </div>

          {/* Content Body */}
          <div className="content-body">
            {!isImplemented ? (
              <div className="coming-soon">
                <div className="coming-soon-icon">🚧</div>
                <h3>Coming Soon!</h3>
                <p>We're working on adding support for {currentTab.label} sensors.</p>
              </div>
            ) : currentSensors.length === 0 ? (
              <div className="empty-state">
                <currentTab.icon size={48} strokeWidth={1} />
                <h3>No Sensors Yet</h3>
                <p>Add your first {currentTab.label.toLowerCase()} sensor to get started.</p>
                <button className="btn btn-primary" onClick={() => setModalOpen(true)}>
                  <Plus size={18} />
                  Add Sensor
                </button>
              </div>
            ) : (
              <div className="sensor-grid">
                {currentSensors.map(sensor => (
                  <SensorCard
                    key={sensor.id}
                    sensor={sensor}
                    onTurnOn={() => handleTurnOn(sensor)}
                    onTurnOff={() => handleTurnOff(sensor)}
                    onFetchNow={() => handleFetchNow(sensor)}
                    onDelete={() => handleDelete(sensor)}
                    loading={actionLoading === sensor.id}
                  />
                ))}
              </div>
            )}
          </div>
        </div>
      </main>

      {/* Add Modal */}
      {modalOpen && (
        <AddSensorModal
          type={activeTab}
          onClose={() => setModalOpen(false)}
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

// Sensor Card Component
interface SensorCardProps {
  sensor: Sensor;
  onTurnOn: () => void;
  onTurnOff: () => void;
  onFetchNow: () => void;
  onDelete: () => void;
  loading: boolean;
}

function SensorCard({ sensor, onTurnOn, onTurnOff, onFetchNow, onDelete, loading }: SensorCardProps) {
  return (
    <div className={`sensor-card ${sensor.status}`}>
      <div className="sensor-card-header">
        <div>
          <h3 className="sensor-name">{sensor.name}</h3>
          <p className="sensor-location">{sensor.location}</p>
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
          <div className="meta-item">
            <Globe size={14} />
            <code>{sensor.ip_address}</code>
          </div>
        )}
        {sensor.sensor_type === 'tempest' && sensor.battery_volts !== null && (
          <div className={`meta-item ${sensor.battery_volts < 2.5 ? 'battery-low' : ''}`}>
            <Battery size={14} />
            <span>{sensor.battery_volts}V</span>
          </div>
        )}
        <div className="meta-item">
          <Clock size={14} />
          <span>{timeAgo(sensor.last_active)}</span>
        </div>
      </div>

      {sensor.last_error && (
        <div className="sensor-error">{sensor.last_error}</div>
      )}

      <div className="sensor-actions">
        {sensor.is_active ? (
          <button className="btn btn-danger" onClick={onTurnOff} disabled={loading}>
            <PowerOff size={16} /> Turn Off
          </button>
        ) : (
          <button className="btn btn-success" onClick={onTurnOn} disabled={loading}>
            <Power size={16} /> Turn On
          </button>
        )}
        {/* Tempest pushes data automatically, show auto-push badge */}
        {sensor.sensor_type === 'tempest' && sensor.is_active && (
          <span className="auto-push-badge">Auto-push</span>
        )}
        {/* Purple Air and others: Ping button to test connection */}
        {sensor.sensor_type !== 'tempest' && (
          <button className="btn" onClick={onFetchNow} disabled={loading}>
            <Play size={16} /> Ping
          </button>
        )}
        <button className="btn btn-icon btn-danger" onClick={onDelete} disabled={loading}>
          <Trash2 size={16} />
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

    // Validate based on sensor type
    if (type === 'purple_air') {
      if (!ip || !name || !location || !token) {
        setError('All fields are required');
        return;
      }
    } else if (type === 'tempest') {
      if (!deviceId || !location || !token) {
        setError('Device ID, Location, and Upload Token are required');
        return;
      }
    }

    setLoading(true);
    try {
      if (type === 'purple_air') {
        await onSubmit({ ip_address: ip, name, location, upload_token: token });
      } else if (type === 'tempest') {
        await onSubmit({ device_id: deviceId, location, upload_token: token });
      }
    } catch (e: any) {
      const msg = typeof e.message === 'string' ? e.message : 'Failed to add sensor';
      setError(msg);
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal">
        <div className="modal-header">
          <h2>
            {type === 'purple_air' && 'Add Air Quality Sensor'}
            {type === 'tempest' && 'Add Weather Station'}
            {type === 'water_quality' && 'Add Water Quality Sensor'}
            {type === 'do_sensor' && 'Add DO Sensor'}
          </h2>
          <button className="modal-close" onClick={onClose}><X size={20} /></button>
        </div>
        <form onSubmit={handleSubmit}>
          <div className="modal-body">
            {error && <div className="form-error">{error}</div>}
            
            {/* Purple Air: IP Address */}
            {type === 'purple_air' && (
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
                <p className="form-hint">Find this in your router or PurpleAir app</p>
              </div>
            )}

            {/* Tempest: Device ID */}
            {type === 'tempest' && (
              <div className="form-group">
                <label className="form-label">Device ID</label>
                <input
                  type="text"
                  className="form-input mono"
                  placeholder="205498"
                  value={deviceId}
                  onChange={e => setDeviceId(e.target.value)}
                  disabled={loading}
                />
                <p className="form-hint">Find in WeatherFlow app under station settings</p>
              </div>
            )}

            {/* Purple Air: Sensor Name */}
            {type === 'purple_air' && (
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
            )}

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
              <p className="form-hint">Get this from oberlin.communityhub.cloud</p>
            </div>
          </div>

          <div className="modal-footer">
            <button type="button" className="btn" onClick={onClose} disabled={loading}>Cancel</button>
            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? <Loader2 size={16} className="spinner" /> : <Plus size={16} />}
              Add Sensor
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
