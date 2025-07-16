// PerformancePanel.js - Shows system performance, analytics, and logs
// Provides graphs, historical stats, and system log display
import React, { useState, useMemo } from 'react';
import './PerformancePanel.css';
import PropTypes from 'prop-types';

// Custom hook to compute detection history statistics
function useHistoryStats(detectionHistory) {
  return useMemo(() => {
    const now = Date.now();
    const oneHourAgo = now - (60 * 60 * 1000);
    const sixHoursAgo = now - (6 * 60 * 60 * 1000);
    const oneDayAgo = now - (24 * 60 * 60 * 1000);
    // Filter detections by time
    const hourlyDetections = detectionHistory.filter(d => {
      const timestampMs = typeof d.timestamp === 'string' 
        ? new Date(d.timestamp).getTime() 
        : d.timestamp;
      return timestampMs > oneHourAgo;
    });
    const sixHourDetections = detectionHistory.filter(d => {
      const timestampMs = typeof d.timestamp === 'string' 
        ? new Date(d.timestamp).getTime() 
        : d.timestamp;
      return timestampMs > sixHoursAgo;
    });
    const dailyDetections = detectionHistory.filter(d => {
      const timestampMs = typeof d.timestamp === 'string' 
        ? new Date(d.timestamp).getTime() 
        : d.timestamp;
      return timestampMs > oneDayAgo;
    });
    // Unique object count and average confidence
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

// Main PerformancePanel component
const PerformancePanel = ({ fps, inferenceTime, objectCount, logs = [], detectionHistory = [], isConnected = false }) => {
  const [selectedTab, setSelectedTab] = useState('graphs');
  // Use custom hook for stats
  const historyStats = useHistoryStats(detectionHistory);

  // --- Render ---
  return (
    <div className="performance-panel">
      {/* Panel header and tabs */}
      <div className="panel-header">
        <div className="header-top">
          <h2>Performance & Analytics</h2>
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
      {/* Panel content for graphs, analytics, and logs */}
      <div className="panel-content">
        {selectedTab === 'graphs' ? (
          <div className="graphs-container">
            {/* FPS graph */}
            <div className="graph-card">
              <h3>FPS</h3>
              <div className="graph-value">{fps.toFixed(1)}</div>
              <div className="graph-bar">
                <div 
                  className="graph-bar-fill"
                  style={{ width: `${Math.min((fps / 30) * 100, 100)}%` }}
                  aria-label="FPS bar"
                />
              </div>
            </div>
            {/* Inference time graph */}
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
                  aria-label="Inference time bar"
                />
              </div>
            </div>
            {/* Object count graph */}
            <div className="graph-card">
              <h3>Objects Detected</h3>
              <div className="graph-value">{objectCount}</div>
              <div className="graph-bar">
                <div 
                  className="graph-bar-fill"
                  style={{ width: `${Math.min((objectCount / 10) * 100, 100)}%` }}
                  aria-label="Objects detected bar"
                />
              </div>
            </div>
            {/* Total history graph */}
            <div className="graph-card">
              <h3>Total History</h3>
              <div className="graph-value">{historyStats.totalDetections}</div>
              <div className="graph-bar">
                <div 
                  className="graph-bar-fill"
                  style={{ width: `${Math.min((historyStats.totalDetections / 1000) * 100, 100)}%` }}
                  aria-label="Total history bar"
                />
              </div>
            </div>
          </div>
        ) : selectedTab === 'history' ? (
          <div className="history-analytics">
            {/* Connection warning if backend is not connected */}
            {!isConnected && (
              <div className="connection-warning">
                <p>⚠️ Backend not connected. Historical analytics may be incomplete.</p>
              </div>
            )}
            <div className="analytics-grid">
             
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
          </div>
        ) : (
          <div className="system-logs-panel">
            <ul className="logs-list">
              {/* Always show backend connection status as first log */}
              <li className={`log-entry ${isConnected ? 'info' : 'error'}`}>
                <span className={`log-timestamp`}>{new Date().toLocaleString()}</span>
                <span className={`log-level ${isConnected ? 'info' : 'error'}`}>[{isConnected ? 'INFO' : 'ERROR'}]</span>
                <span className="log-message">
                  Backend {isConnected ? 'connected' : 'not connected'}
                </span>
              </li>
              {/* System status and control messages */}
              {logs && logs.length > 0 && logs
                .filter(log => {
                  const msg = (log.message || '').toLowerCase();
                  return (
                    msg.includes('system started') ||
                    msg.includes('system stopped') ||
                    msg.includes('detection streaming activated') ||
                    msg.includes('detection streaming deactivated') ||
                    msg.includes('streaming') ||
                    msg.includes('started') ||
                    msg.includes('stopped')
                  );
                })
                .map((log, idx) => {
                  let levelClass = 'info';
                  if (log.level === 'WARNING' || log.level === 'WARN') levelClass = 'warning';
                  if (log.level === 'ERROR') levelClass = 'error';
                  return (
                    <li key={`system-${idx}`} className={`log-entry ${levelClass}`}>
                      <span className={`log-timestamp`}>{log.timestamp ? new Date(log.timestamp).toLocaleString() : ''}</span>
                      <span className={`log-level ${levelClass}`}>
                        [{log.level || 'INFO'}]
                      </span>
                      <span className="log-message">
                        {log.message || String(log)}
                      </span>
                    </li>
                  );
                })}
              {/* Low confidence detections as warnings */}
              {detectionHistory && detectionHistory.length > 0 && detectionHistory
                .filter(detection => detection.confidence < 0.5)
                .slice(-20)
                .map((detection, idx) => (
                  <li key={`low-conf-${idx}`} className="log-entry warning">
                    <span className="log-timestamp">
                      {typeof detection.timestamp === 'string' 
                        ? new Date(detection.timestamp).toLocaleString() 
                        : new Date(detection.timestamp).toLocaleString()}
                    </span>
                    <span className="log-level warning">[WARNING]</span>
                    <span className="log-message">
                      Low confidence detection: {detection.label} ({(detection.confidence * 100).toFixed(1)}%) at ({detection.x.toFixed(0)}, {detection.y.toFixed(0)})
                    </span>
                  </li>
                ))}
              {/* Other system logs (errors, backend, etc.) */}
              {logs && logs.length > 0 && logs
                .filter(log => {
                  const msg = (log.message || '').toLowerCase();
                  return (
                    msg.includes('database') ||
                    msg.includes('db') ||
                    msg.includes('model') ||
                    msg.includes('backend') ||
                    msg.includes('connection') ||
                    msg.includes('disconnected') ||
                    msg.includes('connected') ||
                    msg.includes('error') ||
                    msg.includes('failed')
                  );
                })
                .map((log, idx) => {
                  let levelClass = 'info';
                  if (log.level === 'WARNING' || log.level === 'WARN') levelClass = 'warning';
                  if (log.level === 'ERROR') levelClass = 'error';
                  return (
                    <li key={`other-${idx}`} className={`log-entry ${levelClass}`}>
                      <span className={`log-timestamp`}>{log.timestamp ? new Date(log.timestamp).toLocaleString() : ''}</span>
                      <span className={`log-level ${levelClass}`}>
                        [{log.level || 'INFO'}]
                      </span>
                      <span className="log-message">
                        {log.message || String(log)}
                      </span>
                    </li>
                  );
                })}
            </ul>
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