import React, { useState, useEffect, useCallback } from 'react';
import useSocket from './hooks/useSocket';
import useApi from './hooks/useApi';
import { ENDPOINTS } from './utils/api';
import SystemStatusBar from './components/SystemStatusBar';
import ExperimentSelector from './components/ExperimentSelector';
import Dashboard from './components/Dashboard';

export default function App() {
  const socket = useSocket();
  const { data: experimentsData, refetch: refetchExperiments } = useApi(ENDPOINTS.experiments);
  const { data: healthData, refetch: refetchHealth } = useApi(ENDPOINTS.healthState);
  const { data: diseaseData, refetch: refetchDisease } = useApi(ENDPOINTS.diseaseClassification);

  const [activeExperimentId, setActiveExperimentId] = useState(1);
  const [alertLog, setAlertLog] = useState([]);
  const [simSpeed, setSimSpeed] = useState(1);
  const [simPaused, setSimPaused] = useState(false);
  // force child components to remount on experiment change
  const [refreshKey, setRefreshKey] = useState(0);

  // On mount, set experiment from API
  useEffect(() => {
    if (experimentsData?.active_experiment_id) {
      setActiveExperimentId(experimentsData.active_experiment_id);
    }
  }, [experimentsData]);

  // Track alerts from WebSocket
  useEffect(() => {
    if (socket.lastAlert) {
      setAlertLog((prev) => [socket.lastAlert, ...prev].slice(0, 50));
    }
  }, [socket.lastAlert]);

  const handleExperimentChange = useCallback((expId) => {
    setActiveExperimentId(expId);
    socket.emit('set_experiment', { experiment_id: expId });
    // Allow backend to switch, then refetch ALL data
    setTimeout(() => {
      refetchHealth();
      refetchDisease();
      refetchExperiments();
      setRefreshKey((k) => k + 1);
    }, 300);
  }, [socket, refetchHealth, refetchDisease, refetchExperiments]);

  const handleTestAlert = () => {
    socket.emit('request_alert_test');
  };

  const handleSpeedChange = (speed) => {
    setSimSpeed(speed);
    socket.emit('set_simulation_speed', { speed });
  };

  const handlePauseToggle = () => {
    setSimPaused(!simPaused);
    socket.emit('pause_simulation');
  };

  return (
    <div className="app">
      <SystemStatusBar
        connected={socket.connected}
        systemStatus={socket.systemStatus}
        onTestAlert={handleTestAlert}
      />
      <div className="app-header">
        <h1 className="app-title">Multimodal Health Monitoring</h1>
        <div className="app-controls">
          <ExperimentSelector
            experiments={experimentsData?.experiments || []}
            activeId={activeExperimentId}
            onChange={handleExperimentChange}
          />
          <div className="sim-controls">
            <label>Speed:
              <select value={simSpeed} onChange={(e) => handleSpeedChange(Number(e.target.value))}>
                <option value={0.5}>0.5x</option>
                <option value={1}>1x</option>
                <option value={2}>2x</option>
                <option value={5}>5x</option>
              </select>
            </label>
            <button className="btn" onClick={handlePauseToggle}>
              {simPaused ? '▶ Resume' : '⏸ Pause'}
            </button>
          </div>
        </div>
      </div>
      <Dashboard
        key={refreshKey}
        healthData={healthData}
        diseaseData={diseaseData}
        lastHealthUpdate={socket.lastHealthUpdate}
        alertLog={alertLog}
        socket={socket}
        onTestAlert={handleTestAlert}
      />
    </div>
  );
}
