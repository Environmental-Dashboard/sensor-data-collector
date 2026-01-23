import { useState, useEffect, useCallback, useRef } from 'react';
import {
  Wind, CloudSun, Droplets, Database, Zap,
  Plus, Power, PowerOff, Play, Trash2, X,
  Wifi, WifiOff, Clock, Globe, CheckCircle, XCircle, Loader2,
  Sun, Moon, Battery, Cloud, Sunrise, Settings, MoreVertical,
  Edit, Link, RefreshCw, Eye
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
  { id: 'voltage_meter' as SensorType, label: 'Battery Monitor', icon: Battery, color: 'green' },
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
  
  // Modal states for sensor options
  const [lastDataModal, setLastDataModal] = useState<{ open: boolean; sensor: Sensor | null; data: string | null }>({ open: false, sensor: null, data: null });
  const [editModal, setEditModal] = useState<{ open: boolean; sensor: Sensor | null }>({ open: false, sensor: null });
  const [thresholdsModal, setThresholdsModal] = useState<{ open: boolean; sensor: Sensor | null }>({ open: false, sensor: null });
  const [calibrateModal, setCalibrateModal] = useState<{ open: boolean; sensor: Sensor | null }>({ open: false, sensor: null });

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

  // Relay control for voltage meters
  const handleRelayControl = async (sensor: Sensor, mode: 'auto' | 'on' | 'off') => {
    setActionLoading(sensor.id);
    try {
      await api.setRelayMode(sensor.id, mode);
      const modeLabel = mode === 'auto' ? 'Automatic' : mode === 'on' ? 'Force ON' : 'Force OFF';
      showToast('success', `Relay set to ${modeLabel}`);
      fetchSensors();
    } catch (e: any) {
      const msg = typeof e.message === 'string' ? e.message : 'Failed to set relay mode';
      showToast('error', msg);
    }
    setActionLoading(null);
  };

  // Power mode change for Purple Air
  const handlePowerModeChange = async (sensor: Sensor, mode: 'normal' | 'power_saving') => {
    setActionLoading(sensor.id);
    try {
      await api.setPowerMode(sensor.id, mode);
      const modeLabel = mode === 'normal' ? 'Normal' : 'Power Saving';
      showToast('success', `Power mode set to ${modeLabel}`);
      fetchSensors();
    } catch (e: any) {
      const msg = typeof e.message === 'string' ? e.message : 'Failed to set power mode';
      showToast('error', msg);
    }
    setActionLoading(null);
  };

  // Frequency change for sensors
  const handleFrequencyChange = async (sensor: Sensor, minutes: number) => {
    setActionLoading(sensor.id);
    try {
      await api.setPollingFrequency(sensor.id, minutes);
      showToast('success', `Poll frequency set to ${minutes} minutes`);
      fetchSensors();
    } catch (e: any) {
      const msg = typeof e.message === 'string' ? e.message : 'Failed to set frequency';
      showToast('error', msg);
    }
    setActionLoading(null);
  };

  // View last sent data
  const handleViewLastData = async (sensor: Sensor) => {
    try {
      const result = await api.getLastSentData(sensor.id);
      setLastDataModal({ open: true, sensor, data: result.last_csv_sample || 'No data sent yet' });
    } catch (e: any) {
      showToast('error', 'Failed to get last sent data');
    }
  };

  // Open edit sensor modal
  const handleEditSensor = (sensor: Sensor) => {
    setEditModal({ open: true, sensor });
  };

  // Save edited sensor
  const handleSaveEdit = async (sensor: Sensor, updates: { name?: string; location?: string; ip_address?: string }) => {
    setActionLoading(sensor.id);
    try {
      await api.updateSensor(sensor.id, updates);
      showToast('success', 'Sensor updated');
      setEditModal({ open: false, sensor: null });
      fetchSensors();
    } catch (e: any) {
      const msg = typeof e.message === 'string' ? e.message : 'Failed to update sensor';
      showToast('error', msg);
    }
    setActionLoading(null);
  };

  // Open thresholds modal
  const handleSetThresholds = (sensor: Sensor) => {
    setThresholdsModal({ open: true, sensor });
  };

  // Save thresholds
  const handleSaveThresholds = async (sensor: Sensor, cutoff: number, reconnect: number) => {
    setActionLoading(sensor.id);
    try {
      await api.setThresholds(sensor.id, cutoff, reconnect);
      showToast('success', 'Thresholds updated');
      setThresholdsModal({ open: false, sensor: null });
      fetchSensors();
    } catch (e: any) {
      const msg = typeof e.message === 'string' ? e.message : 'Failed to set thresholds';
      showToast('error', msg);
    }
    setActionLoading(null);
  };

  const handleCalibrate = async (sensor: Sensor, targetVoltage: number) => {
    setActionLoading(sensor.id);
    try {
      await api.calibrateVoltageMeter(sensor.id, targetVoltage);
      showToast('success', `Calibrated to ${targetVoltage}V`);
      setCalibrateModal({ open: false, sensor: null });
      fetchSensors();
    } catch (e: any) {
      const msg = typeof e.message === 'string' ? e.message : 'Failed to calibrate';
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
  const isImplemented = activeTab === 'purple_air' || activeTab === 'tempest' || activeTab === 'voltage_meter';

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
                    onRelayControl={sensor.sensor_type === 'voltage_meter' ? (mode) => handleRelayControl(sensor, mode) : undefined}
                    onPowerModeChange={sensor.sensor_type === 'purple_air' ? (mode) => handlePowerModeChange(sensor, mode) : undefined}
                    onFrequencyChange={sensor.sensor_type === 'purple_air' ? (minutes) => handleFrequencyChange(sensor, minutes) : undefined}
                    onViewLastData={() => handleViewLastData(sensor)}
                    onEditSensor={() => handleEditSensor(sensor)}
                    onSetThresholds={sensor.sensor_type === 'voltage_meter' ? () => handleSetThresholds(sensor) : undefined}
                    onCalibrate={sensor.sensor_type === 'voltage_meter' ? () => setCalibrateModal({ open: true, sensor }) : undefined}
                    relayLoading={actionLoading === sensor.id}
                    voltageMeterSensors={sensors.filter(s => s.sensor_type === 'voltage_meter' && !s.linked_sensor_id)}
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

      {/* Last Data Modal */}
      {lastDataModal.open && lastDataModal.sensor && (
        <LastDataModal
          sensor={lastDataModal.sensor}
          data={lastDataModal.data}
          onClose={() => setLastDataModal({ open: false, sensor: null, data: null })}
        />
      )}

      {/* Edit Sensor Modal */}
      {editModal.open && editModal.sensor && (
        <EditSensorModal
          sensor={editModal.sensor}
          onClose={() => setEditModal({ open: false, sensor: null })}
          onSave={(updates) => handleSaveEdit(editModal.sensor!, updates)}
          loading={actionLoading === editModal.sensor.id}
        />
      )}

      {/* Thresholds Modal */}
      {thresholdsModal.open && thresholdsModal.sensor && (
        <ThresholdsModal
          sensor={thresholdsModal.sensor}
          onClose={() => setThresholdsModal({ open: false, sensor: null })}
          onSave={(cutoff, reconnect) => handleSaveThresholds(thresholdsModal.sensor!, cutoff, reconnect)}
          loading={actionLoading === thresholdsModal.sensor.id}
        />
      )}

      {/* Calibrate Modal */}
      {calibrateModal.open && calibrateModal.sensor && (
        <CalibrateModal
          sensor={calibrateModal.sensor}
          onClose={() => setCalibrateModal({ open: false, sensor: null })}
          onSave={(targetVoltage) => handleCalibrate(calibrateModal.sensor!, targetVoltage)}
          loading={actionLoading === calibrateModal.sensor.id}
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
  onRelayControl?: (mode: 'auto' | 'on' | 'off') => void;
  onPowerModeChange?: (mode: 'normal' | 'power_saving') => void;
  onFrequencyChange?: (minutes: number) => void;
  onViewLastData?: () => void;
  onEditSensor?: () => void;
  onSetThresholds?: () => void;
  onCalibrate?: () => void;
  relayLoading?: boolean;
  voltageMeterSensors?: Sensor[];
  onLinkVoltageMeter?: (voltageMeterI: string) => void;
}

function SensorCard({ sensor, onTurnOn, onTurnOff, onFetchNow, onDelete, loading, onRelayControl, onPowerModeChange, onFrequencyChange, onViewLastData, onEditSensor, onSetThresholds, onCalibrate, relayLoading, voltageMeterSensors, onLinkVoltageMeter }: SensorCardProps) {
  const [showMenu, setShowMenu] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const cardRef = useRef<HTMLDivElement>(null);

  // Close menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as Node;
      if (showMenu && menuRef.current && !menuRef.current.contains(target)) {
        setShowMenu(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [showMenu]);

  // Get relay mode text for voltage meters
  const getRelayModeText = () => {
    if (sensor.sensor_type !== 'voltage_meter') return null;
    if (sensor.auto_mode === true) return 'Auto';
    if (sensor.load_on === true) return 'Force ON';
    if (sensor.load_on === false) return 'Force OFF';
    return null;
  };

  return (
    <div className={`sensor-card ${sensor.status}`} ref={cardRef}>
      <div className="sensor-card-header">
        <div>
          <h3 className="sensor-name">{sensor.name}</h3>
          <p className="sensor-location">{sensor.location}</p>
        </div>
        <div className={`sensor-status ${sensor.status} ${sensor.status_reason === 'battery_low' ? 'battery-low' : ''} ${sensor.status_reason === 'cloud_error' ? 'cloud-error' : ''}`}>
          {sensor.status === 'active' && <Power size={12} />}
          {sensor.status === 'inactive' && <PowerOff size={12} />}
          {sensor.status === 'sleeping' && <Moon size={12} />}
          {sensor.status === 'waking' && <Sunrise size={12} />}
          {sensor.status === 'error' && sensor.status_reason !== 'cloud_error' && <XCircle size={12} />}
          {sensor.status === 'error' && sensor.status_reason === 'cloud_error' && <Cloud size={12} />}
          {sensor.status === 'offline' && sensor.status_reason === 'battery_low' && <Battery size={12} />}
          {sensor.status === 'offline' && sensor.status_reason !== 'battery_low' && <WifiOff size={12} />}
          {sensor.status === 'sleeping' ? 'sleeping' :
           sensor.status === 'waking' ? 'waking up' :
           sensor.status_reason === 'battery_low' ? 'low battery' : 
           sensor.status_reason === 'cloud_error' ? 'cloud issue' : 
           sensor.status}
        </div>
      </div>

      <div className="sensor-meta">
        {sensor.ip_address && (
          <div className="meta-item">
            <Globe size={14} />
            <code>{sensor.ip_address}</code>
          </div>
        )}
        {/* Battery voltage for Tempest and Voltage Meter */}
        {(sensor.sensor_type === 'tempest' || sensor.sensor_type === 'voltage_meter') && sensor.battery_volts !== null && (
          <div className={`meta-item ${sensor.sensor_type === 'tempest' && sensor.battery_volts < 2.5 ? 'battery-low' : ''}`}>
            <Battery size={14} />
            <span>{sensor.battery_volts.toFixed(2)}V</span>
          </div>
        )}
        {/* Relay mode indicator for Voltage Meter */}
        {sensor.sensor_type === 'voltage_meter' && (
          <div className={`meta-item relay-mode ${sensor.load_on ? 'relay-on' : 'relay-off'}`}>
            <Zap size={14} />
            <span>Relay: {sensor.load_on ? 'ON' : 'OFF'} ({getRelayModeText()})</span>
          </div>
        )}
        {/* Threshold info for Voltage Meter */}
        {sensor.sensor_type === 'voltage_meter' && sensor.v_cutoff && sensor.v_reconnect && (
          <div className="meta-item">
            <span className="threshold-info">Cut: {sensor.v_cutoff}V / Rec: {sensor.v_reconnect}V</span>
          </div>
        )}
        {/* Power mode indicator for Purple Air */}
        {sensor.sensor_type === 'purple_air' && sensor.power_mode === 'power_saving' && (
          <div className="meta-item power-mode">
            <Moon size={14} />
            <span>Power Saving ({Math.round((sensor.polling_frequency || 300) / 60)}m)</span>
          </div>
        )}
        {/* Linked sensor for Voltage Meter */}
        {sensor.sensor_type === 'voltage_meter' && sensor.linked_sensor_name && (
          <div className="meta-item linked-sensor">
            <Link size={14} />
            <span>Controls: {sensor.linked_sensor_name}</span>
          </div>
        )}
        <div className="meta-item">
          <Clock size={14} />
          <span>{timeAgo(sensor.last_active)}</span>
        </div>
      </div>

      {/* Sleeping indicator (power saving mode) */}
      {sensor.status === 'sleeping' && (
        <div className="sensor-sleeping">
          <Moon size={14} /> Sleeping until next poll (power saving mode)
        </div>
      )}
      {/* Waking indicator (power saving mode) */}
      {sensor.status === 'waking' && (
        <div className="sensor-waking">
          <Sunrise size={14} /> Waking up... connecting to WiFi
        </div>
      )}
      {/* Battery Low Warning (not an error - expected state) */}
      {sensor.status_reason === 'battery_low' && sensor.battery_volts !== null && (
        <div className="sensor-warning">
          <Battery size={14} /> Battery Low ({sensor.battery_volts.toFixed(1)}V) - Sensor powered off
        </div>
      )}
      {/* Cloud Error (not sensor's fault) */}
      {sensor.last_error && sensor.status_reason === 'cloud_error' && (
        <div className="sensor-cloud-error">
          <Cloud size={14} /> {sensor.last_error}
        </div>
      )}
      {/* Regular Errors - but NOT the "Relay OFF but voltage OK" message for power saving mode */}
      {sensor.last_error && 
       sensor.status_reason !== 'battery_low' && 
       sensor.status_reason !== 'cloud_error' && 
       !(sensor.status === 'sleeping' && sensor.last_error.includes('Relay OFF')) && (
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
        {/* Three-dot options menu - ONLY menu, no separate gear */}
        <div className="menu-container" ref={menuRef}>
          <button className="btn btn-icon" onClick={() => setShowMenu(!showMenu)} title="Options">
            <MoreVertical size={16} />
          </button>
          {showMenu && (
            <div className="dropdown-menu">
              {/* View Last Data */}
              {onViewLastData && (
                <button className="dropdown-item" onClick={() => { onViewLastData(); setShowMenu(false); }}>
                  <Eye size={14} /> View Last Sent Data
                </button>
              )}
              
              {/* Edit Sensor */}
              {onEditSensor && (
                <button className="dropdown-item" onClick={() => { onEditSensor(); setShowMenu(false); }}>
                  <Edit size={14} /> Edit Sensor
                </button>
              )}
              
              {/* Refresh Now */}
              <button className="dropdown-item" onClick={() => { onFetchNow(); setShowMenu(false); }}>
                <RefreshCw size={14} /> Refresh Now
              </button>

              {/* ===== PURPLE AIR OPTIONS ===== */}
              {sensor.sensor_type === 'purple_air' && onPowerModeChange && (
                <>
                  <div className="dropdown-divider" />
                  <div className="dropdown-section-label">Power Mode</div>
                  <button 
                    className={`dropdown-item ${sensor.power_mode !== 'power_saving' ? 'active' : ''}`}
                    onClick={() => { onPowerModeChange('normal'); setShowMenu(false); }}
                  >
                    <Power size={14} /> Normal Mode
                  </button>
                  <button 
                    className={`dropdown-item ${sensor.power_mode === 'power_saving' ? 'active' : ''}`}
                    onClick={() => { onPowerModeChange('power_saving'); setShowMenu(false); }}
                  >
                    <Moon size={14} /> Power Saving Mode
                  </button>
                </>
              )}
              
              {/* Poll Frequency (only for power saving mode) */}
              {sensor.sensor_type === 'purple_air' && sensor.power_mode === 'power_saving' && onFrequencyChange && (
                <>
                  <div className="dropdown-section-label">Poll Frequency</div>
                  <div className="dropdown-frequency-buttons">
                    {[5, 10, 15, 30, 60].map(mins => (
                      <button 
                        key={mins}
                        className={`freq-btn ${sensor.polling_frequency === mins * 60 ? 'active' : ''}`}
                        onClick={() => { onFrequencyChange(mins); setShowMenu(false); }}
                      >
                        {mins}m
                      </button>
                    ))}
                  </div>
                </>
              )}
              
              {/* Link Battery Monitor */}
              {sensor.sensor_type === 'purple_air' && voltageMeterSensors && voltageMeterSensors.length > 0 && (
                <button className="dropdown-item" onClick={() => { onLinkVoltageMeter?.(voltageMeterSensors[0].id); setShowMenu(false); }}>
                  <Link size={14} /> Link Battery Monitor
                </button>
              )}

              {/* ===== VOLTAGE METER OPTIONS ===== */}
              {sensor.sensor_type === 'voltage_meter' && onRelayControl && (
                <>
                  <div className="dropdown-divider" />
                  <div className="dropdown-section-label">Relay Control</div>
                  <button 
                    className={`dropdown-item ${sensor.auto_mode ? 'active' : ''}`}
                    onClick={() => { onRelayControl('auto'); setShowMenu(false); }}
                    disabled={relayLoading}
                  >
                    <Zap size={14} /> Automatic
                  </button>
                  <button 
                    className={`dropdown-item ${!sensor.auto_mode && sensor.load_on ? 'active' : ''}`}
                    onClick={() => { onRelayControl('on'); setShowMenu(false); }}
                    disabled={relayLoading}
                  >
                    <Power size={14} /> Force ON
                  </button>
                  <button 
                    className={`dropdown-item ${!sensor.auto_mode && !sensor.load_on ? 'active' : ''}`}
                    onClick={() => { onRelayControl('off'); setShowMenu(false); }}
                    disabled={relayLoading}
                  >
                    <PowerOff size={14} /> Force OFF
                  </button>
                </>
              )}
              
              {/* Set Thresholds */}
              {sensor.sensor_type === 'voltage_meter' && onSetThresholds && (
                <button className="dropdown-item" onClick={() => { onSetThresholds(); setShowMenu(false); }}>
                  <Battery size={14} /> Set Voltage Thresholds
                </button>
              )}
              
              {/* Calibrate ADC */}
              {sensor.sensor_type === 'voltage_meter' && onCalibrate && (
                <button className="dropdown-item" onClick={() => { onCalibrate(); setShowMenu(false); }}>
                  <Settings size={14} /> Calibrate ADC
                </button>
              )}

              {/* ===== DELETE ===== */}
              <div className="dropdown-divider" />
              <button className="dropdown-item danger" onClick={() => { onDelete(); setShowMenu(false); }}>
                <Trash2 size={14} /> Delete Sensor
              </button>
            </div>
          )}
        </div>
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

// Edit Sensor Modal
interface EditSensorModalProps {
  sensor: Sensor;
  onClose: () => void;
  onSave: (updates: { name?: string; location?: string; ip_address?: string }) => void;
  loading: boolean;
}

function EditSensorModal({ sensor, onClose, onSave, loading }: EditSensorModalProps) {
  const [name, setName] = useState(sensor.name);
  const [location, setLocation] = useState(sensor.location);
  const [ipAddress, setIpAddress] = useState(sensor.ip_address || '');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const updates: { name?: string; location?: string; ip_address?: string } = {};
    if (name !== sensor.name) updates.name = name;
    if (location !== sensor.location) updates.location = location;
    if (ipAddress !== (sensor.ip_address || '')) updates.ip_address = ipAddress;
    onSave(updates);
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Edit Sensor</h2>
          <button className="modal-close" onClick={onClose}><X size={20} /></button>
        </div>
        <form onSubmit={handleSubmit}>
          <div className="modal-body">
            <div className="form-group">
              <label className="form-label">Name</label>
              <input
                type="text"
                className="form-input"
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
                value={location}
                onChange={e => setLocation(e.target.value)}
                disabled={loading}
              />
            </div>
            {sensor.ip_address && (
              <div className="form-group">
                <label className="form-label">IP Address</label>
                <input
                  type="text"
                  className="form-input mono"
                  value={ipAddress}
                  onChange={e => setIpAddress(e.target.value)}
                  disabled={loading}
                />
              </div>
            )}
          </div>
          <div className="modal-footer">
            <button type="button" className="btn" onClick={onClose} disabled={loading}>Cancel</button>
            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? <Loader2 size={16} className="spinner" /> : <CheckCircle size={16} />}
              Save Changes
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// Thresholds Modal for Voltage Meter
interface ThresholdsModalProps {
  sensor: Sensor;
  onClose: () => void;
  onSave: (cutoff: number, reconnect: number) => void;
  loading: boolean;
}

function ThresholdsModal({ sensor, onClose, onSave, loading }: ThresholdsModalProps) {
  const [cutoff, setCutoff] = useState('11.0');
  const [reconnect, setReconnect] = useState('12.6');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSave(parseFloat(cutoff), parseFloat(reconnect));
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Battery Thresholds</h2>
          <button className="modal-close" onClick={onClose}><X size={20} /></button>
        </div>
        <form onSubmit={handleSubmit}>
          <div className="modal-body">
            <p className="form-hint" style={{marginBottom: '20px'}}>
              Configure thresholds for <strong>{sensor.name}</strong>.
              The relay turns off (cutoff) and back on (reconnect) based on battery voltage.
            </p>
            <div className="form-group">
              <label className="form-label">Cutoff Voltage (V)</label>
              <input
                type="number"
                step="0.1"
                min="10"
                max="14"
                className="form-input mono"
                value={cutoff}
                onChange={e => setCutoff(e.target.value)}
                disabled={loading}
              />
              <p className="form-hint">Relay turns OFF when battery drops below this</p>
            </div>
            <div className="form-group">
              <label className="form-label">Reconnect Voltage (V)</label>
              <input
                type="number"
                step="0.1"
                min="10"
                max="14"
                className="form-input mono"
                value={reconnect}
                onChange={e => setReconnect(e.target.value)}
                disabled={loading}
              />
              <p className="form-hint">Relay turns ON when battery rises above this</p>
            </div>
          </div>
          <div className="modal-footer">
            <button type="button" className="btn" onClick={onClose} disabled={loading}>Cancel</button>
            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? <Loader2 size={16} className="spinner" /> : <Battery size={16} />}
              Set Thresholds
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}


// Calibration Modal for Voltage Meter
interface CalibrateModalProps {
  sensor: Sensor;
  onClose: () => void;
  onSave: (targetVoltage: number) => void;
  loading: boolean;
}

function CalibrateModal({ sensor, onClose, onSave, loading }: CalibrateModalProps) {
  const [targetVoltage, setTargetVoltage] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const voltage = parseFloat(targetVoltage);
    if (!isNaN(voltage) && voltage > 0) {
      onSave(voltage);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Calibrate ADC</h2>
          <button className="modal-close" onClick={onClose}><X size={20} /></button>
        </div>
        <form onSubmit={handleSubmit}>
          <div className="modal-body">
            <p className="form-hint" style={{marginBottom: '20px'}}>
              Calibrate the voltage reading for <strong>{sensor.name}</strong>.
            </p>
            
            <div className="calibration-info">
              <div className="calibration-step">
                <span className="step-number">1</span>
                <span>Measure the actual battery voltage with a multimeter</span>
              </div>
              <div className="calibration-step">
                <span className="step-number">2</span>
                <span>Enter that voltage below</span>
              </div>
              <div className="calibration-step">
                <span className="step-number">3</span>
                <span>The ESP32 will auto-calibrate its ADC</span>
              </div>
            </div>

            <div className="current-reading">
              <span>Current displayed voltage:</span>
              <strong>{sensor.battery_volts?.toFixed(2) || '?'}V</strong>
            </div>

            <div className="form-group">
              <label className="form-label">Actual Voltage (from multimeter)</label>
              <input
                type="number"
                step="0.01"
                min="8"
                max="16"
                placeholder="e.g., 12.85"
                className="form-input mono"
                value={targetVoltage}
                onChange={e => setTargetVoltage(e.target.value)}
                disabled={loading}
                autoFocus
              />
              <p className="form-hint">Enter the exact voltage reading from your multimeter</p>
            </div>
          </div>
          <div className="modal-footer">
            <button type="button" className="btn" onClick={onClose} disabled={loading}>Cancel</button>
            <button type="submit" className="btn btn-primary" disabled={loading || !targetVoltage}>
              {loading ? <Loader2 size={16} className="spinner" /> : <Settings size={16} />}
              Calibrate
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}


// Last Data Modal - Shows CSV data in a nice table
interface LastDataModalProps {
  sensor: Sensor;
  data: string | null;
  onClose: () => void;
}

function LastDataModal({ sensor, data, onClose }: LastDataModalProps) {
  // Parse CSV into headers and rows
  const parseCSV = (csv: string | null): { headers: string[]; rows: string[][] } => {
    if (!csv) return { headers: [], rows: [] };
    
    const lines = csv.trim().split('\n');
    if (lines.length === 0) return { headers: [], rows: [] };
    
    const headers = lines[0].split(',').map(h => h.trim());
    const rows = lines.slice(1).map(line => line.split(',').map(cell => cell.trim()));
    
    return { headers, rows };
  };

  const { headers, rows } = parseCSV(data);

  // Format header names to be more readable
  const formatHeader = (header: string): string => {
    // Remove units in parentheses for display, keep them as tooltip
    return header
      .replace(/\s*\([^)]*\)/g, '')  // Remove parentheses content
      .replace(/:/g, '')              // Remove colons
      .trim();
  };

  // Format cell values nicely
  const formatValue = (value: string, header: string): string => {
    // Check for timestamp/date fields first (before number parsing)
    const headerLower = header.toLowerCase();
    if (headerLower.includes('timestamp') || headerLower.includes('time') || headerLower.includes('date')) {
      // Try to parse as date
      if (value.includes('T') || value.includes('-')) {
        try {
          const date = new Date(value);
          if (!isNaN(date.getTime())) {
            // Format nicely: "Jan 23, 2026 4:48:34 AM"
            return date.toLocaleString('en-US', {
              month: 'short',
              day: 'numeric',
              year: 'numeric',
              hour: 'numeric',
              minute: '2-digit',
              second: '2-digit',
              hour12: true
            });
          }
        } catch {
          return value;
        }
      }
      return value;
    }
    
    // Check if it's a number (but not a date-like string)
    if (!value.includes('-') && !value.includes('T')) {
      const num = parseFloat(value);
      if (!isNaN(num)) {
        // Temperature, voltage, pressure - show 1-2 decimals
        if (header.includes('Temp') || header.includes('Voltage') || header.includes('Pressure') || header.includes('Battery')) {
          return num.toFixed(1);
        }
        // Percentages and counts
        if (header.includes('%') || header.includes('Count') || header.includes('Cycle')) {
          return Math.round(num).toString();
        }
        // Boolean-like (0/1)
        if (value === '0' || value === '1') {
          if (header.includes('Load') || header.includes('Auto') || header.includes('On')) {
            return value === '1' ? '✓ Yes' : '✗ No';
          }
        }
        // Default number formatting
        if (Number.isInteger(num)) return num.toString();
        return num.toFixed(2);
      }
    }
    return value;
  };

  // Get unit from header
  const getUnit = (header: string): string => {
    const match = header.match(/\(([^)]+)\)/);
    return match ? match[1] : '';
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal modal-wide" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h2>📊 Last Sent Data</h2>
          <button className="modal-close" onClick={onClose}><X size={20} /></button>
        </div>
        <div className="modal-body">
          <div className="last-data-info">
            <span className="sensor-badge">{sensor.sensor_type.replace('_', ' ')}</span>
            <span className="sensor-name-label">{sensor.name}</span>
          </div>
          
          {headers.length === 0 ? (
            <div className="no-data">
              <Database size={32} strokeWidth={1} />
              <p>No data sent yet</p>
            </div>
          ) : (
            <div className="data-table-container">
              <table className="data-table">
                <thead>
                  <tr>
                    <th className="field-col">Field</th>
                    <th className="value-col">Value</th>
                    <th className="unit-col">Unit</th>
                  </tr>
                </thead>
                <tbody>
                  {headers.map((header, i) => (
                    <tr key={i}>
                      <td className="field-col">
                        <span className="field-name">{formatHeader(header)}</span>
                      </td>
                      <td className="value-col">
                        <span className="field-value">{rows[0] ? formatValue(rows[0][i], header) : '-'}</span>
                      </td>
                      <td className="unit-col">
                        <span className="field-unit">{getUnit(header)}</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
