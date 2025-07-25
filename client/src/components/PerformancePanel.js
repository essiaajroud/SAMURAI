// PerformancePanel.js - Shows system performance, analytics, and logs
// Provides graphs, historical stats, and system log display
import React, { useState, useEffect } from 'react';
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
  const [systemAlerts, setSystemAlerts] = useState([]);
  
  // Fonction pour générer des alertes système basées sur les données
  const generateSystemAlerts = () => {
    const alerts = [];
    const now = new Date();
    
    // Alerte de connexion backend
    alerts.push({
      id: 'backend-connection',
      timestamp: now,
      level: isConnected ? 'info' : 'error',
      message: `Backend ${isConnected ? 'connecté' : 'non connecté'}`
    });
    
    // Si le backend n'est pas connecté, ajouter une alerte pour indiquer que l'interface est en mode hors ligne
    if (!isConnected) {
      alerts.push({
        id: 'offline-mode',
        timestamp: now,
        level: 'info',
        message: 'Interface en mode hors ligne - Les fonctionnalités nécessitant le backend ne sont pas disponibles'
      });
      
      // Ne pas afficher d'autres alertes si le backend n'est pas connecté
      return alerts;
    }
    
    // Alertes basées sur les métriques système (seulement si le backend est connecté)
    if (systemMetrics) {
      // Alerte de température CPU
      if (systemMetrics.cpu_temp && systemMetrics.cpu_temp > 80) {
        alerts.push({
          id: 'cpu-temp',
          timestamp: now,
          level: systemMetrics.cpu_temp > 90 ? 'critical' : 'warning',
          message: `Température CPU anormale (${systemMetrics.cpu_temp}°C) - ${systemMetrics.cpu_temp > 90 ? 'ARRÊT IMMINENT' : 'Réduction de performance activée'}`
        });
      }
      
      // Alerte d'utilisation CPU
      if (systemMetrics.cpu_percent && systemMetrics.cpu_percent > 90) {
        alerts.push({
          id: 'cpu-usage',
          timestamp: now,
          level: 'warning',
          message: `Utilisation CPU élevée (${systemMetrics.cpu_percent}%) - Performance dégradée possible`
        });
      }
      
      // Alerte d'utilisation RAM
      if (systemMetrics.ram_percent && systemMetrics.ram_percent > 85) {
        alerts.push({
          id: 'ram-usage',
          timestamp: now,
          level: 'warning',
          message: `Mémoire RAM critique (${systemMetrics.ram_percent}%) - ${systemMetrics.ram_free_MB}MB disponible`
        });
      }
    }
    
    // Alertes basées sur les détections (seulement si le backend est connecté)
    if (detectionHistory && detectionHistory.length > 0) {
      // Prendre les 5 dernières détections
      const recentDetections = detectionHistory.slice(-5);
      
      recentDetections.forEach(detection => {
        if (!detection.class) return;
        
        // Alerte pour armes détectées
        if (detection.class.toLowerCase().includes('weapon') ||
            detection.class.toLowerCase().includes('gun') ||
            detection.class.toLowerCase().includes('rifle')) {
          
          // Vérifier si la zone est civile (simulation)
          const isInCivilianZone = Math.random() > 0.5; // Simulation
          
          if (isInCivilianZone) {
            alerts.push({
              id: `weapon-${detection.id || Date.now()}`,
              timestamp: detection.timestamp || now,
              level: 'critical',
              message: `Détection d&apos;arme en zone civile - Coordonnées: ${detection.coordinates || '48.8566, 2.3522'}`
            });
          }
        }
        
        // Alerte pour personnes en zone restreinte
        if (detection.class.toLowerCase().includes('person') ||
            detection.class.toLowerCase().includes('civilian')) {
          
          // Vérifier si la zone est militaire (simulation)
          const isInMilitaryZone = Math.random() > 0.7; // Simulation
          
          if (isInMilitaryZone) {
            alerts.push({
              id: `restricted-${detection.id || Date.now()}`,
              timestamp: detection.timestamp || now,
              level: 'critical',
              message: `Civil détecté en zone militaire restreinte - Alerte de sécurité niveau ${Math.floor(Math.random() * 3) + 1}`
            });
          }
        }
      });
    }
    
    // N'afficher les alertes de statut caméra que si le backend est connecté
    // Statut de la caméra basé sur l'état de détection plutôt que sur une simulation aléatoire
    if (modelMetrics && modelMetrics.fps && modelMetrics.fps > 0) {
      alerts.push({
        id: 'camera-status',
        timestamp: now,
        level: 'info',
        message: 'Caméra connectée - Flux vidéo actif'
      });
    } else {
      alerts.push({
        id: 'camera-status',
        timestamp: now,
        level: 'warning',
        message: 'Caméra non détectée ou flux vidéo inactif'
      });
    }
    
    return alerts;
  };
  
  // Mettre à jour les alertes lorsque les données changent
  useEffect(() => {
    setSystemAlerts(generateSystemAlerts());
  }, [isConnected, systemMetrics, detectionHistory]);

  // --- Chart Data and Options ---

  // Préparation des données pour les graphiques d'historique
  const prepareDetectionHistoryData = () => {
    // Regrouper les détections par timestamp (jour/heure)
    const groupedByTime = {};
    const last10Timestamps = [];
    
    // Si l'historique existe et contient des données
    if (detectionHistory && detectionHistory.length > 0) {
      // Prendre les 10 derniers timestamps uniques
      const uniqueTimestamps = [...new Set(detectionHistory.map(d => {
        // Formater le timestamp pour regrouper par heure
        const date = new Date(d.timestamp);
        return date.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
      }))];
      
      // Prendre les 10 derniers timestamps
      const recentTimestamps = uniqueTimestamps.slice(-10);
      
      // Compter les détections pour chaque timestamp
      recentTimestamps.forEach(timestamp => {
        const count = detectionHistory.filter(d => {
          const date = new Date(d.timestamp);
          return date.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}) === timestamp;
        }).length;
        
        groupedByTime[timestamp] = count;
        last10Timestamps.push(timestamp);
      });
    }
    
    return {
      labels: last10Timestamps,
      data: last10Timestamps.map(t => groupedByTime[t] || 0)
    };
  };
  
  const prepareClassHistoryData = () => {
    // Regrouper les détections par classe
    const classCounts = {};
    
    // Si l'historique existe et contient des données
    if (detectionHistory && detectionHistory.length > 0) {
      // Compter les occurrences de chaque classe
      detectionHistory.forEach(detection => {
        if (detection.class) {
          classCounts[detection.class] = (classCounts[detection.class] || 0) + 1;
        }
      });
    }
    
    // Convertir en format pour le graphique
    const labels = Object.keys(classCounts);
    const data = labels.map(label => classCounts[label]);
    
    return { labels, data };
  };
  
  // Données pour les graphiques d'historique
  const detectionHistoryData = prepareDetectionHistoryData();
  const classHistoryData = prepareClassHistoryData();
  
  // Configuration des graphiques d'historique
  const detectionHistoryChartData = {
    labels: detectionHistoryData.labels,
    datasets: [{
      label: 'Nombre de détections',
      data: detectionHistoryData.data,
      borderColor: 'rgb(75, 192, 192)',
      backgroundColor: 'rgba(75, 192, 192, 0.5)',
      tension: 0.3
    }]
  };
  
  const classHistoryChartData = {
    labels: classHistoryData.labels,
    datasets: [{
      label: 'Détections par classe',
      data: classHistoryData.data,
      backgroundColor: [
        'rgba(255, 99, 132, 0.5)',
        'rgba(54, 162, 235, 0.5)',
        'rgba(255, 206, 86, 0.5)',
        'rgba(75, 192, 192, 0.5)',
        'rgba(153, 102, 255, 0.5)',
        'rgba(255, 159, 64, 0.5)'
      ],
      borderColor: [
        'rgb(255, 99, 132)',
        'rgb(54, 162, 235)',
        'rgb(255, 206, 86)',
        'rgb(75, 192, 192)',
        'rgb(153, 102, 255)',
        'rgb(255, 159, 64)'
      ],
      borderWidth: 1
    }]
  };
  
  const historyChartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    scales: {
      y: {
        beginAtZero: true,
        ticks: {
          color: '#ccc'
        },
        grid: {
          color: '#444'
        }
      },
      x: {
        ticks: {
          color: '#ccc'
        },
        grid: {
          color: '#444'
        }
      }
    },
    plugins: {
      legend: {
        position: 'top',
        labels: {
          color: '#ccc'
        }
      },
      title: {
        display: true,
        color: '#fff'
      }
    }
  };

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
        data: systemMetricsHistory.map(m => m.cpu_percent),
        borderColor: 'rgb(255, 99, 132)',
        backgroundColor: 'rgba(255, 99, 132, 0.5)',
        yAxisID: 'y',
      },
      {
        label: 'RAM Usage (%)',
        data: systemMetricsHistory.map(m => m.ram_percent),
        borderColor: 'rgb(54, 162, 235)',
        backgroundColor: 'rgba(54, 162, 235, 0.5)',
        yAxisID: 'y',
      },
      {
        label: 'Disk Usage (%)',
        data: systemMetricsHistory.map(m => m.disk_percent),
        borderColor: 'rgb(255, 206, 86)',
        backgroundColor: 'rgba(255, 206, 86, 0.5)',
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
    <div className="performance-panel" style={{ height: '520px', overflow: 'auto', boxSizing: 'border-box' }}>
      <div className="panel-header">
          <h2>Performance & Analytics</h2>
        <div className="panel-tabs">
          <button className={selectedTab === 'model' ? 'active tab-button' : 'tab-button'} onClick={() => setSelectedTab('model')}>Model Performance</button>
          <button className={selectedTab === 'system' ? 'active tab-button' : 'tab-button'} onClick={() => setSelectedTab('system')}>System Performance</button>
          <button className={selectedTab === 'history' ? 'active tab-button' : 'tab-button'} onClick={() => setSelectedTab('history')}>History</button>
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
              <div className="metric-card">CPU Usage<br /><span>{formatMetric(systemMetrics.cpu_percent, 1)}%</span></div>
              <div className="metric-card">RAM Usage<br /><span>{formatMetric(systemMetrics.ram_percent, 1)}% ({systemMetrics.ram_used_MB} / {systemMetrics.ram_total_MB} MB)</span></div>
              <div className="metric-card">Disk Usage<br /><span>{formatMetric(systemMetrics.disk_percent, 1)}% ({systemMetrics.disk_used_GB} / {systemMetrics.disk_total_GB} GB)</span></div>
              <div className="metric-card">Network Sent<br /><span>{formatMetric(systemMetrics.net_sent_MB, 2)} MB</span></div>
              <div className="metric-card">Network Received<br /><span>{formatMetric(systemMetrics.net_recv_MB, 2)} MB</span></div>
              <div className="metric-card">Processes<br /><span>{systemMetrics.running_processes}</span></div>
            </div>
            <div className="metrics-row" style={{ height: '200px' }}>
              <Line options={systemChartOptions} data={systemChartData} />
            </div>
          </div>
        )}
        {selectedTab === 'history' && (
          <div className="history-analytics-section">
            {/* Historique des détections, stats globales, etc. */}
            <div className="metrics-row">
              <div className="metric-card">Total Detections<br /><span>{detectionHistory.length}</span></div>
              <div className="metric-card">Classes Uniques<br /><span>{classHistoryData.labels.length}</span></div>
              <div className="metric-card">Période<br /><span>Dernière heure</span></div>
            </div>
            
            {/* Graphiques d'historique */}
            <div className="metrics-row" style={{ height: '200px' }}>
              <div className="chart-container">
                <Line
                  data={detectionHistoryChartData}
                  options={{
                    ...historyChartOptions,
                    plugins: {
                      ...historyChartOptions.plugins,
                      title: {
                        ...historyChartOptions.plugins.title,
                        text: 'Historique des détections'
                      }
                    }
                  }}
                />
              </div>
              <div className="chart-container">
                <Bar
                  data={classHistoryChartData}
                  options={{
                    ...historyChartOptions,
                    plugins: {
                      ...historyChartOptions.plugins,
                      title: {
                        ...historyChartOptions.plugins.title,
                        text: 'Détections par classe'
                      }
                    }
                  }}
                />
              </div>
            </div>
          </div>
        )}
        {selectedTab === 'logs' && (
          <div className="system-logs-panel">
            <ul className="logs-list">
              {/* Alertes système générées dynamiquement */}
              {systemAlerts.map((alert) => (
                <li key={alert.id} className={`log-entry ${alert.level}`}>
                  <span className="log-timestamp">{alert.timestamp.toLocaleString()}</span>
                  <span className={`log-level ${alert.level}`}>[{alert.level.toUpperCase()}]</span>
                  <span className="log-message">{alert.message}</span>
                </li>
              ))}
              
              {/* Logs dynamiques de l'application */}
              {logs && logs.length > 0 && logs.map((log, idx) => (
                <li key={`app-log-${idx}`} className={`log-entry ${log.level?.toLowerCase() || 'info'}`}>
                  <span className="log-timestamp">{log.timestamp ? new Date(log.timestamp).toLocaleString() : ''}</span>
                  <span className={`log-level ${log.level?.toLowerCase() || 'info'}`}>[{log.level || 'INFO'}]</span>
                  <span className="log-message">{log.message || String(log)}</span>
                </li>
              ))}
              
              {/* Message si aucun log n'est disponible */}
              {systemAlerts.length === 0 && (!logs || logs.length === 0) && (
                <li className="log-entry info">
                  <span className="log-timestamp">{new Date().toLocaleString()}</span>
                  <span className="log-level info">[INFO]</span>
                  <span className="log-message">Aucun log système disponible</span>
                </li>
              )}
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