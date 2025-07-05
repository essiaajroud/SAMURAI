import React, { useState, useMemo, useEffect } from 'react';
import './PerformancePanel.css';
import PropTypes from 'prop-types';

// Hook pour calculer les statistiques d'historique
function useHistoryStats(detectionHistory) {
  return useMemo(() => {
    const now = Date.now();
    const oneHourAgo = now - (60 * 60 * 1000);
    const sixHoursAgo = now - (6 * 60 * 60 * 1000);
    const oneDayAgo = now - (24 * 60 * 60 * 1000);

    const hourlyDetections = detectionHistory.filter(d => d.timestamp > oneHourAgo);
    const sixHourDetections = detectionHistory.filter(d => d.timestamp > sixHoursAgo);
    const dailyDetections = detectionHistory.filter(d => d.timestamp > oneDayAgo);

    const uniqueObjects = new Set(detectionHistory.map(d => d.id)).size;
    const avgConfidence = detectionHistory.length > 0 
      ? detectionHistory.reduce((acc, d) => acc + d.confidence, 0) / detectionHistory.length 
      : 0;

    return {
      hourlyCount: hourlyDetections.length,
      sixHourCount: sixHourDetections.length,
      dailyCount: dailyDetections.length,
      uniqueObjects,
      avgConfidence: avgConfidence * 100,
      totalDetections: detectionHistory.length
    };
  }, [detectionHistory]);
}

