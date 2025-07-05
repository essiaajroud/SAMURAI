import React, { useState, useMemo } from 'react';
import './DetectionPanel.css';
import PropTypes from 'prop-types';

// Hook pour filtrer les détections et l'historique
function useDetectionFilters(detections, detectionHistory, confidenceThreshold, selectedClass, timeRange) {
  const uniqueClasses = useMemo(
    () => ['all', ...new Set(detections.map(d => d.label))],
    [detections]
  );

  const filteredCurrentDetections = useMemo(() =>
    detections.filter(detection => {
      const matchesClass = selectedClass === 'all' || detection.label === selectedClass;
      const matchesConfidence = detection.confidence >= confidenceThreshold;
      return matchesClass && matchesConfidence;
    }),
    [detections, selectedClass, confidenceThreshold]
  );

  // Calculer la plage de temps en ms une seule fois
  const timeRangeMs = useMemo(() => {
    switch (timeRange) {
      case '1h': return 60 * 60 * 1000;
      case '6h': return 6 * 60 * 60 * 1000;
      case '24h': return 24 * 60 * 60 * 1000;
      default: return 60 * 60 * 1000;
    }
  }, [timeRange]);

  const filteredHistory = useMemo(() =>
    detectionHistory.filter(detection => {
      const isInTimeRange = Date.now() - detection.timestamp < timeRangeMs;
      const matchesClass = selectedClass === 'all' || detection.label === selectedClass;
      const matchesConfidence = detection.confidence >= confidenceThreshold;
      return isInTimeRange && matchesClass && matchesConfidence;
    }),
    [detectionHistory, selectedClass, confidenceThreshold, timeRangeMs]
  );

  return { uniqueClasses, filteredCurrentDetections, filteredHistory };
}

// Hook pour analyser les trajectoires
function useTrajectoryAnalysis(trajectoryHistory) {
  return useMemo(() =>
    Object.values(trajectoryHistory).map(trajectory => {
      const points = trajectory.points;
      const duration = trajectory.lastSeen - trajectory.startTime;
      const totalDistance = points.reduce((acc, point, index) => {
        if (index === 0) return 0;
        const prevPoint = points[index - 1];
        const dx = point.x - prevPoint.x;
        const dy = point.y - prevPoint.y;
        return acc + Math.sqrt(dx * dx + dy * dy);
      }, 0);
      const avgSpeed = duration > 0 ? (totalDistance / duration) * 1000 : 0; // pixels/sec
      return {
        id: trajectory.id,
        label: trajectory.label,
        startTime: trajectory.startTime,
        lastSeen: trajectory.lastSeen,
        duration: duration,
        totalDistance: totalDistance,
        avgSpeed: avgSpeed,
        pointCount: points.length
      };
    }),
    [trajectoryHistory]
  );
}


