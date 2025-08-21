// Performance monitoring and visualization component
import React, { useState, useEffect, useMemo } from 'react';
import PropTypes from 'prop-types';
import axios from 'axios';
import { Line, Bar } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';
import './PerformancePanel.css';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, BarElement, Title, Tooltip, Legend);

// Base chart configuration
const baseChartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  scales: {
    y: { beginAtZero: true, ticks: { color: '#ccc' }, grid: { color: '#444' } },
    x: { ticks: { color: '#ccc' }, grid: { color: '#444' } }
  },
  plugins: {
    legend: { position: 'top', labels: { color: '#ccc' } },
    title: { display: true, color: '#fff' }
  }
};

// Utility functions
const formatMetric = (value, decimals = 1) => {
  if (value == null || isNaN(value)) return '--';
  return value.toFixed(decimals);
};

// Main component
const PerformancePanel = ({
  modelMetrics = {}, modelMetricsHistory = [], systemMetrics = {},
  systemMetricsHistory = [], logs = [], detectionHistory = [], isConnected = false, isDetectionStarted = false, sourceType = 'network'
}) => {
  const [selectedTab, setSelectedTab] = useState('model');
  const [realtimeAlerts, setRealtimeAlerts] = useState([]);
  const [systemAlerts, setSystemAlerts] = useState([]);

  // --- Data Processing with useMemo ---
  const processedMetrics = useMemo(() => {
    const knownClasses = ['person', 'soldier', 'weapon', 'military_vehicles', 'civilian_vehicles', 'military_aircraft', 'civilian_aircraft'];
    
    // Process detection history data
    const timeLabels = [...new Set(detectionHistory.map(d => 
      new Date(d.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    ))].slice(-10);

    // Group detections by class and time
    const groupedDetections = {};
    timeLabels.forEach(t => { groupedDetections[t] = {}; });
    detectionHistory.forEach(d => {
      const t = new Date(d.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      if (groupedDetections[t]) {
        const cls = d.label || 'unknown';
        groupedDetections[t][cls] = (groupedDetections[t][cls] || 0) + 1;
      }
    });

    return {
      timeLabels,
      classData: {
        labels: timeLabels,
        datasets: knownClasses.map((cls, idx) => ({
          label: cls,
          data: timeLabels.map(t => groupedDetections[t]?.[cls] || 0),
          backgroundColor: `hsl(${(idx * 360) / knownClasses.length}, 70%, 50%)`,
          maxBarThickness: 75
        }))
      },
      totalData: {
        labels: timeLabels,
        datasets: [{
          label: 'Total Detections',
          data: timeLabels.map(t => 
            Object.values(groupedDetections[t] || {}).reduce((sum, val) => sum + val, 0)
          ),
          borderColor: 'rgb(54, 162, 235)',
          backgroundColor: 'rgba(54, 162, 235, 0.3)',
          tension: 0.3
        }]
      }
    };
  }, [detectionHistory]);

  // --- Logique pour les alertes ---
  useEffect(() => {
    let interval = null;
    if (isConnected && selectedTab === 'logs') {
      const fetchAlerts = async () => {
        try {
          const res = await axios.get('/api/alerts');
          setRealtimeAlerts(res.data.alerts || []);
        } catch {
          setRealtimeAlerts([]);
        }
      };
      fetchAlerts();
      interval = setInterval(fetchAlerts, 5000);
    }
    return () => interval && clearInterval(interval);
  }, [isConnected, selectedTab]);

  useEffect(() => {
    const alerts = [];
    alerts.push({ id: 'backend', level: isConnected ? 'info' : 'error', message: `Backend ${isConnected ? 'connected' : 'not connected'}` });
    if(isConnected) {
        if (modelMetrics.fps === 0 && modelMetrics.inferenceTime > 0) {
            alerts.push({ id: 'camera', level: 'warning', message: 'Camera connected but stream seems frozen (0 FPS)' });
        }
        if (systemMetrics.cpu_percent > 90) {
            alerts.push({ id: 'cpu', level: 'warning', message: `High CPU usage (${systemMetrics.cpu_percent}%)` });
        }
        if (systemMetrics.ram_percent > 85) {
            alerts.push({ id: 'ram', level: 'warning', message: `Critical RAM usage (${systemMetrics.ram_percent}%)` });
        }
        if (modelMetrics.gpuUsage > 90) { // Déclenche dès 10%
        alerts.push({ id: 'gpu-usage', level: 'warning', message: `High GPU usage (${formatMetric(modelMetrics.gpuUsage)}%)` });
      }
        if (systemMetrics.battery_percent != null && systemMetrics.battery_percent < 20 && !systemMetrics.battery_plugged) {
            alerts.push({ id: 'battery', level: 'warning', message: `Low battery (${systemMetrics.battery_percent}%)` });
        }
        if (sourceType === 'network') {
           const isCameraActive = isDetectionStarted && modelMetrics.fps > 0;

        // Logique spécifique à la CAMÉRA RÉSEAU
        alerts.push({
        id: 'camera-status',
        level: isCameraActive ? 'info' : 'error',
        message: `Camera ${isCameraActive ? 'connected' : 'not connected'}`
      });
      } 
    }
    setSystemAlerts(alerts);
  }, [isConnected, systemMetrics, modelMetrics, isDetectionStarted, sourceType]);

  // --- RENDU DES DONNÉES DE PERFORMANCE ---
  const renderModelPerformance = () => (
    <div className="model-metrics-section">
      <div className="metrics-row">
        <div className="metric-card">FPS<br /><span>{formatMetric(modelMetrics.fps)}</span></div>
        <div className="metric-card">Inference Time<br /><span>{formatMetric(modelMetrics.inferenceTime, 0)} ms</span></div>
        <div className="metric-card">Object Count<br /><span>{modelMetrics.objectCount ?? '--'}</span></div>
        <div className="metric-card">Total Tracks<br /><span>{modelMetrics.totalTracks ?? '--'}</span></div>
        <div className="metric-card">Active Trajectories<br /><span>{modelMetrics.active_trajectories ?? '--'}</span></div>
      </div>
      <div className="metrics-row">
        <div className="metric-card metric-card-wide">
          <strong>Objects detected by class</strong>
          <ul>
            {modelMetrics.objectsByClass && Object.keys(modelMetrics.objectsByClass).length > 0
              ? Object.entries(modelMetrics.objectsByClass).map(([cls, count]) => <li key={cls}>{cls}: {count}</li>)
              : <li>--</li>}
          </ul>
        </div>
      </div>
       <div className="metrics-row">
          <div className="metric-card">Total Detections<br /><span>{detectionHistory.length}</span></div>
          <div className="metric-card">Unique Classes<br /><span>{processedMetrics.classData.datasets.filter(ds => ds.data.some(d => d > 0)).length}</span></div>
          <div className="metric-card">Time Range<br /><span>Last hour</span></div>
        </div>
      <div className="metrics-row" style={{ height: '200px' }}>
        <div className="chart-container">
          <Line
            data={processedMetrics.totalData}
            options={{
              ...baseChartOptions,
              plugins: {
                ...baseChartOptions.plugins,
                title: { ...baseChartOptions.plugins.title, text: 'Detection history' }
              }
            }}
          />
        </div>
        <div className="chart-container">
          <Bar
            data={processedMetrics.classData}
            options={{
              ...baseChartOptions,
              plugins: {
                ...baseChartOptions.plugins,
                title: { ...baseChartOptions.plugins.title, text: 'Detections by class' }
              },
              scales: {
                ...baseChartOptions.scales,
                x: { ...baseChartOptions.scales.x, stacked: true },
                y: { ...baseChartOptions.scales.y, stacked: true }
              }
            }}
          />
        </div>
      </div>
    </div>
  );

  const renderSystemPerformance = () => (
    <div className="system-metrics-section">
      <div className="metrics-row">
        <div className="metric-card">CPU Usage<br /><span>{formatMetric(modelMetrics.fps > 0 ? modelMetrics.cpuUsage : systemMetrics.cpu_percent)}%</span></div>
        <div className="metric-card">GPU Usage<br /><span>{formatMetric(modelMetrics.gpuUsage)}%</span></div>
        <div className="metric-card">GPU Memory<br /><span>{formatMetric(modelMetrics.gpuMemoryUsage)}%</span></div>
        <div className="metric-card">RAM Usage<br /><span>{formatMetric(systemMetrics.ram_percent)}% ({formatMetric(systemMetrics.ram_used_MB, 0)} / {formatMetric(systemMetrics.ram_total_MB, 0)} MB)</span></div>
        <div className="metric-card">Disk Usage<br /><span>{formatMetric(systemMetrics.disk_percent)}% ({formatMetric(systemMetrics.disk_used_GB)} / {formatMetric(systemMetrics.disk_total_GB)} GB)</span></div>
        <div className="metric-card">Network Sent<br /><span>{formatMetric(systemMetrics.net_sent_MB, 2)} MB</span></div>
        <div className="metric-card">Network Received<br /><span>{formatMetric(systemMetrics.net_recv_MB, 2)} MB</span></div>
        <div className="metric-card">Processes<br /><span>{systemMetrics.running_processes ?? '--'}</span></div>
        <div className="metric-card">Battery<br /><span>{systemMetrics.battery_percent != null ? `${formatMetric(systemMetrics.battery_percent)}%` : '--'} {systemMetrics.battery_plugged ? '(Charging)' : ''}</span></div>
      </div>
      <div className="metrics-row" style={{ height: '200px' }}>
        <Line 
          options={{...baseChartOptions, plugins: {...baseChartOptions.plugins, title: {...baseChartOptions.plugins.title, text: 'System Performance History'}}}}
          data={{
            labels: systemMetricsHistory.map(m => m.timestamp),
            datasets: [
              { label: 'CPU (%)', data: modelMetricsHistory.map(m => m.cpuUsage), borderColor: 'rgb(255, 99, 132)', backgroundColor: 'rgba(255, 99, 132, 0.5)', tension: 0.3 },
              { label: 'GPU (%)', data: modelMetricsHistory.map(m => m.gpuUsage), borderColor: 'rgb(75, 192, 192)', backgroundColor: 'rgba(75, 192, 192, 0.5)', tension: 0.3 },
              { label: 'RAM (%)', data: systemMetricsHistory.map(m => m.ram_percent), borderColor: 'rgb(54, 162, 235)', backgroundColor: 'rgba(54, 162, 235, 0.5)', tension: 0.3 }
            ]
          }} 
        />
      </div>
    </div>
  );

  const renderLogs = () => (
    <div className="system-logs-panel">
      <ul className="logs-list">
        {realtimeAlerts.map((alert, idx) => (
          <li key={`realtime-${idx}`} className={`log-entry`} style={{ borderLeft: `6px solid ${alert.color || '#ff4d4d'}` }}>
            <span className="log-timestamp">{new Date(alert.timestamp).toLocaleString()}</span>
            <span className={`log-level`} style={{ color: alert.color || '#ff4d4d', fontWeight: 'bold' }}>[{alert.type?.toUpperCase() || 'DANGER'}]</span>
            <span className="log-message">{alert.message}</span>
          </li>
        ))}
        {systemAlerts.map((alert) => (
          <li key={alert.id} className={`log-entry ${alert.level}`}>
            <span className="log-timestamp">{new Date().toLocaleString()}</span>
            <span className={`log-level ${alert.level}`}>[{alert.level.toUpperCase()}]</span>
            <span className="log-message">{alert.message}</span>
          </li>
        ))}
        {logs.length > 0 && realtimeAlerts.length === 0 && systemAlerts.length === 0 && logs.map((log, idx) => (
          <li key={`app-log-${idx}`}><span>{log}</span></li>
        ))}
      </ul>
    </div>
  );

  return (
    <div className="performance-panel">
      <div className="panel-header">
        <h2>Performance & Analytics</h2>
        <div className="panel-tabs">
          <button className={`tab-button ${selectedTab === 'model' ? 'active' : ''}`} onClick={() => setSelectedTab('model')}>Model Performance</button>
          <button className={`tab-button ${selectedTab === 'system' ? 'active' : ''}`} onClick={() => setSelectedTab('system')}>System Performance</button>
          <button className={`tab-button ${selectedTab === 'logs' ? 'active' : ''}`} onClick={() => setSelectedTab('logs')}>Logs</button>
        </div>
      </div>
      <div className="panel-content">
        {selectedTab === 'model' && renderModelPerformance()}
        {selectedTab === 'system' && renderSystemPerformance()}
        {selectedTab === 'logs' && renderLogs()}
      </div>
    </div>
  );
};

// --- VALIDATION DES PROPS (POUR CORRIGER LES AVERTISSEMENTS) ---
PerformancePanel.propTypes = {
  modelMetrics: PropTypes.object,
  modelMetricsHistory: PropTypes.array,
  systemMetrics: PropTypes.object,
  systemMetricsHistory: PropTypes.array,
  logs: PropTypes.array,
  detectionHistory: PropTypes.array,
  isConnected: PropTypes.bool,
  isDetectionStarted: PropTypes.bool,
  sourceType: PropTypes.string
};

export default PerformancePanel;