const PerformancePanel = ({ fps, inferenceTime, objectCount, logs = [], detectionHistory = [], isConnected = false }) => {
  const [selectedTab, setSelectedTab] = useState('graphs');

  // Utilisation du hook pour les stats
  const historyStats = useHistoryStats(detectionHistory);

  return (
    <div className="performance-panel">
      <div className="panel-header">
        <div className="header-top">
          <h2>Performance & Analytics</h2>
          <div className="connection-status">
            <span className={`status-dot ${isConnected ? 'connected' : 'disconnected'}`}></span>
            <span className="status-text">
              {isConnected ? 'Backend Connected' : 'Backend Disconnected'}
            </span>
          </div>
        </div>
        <div className="panel-tabs">
          <button
            className={`tab-button ${selectedTab === 'graphs' ? 'active' : ''}`}
            onClick={() => setSelectedTab('graphs')}
            aria-label="Show performance graphs"
          >
            Performance Graphs
          </button>
          <button
            className={`tab-button ${selectedTab === 'history' ? 'active' : ''}`}
            onClick={() => setSelectedTab('history')}
            aria-label="Show historical analytics"
          >
            History Analytics
          </button>
          <button
            className={`tab-button ${selectedTab === 'logs' ? 'active' : ''}`}
            onClick={() => setSelectedTab('logs')}
            aria-label="Show system logs"
          >
            System Logs
          </button>
        </div>
      </div>

      <div className="panel-content">
        {selectedTab === 'graphs' ? (
          <div className="graphs-container">
            <div className="graph-card">
              <h3>FPS</h3>
              <div className="graph-value">{fps.toFixed(1)}</div>
              <div className="graph-bar">
                <div 
                  className="graph-bar-fill"
                  style={{ width: `${Math.min((fps / 30) * 100, 100)}%` }}
                  aria-label="Barre de FPS"
                />
              </div>
            </div>

            <div className="graph-card">
              <h3>Inference Time</h3>
              <div className="graph-value">{inferenceTime.toFixed(1)}ms</div>
              <div className="graph-bar">
                <div 
                  className="graph-bar-fill"
                  style={{ 
                    width: `${Math.min((inferenceTime / 100) * 100, 100)}%`,
                    backgroundColor: inferenceTime > 50 ? '#ff4444' : '#00ff00'
                  }}
                  aria-label="Barre de temps d'inférence"
                />
              </div>
            </div>

            <div className="graph-card">
              <h3>Objects Detected</h3>
              <div className="graph-value">{objectCount}</div>
              <div className="graph-bar">
                <div 
                  className="graph-bar-fill"
                  style={{ width: `${Math.min((objectCount / 10) * 100, 100)}%` }}
                  aria-label="Barre d'objets détectés"
                />
              </div>
            </div>

            <div className="graph-card">
              <h3>Total History</h3>
              <div className="graph-value">{historyStats.totalDetections}</div>
              <div className="graph-bar">
                <div 
                  className="graph-bar-fill"
                  style={{ width: `${Math.min((historyStats.totalDetections / 1000) * 100, 100)}%` }}
                  aria-label="Barre d'historique total"
                />
              </div>
            </div>
          </div>
        ) : selectedTab === 'history' ? (
          <div className="history-analytics">
            {!isConnected && (
              <div className="connection-warning">
                <p>⚠️ Backend not connected. Historical analytics may be incomplete.</p>
              </div>
            )}
            <div className="analytics-grid">
              <div className="analytics-card">
                <h4>Last Hour</h4>
                <div className="analytics-value">{historyStats.hourlyCount}</div>
                <div className="analytics-label">detections</div>
              </div>
              
              <div className="analytics-card">
                <h4>Last 6 Hours</h4>
                <div className="analytics-value">{historyStats.sixHourCount}</div>
                <div className="analytics-label">detections</div>
              </div>
              
              <div className="analytics-card">
                <h4>Last 24 Hours</h4>
                <div className="analytics-value">{historyStats.dailyCount}</div>
                <div className="analytics-label">detections</div>
              </div>
              
              <div className="analytics-card">
                <h4>Unique Objects</h4>
                <div className="analytics-value">{historyStats.uniqueObjects}</div>
                <div className="analytics-label">tracked</div>
              </div>
              
              <div className="analytics-card">
                <h4>Avg Confidence</h4>
                <div className="analytics-value">{historyStats.avgConfidence.toFixed(1)}%</div>
                <div className="analytics-label">overall</div>
              </div>
              
              <div className="analytics-card">
                <h4>Total Detections</h4>
                <div className="analytics-value">{historyStats.totalDetections}</div>
                <div className="analytics-label">all time</div>
              </div>
            </div>
            
            <div className="detection-timeline">
              <h4>Recent Detection Timeline</h4>
              <div className="timeline-container">
                {detectionHistory.slice(-10).reverse().map((detection, index) => (
                  <div key={detection.historyId || index} className="timeline-item">
                    <div className="timeline-time">
                      {new Date(detection.timestamp).toLocaleTimeString()}
                    </div>
                    <div className="timeline-content">
                      <span className="timeline-object">{detection.label}</span>
                      <span className="timeline-confidence">
                        {(detection.confidence * 100).toFixed(1)}%
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        ) : (
          <div className="system-logs-panel">
            {logs && (
              <ul className="logs-list">
                {/* Always show backend connection status as first log */}
                <li className={`log-entry ${isConnected ? 'info' : 'error'}`}>
                  <span className={`log-timestamp`}>{new Date().toLocaleString()}</span>
                  <span className={`log-level ${isConnected ? 'info' : 'error'}`}>[{isConnected ? 'INFO' : 'ERROR'}]</span>
                  <span className="log-message">
                    Backend {isConnected ? 'connected' : 'not connected'}
                  </span>
                </li>
                {logs && logs.length > 0 ? (
                  logs
                    .filter(log => {
                      const msg = (log.message || '').toLowerCase();
                      // Show system logs and also logs with confidence < 0.5
                      if (
                        msg.includes('database') ||
                        msg.includes('db') ||
                        msg.includes('model') ||
                        msg.includes('backend') ||
                        msg.includes('connection') ||
                        msg.includes('disconnected') ||
                        msg.includes('connected')
                      ) {
                        return true;
                      }
                      // Detect low confidence logs by value if present
                      if (log.confidence !== undefined && typeof log.confidence === 'number' && log.confidence < 0.5) {
                        return true;
                      }
                      // Fallback: try to match 'low confidence' in message
                      if (msg.includes('low confidence')) {
                        return true;
                      }
                      return false;
                    })
                    .map((log, idx) => {
                      let levelClass = 'info';
                      if (log.level === 'WARNING' || log.level === 'WARN') levelClass = 'warning';
                      if (log.level === 'ERROR') levelClass = 'error';
                      return (
                        <li key={idx} className={`log-entry ${levelClass}`}>
                          <span className={`log-timestamp`}>{log.timestamp ? new Date(log.timestamp).toLocaleString() : ''}</span>
                          <span className={`log-level ${levelClass}`}>
                            [{log.level || 'INFO'}]
                          </span>
                          <span className="log-message">
                            {log.message || String(log)}
                          </span>
                        </li>
                      );
                    })
                ) : null}
              </ul>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

PerformancePanel.propTypes = {
  fps: PropTypes.number.isRequired,
  inferenceTime: PropTypes.number.isRequired,
  objectCount: PropTypes.number.isRequired,
  logs: PropTypes.array,
  detectionHistory: PropTypes.array,
  isConnected: PropTypes.bool
};

export default PerformancePanel;