const DetectionPanel = ({ detections = [], detectionHistory = [], trajectoryHistory = {}, isConnected = false }) => {
  const [confidenceThreshold, setConfidenceThreshold] = useState(0.5);
  const [selectedClass, setSelectedClass] = useState('all');
  const [activeTab, setActiveTab] = useState('current');
  const [timeRange, setTimeRange] = useState('1h'); // 1h, 6h, 24h

  // Utilisation des hooks personnalisés
  const { uniqueClasses, filteredCurrentDetections, filteredHistory } = useDetectionFilters(
    detections, detectionHistory, confidenceThreshold, selectedClass, timeRange
  );
  const trajectoryAnalysis = useTrajectoryAnalysis(trajectoryHistory);

  // Fonction pour exporter l'historique
  const exportHistory = () => {
    const exportData = {
      exportDate: new Date().toISOString(),
      detectionHistory: detectionHistory,
      trajectoryHistory: trajectoryHistory,
      currentDetections: detections,
      filters: {
        confidenceThreshold,
        selectedClass,
        timeRange
      }
    };
    const dataStr = JSON.stringify(exportData, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `detection_history_${new Date().toISOString().split('T')[0]}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="detection-panel">
      <div className="panel-header">
        <div className="header-top">
          <h2>Detection Details</h2>
          <div className="header-controls">
            <div className="connection-indicator">
              <span className={`status-dot ${isConnected ? 'connected' : 'disconnected'}`}></span>
              <span className="status-text">
                {isConnected ? 'Backend Connected' : 'Backend Disconnected'}
              </span>
            </div>
            <button 
              className="export-button"
              onClick={exportHistory}
              title="Export detection history"
              disabled={!isConnected}
            >
              📊 Export
            </button>
          </div>
        </div>
        <div className="panel-tabs">
          <button 
            className={`tab-button ${activeTab === 'current' ? 'active' : ''}`}
            onClick={() => setActiveTab('current')}
          >
            Current
          </button>
          <button 
            className={`tab-button ${activeTab === 'history' ? 'active' : ''}`}
            onClick={() => setActiveTab('history')}
          >
            History
          </button>
          <button 
            className={`tab-button ${activeTab === 'trajectories' ? 'active' : ''}`}
            onClick={() => setActiveTab('trajectories')}
          >
            Trajectories
          </button>
        </div>
        <div className="filters">
          <div className="filter-group">
            <label htmlFor="class-select">Class:</label>
            <select 
              id="class-select"
              value={selectedClass}
              onChange={(e) => setSelectedClass(e.target.value)}
              aria-label="Filtrer par classe"
            >
              {uniqueClasses.map(cls => (
                <option key={cls} value={cls}>
                  {cls.charAt(0).toUpperCase() + cls.slice(1)}
                </option>
              ))}
            </select>
          </div>
          <div className="filter-group">
            <label htmlFor="confidence-range">Confidence:</label>
            <input
              id="confidence-range"
              type="range"
              min="0"
              max="1"
              step="0.1"
              value={confidenceThreshold}
              onChange={(e) => setConfidenceThreshold(parseFloat(e.target.value))}
              aria-valuenow={confidenceThreshold}
              aria-valuemin={0}
              aria-valuemax={1}
            />
            <span>{Math.round(confidenceThreshold * 100)}%</span>
          </div>
          {activeTab === 'history' && (
            <div className="filter-group">
              <label htmlFor="time-range-select">Time Range:</label>
              <select 
                id="time-range-select"
                value={timeRange}
                onChange={(e) => setTimeRange(e.target.value)}
                aria-label="Filtrer par plage temporelle"
              >
                <option value="1h">Last Hour</option>
                <option value="6h">Last 6 Hours</option>
                <option value="24h">Last 24 Hours</option>
              </select>
            </div>
          )}
        </div>
      </div>

      <div className="panel-content">
        {activeTab === 'current' && (
          <div className="detections-table">
            <table>
              <thead>
                <tr>
                  <th>Object</th>
                  <th>Confidence</th>
                  <th>Speed</th>
                  <th>Position</th>
                  <th>Distance</th>
                </tr>
              </thead>
              <tbody>
                {filteredCurrentDetections.map((detection, index) => (
                  <tr key={index}>
                    <td>{detection.label}</td>
                    <td>{(detection.confidence * 100).toFixed(1)}%</td>
                    <td>{detection.speed?.toFixed(1) || 'N/A'} m/s</td>
                    <td>({detection.x.toFixed(0)}, {detection.y.toFixed(0)})</td>
                    <td>{detection.distance?.toFixed(1) || 'N/A'} m</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {activeTab === 'history' && (
          <div className="detections-table">
            <table>
              <thead>
                <tr>
                  <th>Object</th>
                  <th>Confidence</th>
                  <th>Speed</th>
                  <th>Position</th>
                  <th>Distance</th>
                  <th>Timestamp</th>
                </tr>
              </thead>
              <tbody>
                {filteredHistory.map((detection, index) => (
                  <tr key={index}>
                    <td>{detection.label}</td>
                    <td>{(detection.confidence * 100).toFixed(1)}%</td>
                    <td>{detection.speed?.toFixed(1) || 'N/A'} m/s</td>
                    <td>({detection.x.toFixed(0)}, {detection.y.toFixed(0)})</td>
                    <td>{detection.distance?.toFixed(1) || 'N/A'} m</td>
                    <td>{new Date(detection.timestamp).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {activeTab === 'trajectories' && (
          <div className="trajectories-table">
            <table>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Label</th>
                  <th>Duration (s)</th>
                  <th>Total Distance</th>
                  <th>Avg Speed</th>
                  <th>Points</th>
                </tr>
              </thead>
              <tbody>
                {trajectoryAnalysis.map((traj, index) => (
                  <tr key={index}>
                    <td>{traj.id}</td>
                    <td>{traj.label}</td>
                    <td>{(traj.duration / 1000).toFixed(1)}</td>
                    <td>{traj.totalDistance.toFixed(1)}</td>
                    <td>{traj.avgSpeed.toFixed(2)}</td>
                    <td>{traj.pointCount}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

DetectionPanel.propTypes = {
  detections: PropTypes.array,
  detectionHistory: PropTypes.array,
  trajectoryHistory: PropTypes.object,
  isConnected: PropTypes.bool
};

export default DetectionPanel;