// PerformancePanel.js (VERSION FINALE AVEC CORRECTION DE LA TAILLE DES BARRES)

import React, { useState, useEffect, useMemo } from 'react';
import axios from 'axios';
import PropTypes from 'prop-types';
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

// --- Fonctions Utilitaires ---

const formatMetric = (value, decimals = 1) => {
  if (value == null || isNaN(value)) return '--';
  return value.toFixed(decimals);
};

const baseChartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  scales: {
    y: { 
      beginAtZero: true, 
      ticks: { color: '#ccc' }, 
      grid: { color: '#444' } 
    },
    x: { 
      ticks: { color: '#ccc' }, 
      grid: { color: '#444' } 
    }
  },
  plugins: {
    legend: { 
      position: 'top', 
      labels: { color: '#ccc' } 
    },
    title: { 
      display: true, 
      color: '#fff' 
    }
  }
};

// --- Composant Principal ---

const PerformancePanel = ({
  modelMetrics = {},
  modelMetricsHistory = [],
  systemMetrics = {},
  systemMetricsHistory = [],
  logs = [],
  detectionHistory = [],
  isConnected = false
}) => {
  const [selectedTab, setSelectedTab] = useState('model');
  const [realtimeAlerts, setRealtimeAlerts] = useState([]);

  // Logique pour les alertes
  useEffect(() => {
    let interval = null;
    if (selectedTab === 'logs') {
      const fetchAlerts = () => {
        axios.get('/api/alerts')
          .then(res => setRealtimeAlerts(res.data.alerts || []))
          .catch(() => setRealtimeAlerts([]));
      };
      fetchAlerts();
      interval = setInterval(fetchAlerts, 5000);
    }
    return () => clearInterval(interval);
  }, [selectedTab]);

  // --- PRÉPARATION DES DONNÉES POUR LES GRAPHIQUES ---

  const classHistoryData = useMemo(() => {
    const knownClasses = ['person', 'soldier', 'weapon', 'military_vehicles', 'civilian_vehicles', 'military_aircraft', 'civilian_aircraft'];
    const grouped = {};
    if (detectionHistory?.length) {
      detectionHistory.forEach(d => {
        const t = new Date(d.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        const cls = d.label || 'unknown';
        if (!grouped[t]) grouped[t] = {};
        grouped[t][cls] = (grouped[t][cls] || 0) + 1;
      });
    }
    const labels = [...new Set(detectionHistory.map(d => new Date(d.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })))].slice(-10);
    const datasets = knownClasses.map((cls, idx) => ({
      label: cls,
      data: labels.map(t => grouped[t]?.[cls] || 0),
      backgroundColor: `hsl(${(idx * 360) / knownClasses.length}, 70%, 50%)`,
      // --- AJOUT DE L'OPTION POUR LA TAILLE DES BARRES ---
      maxBarThickness: 50// Les barres ne dépasseront jamais 75 pixels de large
    }));
    return { labels, datasets };
  }, [detectionHistory]);

  const detectionHistoryData = useMemo(() => {
    const groupedByTime = {};
    if (detectionHistory?.length) {
      detectionHistory.forEach(d => {
        const timeLabel = new Date(d.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        groupedByTime[timeLabel] = (groupedByTime[timeLabel] || 0) + 1;
      });
    }
    const labels = Object.keys(groupedByTime).slice(-10);
    const data = labels.map(label => groupedByTime[label]);
    return { labels, data };
  }, [detectionHistory]);


  // --- JSX POUR LES ONGLETS ---

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
          <strong>Objets détectés par classe</strong>
          <ul>
            {modelMetrics.objectsByClass && Object.keys(modelMetrics.objectsByClass).length > 0
              ? Object.entries(modelMetrics.objectsByClass).map(([cls, count]) => <li key={cls}>{cls}: {count}</li>)
              : <li>--</li>}
          </ul>
        </div>
      </div>
       <div className="metrics-row">
          <div className="metric-card">Total Detections<br /><span>{detectionHistory.length}</span></div>
          <div className="metric-card">Classes Uniques<br /><span>{classHistoryData.datasets.filter(ds => ds.data.some(d => d > 0)).length}</span></div>
          <div className="metric-card">Période<br /><span>Dernière heure</span></div>
        </div>
      <div className="metrics-row" style={{ height: '200px' }}>
        <div className="chart-container">
          <Line
            data={{
              labels: detectionHistoryData.labels,
              datasets: [{
                label: 'Total Detections',
                data: detectionHistoryData.data,
                borderColor: 'rgb(54, 162, 235)',
                backgroundColor: 'rgba(54, 162, 235, 0.3)',
                tension: 0.3
              }]
            }}
            options={{ ...baseChartOptions, plugins: { ...baseChartOptions.plugins, title: { ...baseChartOptions.plugins.title, text: 'Historique des détections' } } }}
          />
        </div>
        <div className="chart-container">
          <Bar
            data={classHistoryData}
            options={{ ...baseChartOptions, plugins: { ...baseChartOptions.plugins, title: { ...baseChartOptions.plugins.title, text: 'Détections par classe' } }, scales: { ...baseChartOptions.scales, x: { ...baseChartOptions.scales.x, stacked: true }, y: { ...baseChartOptions.scales.y, stacked: true } } }}
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
          <li key={`realtime-${idx}`} className={`log-entry`} style={{ borderLeft: `6px solid ${alert.color || '#888'}` }}>
            <span className="log-timestamp">{alert.timestamp ? new Date(alert.timestamp).toLocaleString() : ''}</span>
            <span className={`log-level`} style={{ color: alert.color || '#888', fontWeight: 'bold' }}>[{alert.type?.toUpperCase() || 'ALERT'}]</span>
            <span className="log-message">{alert.message}</span>
          </li>
        ))}
        {logs.map((log, idx) => (
          <li key={`app-log-${idx}`} className={`log-entry`}>
            <span className="log-timestamp">{log.timestamp ? new Date(log.timestamp).toLocaleString() : ''}</span>
            <span className={`log-level`}>[{log.level || 'INFO'}]</span>
            <span className="log-message">{log.message || String(log)}</span>
          </li>
        ))}
        {logs.length === 0 && realtimeAlerts.length === 0 && <li className="log-entry">No logs available.</li>}
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

PerformancePanel.propTypes = {
  modelMetrics: PropTypes.object,
  modelMetricsHistory: PropTypes.array,
  systemMetrics: PropTypes.object,
  systemMetricsHistory: PropTypes.array,
  logs: PropTypes.array,
  detectionHistory: PropTypes.array,
  isConnected: PropTypes.bool
};

export default PerformancePanel;