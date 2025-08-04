// PerformancePanel.js - Shows system performance, analytics, and logs
// Provides graphs, historical stats, and system log display
import React, { useState, useEffect } from 'react';
import PropTypes from 'prop-types';
import { Line, Bar } from 'react-chartjs-2';
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
    return '0';
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
  
  // Nouvelle version : courbe multi-classes par timestamp
  const prepareClassHistoryData = () => {
    // Récupérer la liste des classes connues (mêmes que MapDemo)
    const knownClasses = [
      'person', 'soldier', 'weapon', 'military_vehicles', 'civilian_vehicles', 'military_aircraft', 'civilian_aircraft'
    ];
    // Grouper les détections par timestamp (arrondi à la minute)
    const timeStep = 60 * 1000; // 1 min
    const grouped = {};
    if (detectionHistory && detectionHistory.length > 0) {
      detectionHistory.forEach(d => {
        const t = d.timestamp ? Math.floor(Number(d.timestamp) / timeStep) * timeStep : 0;
        const cls = d.label || d.class || 'unknown';
        if (!grouped[t]) grouped[t] = {};
        grouped[t][cls] = (grouped[t][cls] || 0) + 1;
      });
    }
    // Générer les labels temporels (X)
    const allTimestamps = Object.keys(grouped).map(Number).sort((a, b) => a - b);
    // Générer les datasets par classe
    const datasets = knownClasses.map((cls, idx) => ({
      label: cls,
      data: allTimestamps.map(t => grouped[t]?.[cls] || 0),
      borderColor: `hsl(${(idx * 360) / knownClasses.length}, 70%, 50%)`,
      backgroundColor: `hsl(${(idx * 360) / knownClasses.length}, 70%, 80%)`,
      tension: 0.3
    }));
    // Labels X en format lisible
    const labels = allTimestamps.map(t => {
      const d = new Date(t);
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    });
    return { labels, datasets };
  };
  
  // Données pour les graphiques d'historique
  const detectionHistoryData = prepareDetectionHistoryData();
  const classHistoryData = prepareClassHistoryData();
  
  // Configuration des graphiques d'historique
  // Multi courbe par classe
  const classHistoryChartData = {
    labels: classHistoryData.labels,
    datasets: classHistoryData.datasets
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
          <button className={selectedTab === 'logs' ? 'active tab-button' : 'tab-button'} onClick={() => setSelectedTab('logs')}>Logs</button>
        </div>
      </div>
      <div className="panel-content">
        {selectedTab === 'model' && (
          <div className="model-metrics-section">
            {/* FPS, Inference Time, Object Count, Total Tracks, Active Trajectories, ID Switch, MOTA, MOTP, Objects by class */}
            <div className="metrics-row">
              <div className="metric-card">FPS<br /><span>{formatMetric(modelMetrics.fps, 1)}</span></div>
              <div className="metric-card">Inference Time<br /><span>{formatMetric(modelMetrics.inferenceTime)} ms</span></div>
              <div className="metric-card">Object Count<br /><span>{modelMetrics.objectCount ?? '--'}</span></div>
              <div className="metric-card">Total Tracks<br /><span>{modelMetrics.totalTracks ?? '--'}</span></div>
              <div className="metric-card">Active Trajectories<br /><span>{modelMetrics.active_trajectories ?? '--'}</span></div>
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

            {/* Elements from History tab moved here */}
            <div className="metrics-row">
              <div className="metric-card">Total Detections<br /><span>{detectionHistory.length}</span></div>
              <div className="metric-card">Classes Uniques<br /><span>{classHistoryData.labels.length}</span></div>
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
              <div className="metric-card">Battery<br /><span>{systemMetrics.battery_percent !== undefined
                        ? `${formatMetric(systemMetrics.battery_percent, 1)}%`
                        : '--'}
                      {systemMetrics.battery_plugged !== undefined
                        ? (systemMetrics.battery_plugged ? ' (Charging)' : ' (On battery)')
                        : ''}
                    </span>
                  </div>
            </div>
            <div className="metrics-row" style={{ height: '200px' }}>
              <Line options={systemChartOptions} data={systemChartData} />
            </div>
          </div>
        )}
        {/* History tab removed, content moved to model tab */}
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