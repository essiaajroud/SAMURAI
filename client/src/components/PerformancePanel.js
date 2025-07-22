// PerformancePanel.js - Shows system performance, analytics, and logs
// Provides graphs, historical stats, and system log display
import React, { useState } from 'react';
import PropTypes from 'prop-types';
import { Line, Bar, Doughnut } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';
import './PerformancePanel.css';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend
);

// Helper to format numbers
const formatMetric = (value, decimals = 3) => {
  if (value === null || value === undefined || isNaN(value)) {
    return '--';
  }
  return value.toFixed(decimals);
};

// Squelette avancé pour cockpit de monitoring modèle + système
const PerformancePanel = ({
  modelMetrics = {},
  modelMetricsHistory = [],
  systemMetrics = {},
  systemMetricsHistory = [],
  logs = [],
  detectionHistory = [],
  isConnected = false
}) => {
  const [selectedTab, setSelectedTab] = useState('model'); // Default to model tab

  // --- Chart Data and Options ---

  const prf1ChartData = {
    labels: ['Metrics'],
    datasets: [
      {
        label: 'Precision (%)',
        data: [modelMetrics.precision],
        backgroundColor: 'rgba(255, 99, 132, 0.5)',
      },
      {
        label: 'Recall (%)',
        data: [modelMetrics.recall],
        backgroundColor: 'rgba(54, 162, 235, 0.5)',
      },
      {
        label: 'F1-Score',
        data: [modelMetrics.f1Score ? modelMetrics.f1Score * 100 : 0], // Scale F1 to %
        backgroundColor: 'rgba(75, 192, 192, 0.5)',
      },
    ],
  };

  const detectionRateChartData = {
    labels: ['Detection Rate', ''],
    datasets: [{
      data: [modelMetrics.detectionRate, 100 - modelMetrics.detectionRate],
      backgroundColor: ['rgba(75, 192, 192, 0.8)', 'rgba(200, 200, 200, 0.2)'],
      circumference: 180,
      rotation: 270,
    }],
  };

  const idSwitchChartData = {
    labels: modelMetricsHistory.map(m => m.timestamp),
    datasets: [{
      label: 'ID Switches',
      data: modelMetricsHistory.map(m => m.idSwitchCount),
      borderColor: 'rgb(255, 159, 64)',
      backgroundColor: 'rgba(255, 159, 64, 0.5)',
    }],
  };

  const systemChartData = {
    labels: systemMetricsHistory.map(m => m.timestamp),
    datasets: [
      {
        label: 'CPU Usage (%)',
        data: systemMetricsHistory.map(m => m.cpu),
        borderColor: 'rgb(255, 99, 132)',
        backgroundColor: 'rgba(255, 99, 132, 0.5)',
        yAxisID: 'y',
      },
      {
        label: 'RAM Usage (%)',
        data: systemMetricsHistory.map(m => m.ram),
        borderColor: 'rgb(54, 162, 235)',
        backgroundColor: 'rgba(54, 162, 235, 0.5)',
        yAxisID: 'y',
      },
      {
        label: 'GPU Usage (%)',
        data: systemMetricsHistory.map(m => m.gpu),
        borderColor: 'rgb(75, 192, 192)',
        backgroundColor: 'rgba(75, 192, 192, 0.5)',
        yAxisID: 'y',
      },
    ],
  };

  const systemChartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    scales: {
      y: {
        type: 'linear',
        display: true,
        position: 'left',
        min: 0,
        max: 100,
        ticks: {
          color: '#ccc',
        },
        grid: {
          color: '#444',
        }
      },
    },
    plugins: {
      legend: {
        position: 'top',
        labels: {
          color: '#ccc',
        }
      },
      title: {
        display: true,
        text: 'Real-time System Performance',
        color: '#fff',
      },
    },
  };

  return (
    <div className="performance-panel">
      <div className="panel-header">
          <h2>Performance & Analytics</h2>
        <div className="panel-tabs">
          <button className={selectedTab === 'model' ? 'active tab-button' : 'tab-button'} onClick={() => setSelectedTab('model')}>Performance Modèle</button>
          <button className={selectedTab === 'system' ? 'active tab-button' : 'tab-button'} onClick={() => setSelectedTab('system')}>Performance Système</button>
          <button className={selectedTab === 'history' ? 'active tab-button' : 'tab-button'} onClick={() => setSelectedTab('history')}>Historique</button>
          <button className={selectedTab === 'logs' ? 'active tab-button' : 'tab-button'} onClick={() => setSelectedTab('logs')}>Logs</button>
        </div>
      </div>
      <div className="panel-content">
        {selectedTab === 'model' && (
          <div className="model-metrics-section">
            {/* FPS, Inference Time, Detection Rate, Precision, Recall, F1, ID Switch, MOTA, MOTP, Objects by class */}
            <div className="metrics-row">
              <div className="metric-card">FPS<br /><span>{formatMetric(modelMetrics.fps, 1)}</span></div>
              <div className="metric-card">Inference Time<br /><span>{formatMetric(modelMetrics.inferenceTime)} ms</span></div>
              <div className="metric-card">Object Count<br /><span>{modelMetrics.objectCount ?? '--'}</span></div>
              <div className="metric-card">Detection Rate<br /><span>{formatMetric(modelMetrics.detectionRate)}%</span></div>
              <div className="metric-card">Precision<br /><span>{formatMetric(modelMetrics.precision)}%</span></div>
              <div className="metric-card">Recall<br /><span>{formatMetric(modelMetrics.recall)}%</span></div>
              <div className="metric-card">F1-Score<br /><span>{formatMetric(modelMetrics.f1Score)}</span></div>
            </div>
            <div className="metrics-row">
              <div className="metric-card">ID Switch<br /><span>{modelMetrics.idSwitchCount ?? '--'}</span></div>
              <div className="metric-card">MOTA<br /><span>{formatMetric(modelMetrics.mota)}</span></div>
              <div className="metric-card">MOTP<br /><span>{formatMetric(modelMetrics.motp)}</span></div>
            </div>
            <div className="metrics-row">
              <div className="metric-card metric-card-wide">
                <strong>Objets détectés par classe</strong>
                <ul>
                  {modelMetrics.objectsByClass ? Object.entries(modelMetrics.objectsByClass).map(([cls, count]) => (
                    <li key={cls}>{cls}: {count}</li>
                  )) : <li>--</li>}
                </ul>
              </div>
            </div>
            <div className="metrics-row" style={{ height: '180px' }}>
              <div className="chart-container">
                <Bar data={prf1ChartData} options={{ maintainAspectRatio: false, indexAxis: 'y', plugins: { title: { display: true, text: 'Precision / Recall / F1', color: '#fff' }, legend: { labels: { color: '#ccc' } } }, scales: { x: { min: 80, max: 100, ticks: { color: '#ccc' } }, y: { ticks: { color: '#ccc' } } } }} />
              </div>
              <div className="chart-container">
                <Doughnut data={detectionRateChartData} options={{ maintainAspectRatio: false, plugins: { title: { display: true, text: 'Detection Rate', color: '#fff' }, legend: { display: false } } }} />
              </div>
              <div className="chart-container">
                <Line data={idSwitchChartData} options={{ maintainAspectRatio: false, plugins: { title: { display: true, text: 'ID Switches', color: '#fff' }, legend: { display: false } }, scales: { y: { beginAtZero: true, ticks: { color: '#ccc' } }, x: { ticks: { color: '#ccc' } } } }} />
              </div>
            </div>
              </div>
            )}
        {selectedTab === 'system' && (
          <div className="system-metrics-section">
            {/* CPU, GPU, RAM, Températures, Réseau */}
            <div className="metrics-row">
              <div className="metric-card">CPU Usage<br /><span>{formatMetric(systemMetrics.cpu, 1)}%</span></div>
              <div className="metric-card">GPU Usage<br /><span>{formatMetric(systemMetrics.gpu, 1)}%</span></div>
              <div className="metric-card">RAM Used<br /><span>{formatMetric(systemMetrics.ram, 1)}%</span></div>
              <div className="metric-card">Temp CPU<br /><span>{formatMetric(systemMetrics.tempCpu, 1)}°C</span></div>
              <div className="metric-card">Temp GPU<br /><span>{formatMetric(systemMetrics.tempGpu, 1)}°C</span></div>
              </div>
            <div className="metrics-row">
              <div className="metric-card">Net In<br /><span>{formatMetric(systemMetrics.netIn)} Mbps</span></div>
              <div className="metric-card">Net Out<br /><span>{formatMetric(systemMetrics.netOut)} Mbps</span></div>
              </div>
            <div className="metrics-row" style={{ height: '200px' }}>
              <Line options={systemChartOptions} data={systemChartData} />
            </div>
          </div>
        )}
        {selectedTab === 'history' && (
          <div className="history-analytics-section">
            {/* Historique des détections, stats globales, etc. */}
            <div className="metric-card">Total Detections<br /><span>{detectionHistory.length}</span></div>
            {/* Placeholders pour graphes historiques */}
            <div className="metric-graph-placeholder">[Courbe historique détections]</div>
            <div className="metric-graph-placeholder">[Courbe historique classes]</div>
          </div>
        )}
        {selectedTab === 'logs' && (
          <div className="system-logs-panel">
            <ul className="logs-list">
              <li className={`log-entry ${isConnected ? 'info' : 'error'}`}>
                <span className={`log-timestamp`}>{new Date().toLocaleString()}</span>
                <span className={`log-level ${isConnected ? 'info' : 'error'}`}>[{isConnected ? 'INFO' : 'ERROR'}]</span>
                <span className="log-message">
                  Backend {isConnected ? 'connected' : 'not connected'}
                </span>
              </li>
              {logs && logs.length > 0 && logs.map((log, idx) => (
                <li key={idx} className={`log-entry ${log.level?.toLowerCase() || 'info'}`}>
                  <span className="log-timestamp">{log.timestamp ? new Date(log.timestamp).toLocaleString() : ''}</span>
                  <span className={`log-level ${log.level?.toLowerCase() || 'info'}`}>[{log.level || 'INFO'}]</span>
                  <span className="log-message">{log.message || String(log)}</span>
                  </li>
                ))}
            </ul>
          </div>
        )}
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