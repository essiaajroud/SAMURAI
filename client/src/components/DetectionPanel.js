// DetectionPanel.js - Shows current, historical, and trajectory detection data
// Provides filtering, export, and analytics for detections
import React, { useState, useMemo } from 'react';
import './DetectionPanel.css';
import PropTypes from 'prop-types';

// Custom hook to filter detections and history based on UI controls
function useDetectionFilters(detections, detectionHistory, confidenceThreshold, selectedClass, timeRange) {
  // Support both array and object structure for detections
  const detectionsArray = useMemo(() => 
    Array.isArray(detections) ? detections : (detections?.detections || []),
    [detections]
  );
  // List of available classes for filtering
  const uniqueClasses = useMemo(
    () => ['all', 'person', 'soldier', 'weapon', 'military_vehicles', 'civilian_vehicles', 'military_aircraft', 'civilian_aircraft'],
    []
  );
  // Filter current detections by class and confidence
  const filteredCurrentDetections = useMemo(() =>
    detectionsArray.filter(detection => {
      const matchesClass = selectedClass === 'all' || detection.label === selectedClass;
      const matchesConfidence = detection.confidence >= confidenceThreshold;
      return matchesClass && matchesConfidence;
    }),
    [detectionsArray, selectedClass, confidenceThreshold]
  );
  // Calculate time range in ms
  const timeRangeMs = useMemo(() => {
    switch (timeRange) {
      case '1h': return 60 * 60 * 1000;
      case '6h': return 6 * 60 * 60 * 1000;
      case '24h': return 24 * 60 * 60 * 1000;
      default: return 60 * 60 * 1000;
    }
  }, [timeRange]);
  // Filter detection history by time, class, and confidence
  const filteredHistory = useMemo(() => {
    return detectionHistory.filter(detection => {
      const timestampMs = typeof detection.timestamp === 'string' 
        ? new Date(detection.timestamp).getTime() 
        : detection.timestamp;
      const isInTimeRange = Date.now() - timestampMs < timeRangeMs;
      const matchesClass = selectedClass === 'all' || detection.label === selectedClass;
      const matchesConfidence = detection.confidence >= confidenceThreshold;
      return isInTimeRange && matchesClass && matchesConfidence;
    });
  }, [detectionHistory, selectedClass, confidenceThreshold, timeRangeMs]);
  return { uniqueClasses, filteredCurrentDetections, filteredHistory };
}

// Custom hook to analyze trajectory data
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

// Main DetectionPanel component
const DetectionPanel = ({ detections = [], detectionHistory = [], trajectoryHistory = {}, isConnected = false }) => {
  const [confidenceThreshold, setConfidenceThreshold] = useState(0.5);
  const [selectedClass, setSelectedClass] = useState('all');
  const [activeTab, setActiveTab] = useState('current');
  const [timeRange, setTimeRange] = useState('24h'); // Default: 24h for history

  // Use custom hooks for filtering and analytics
  const { uniqueClasses, filteredCurrentDetections, filteredHistory } = useDetectionFilters(
    detections, detectionHistory, confidenceThreshold, selectedClass, timeRange
  );
  const trajectoryAnalysis = useTrajectoryAnalysis(trajectoryHistory);

  // Export filtered detection history as JSON
  const exportHistory = () => {
    const exportData = {
      exportDate: new Date().toISOString(),
      exportInfo: {
        totalDetections: detectionHistory.length,
        filteredDetections: filteredHistory.length,
        timeRange: timeRange,
        confidenceThreshold: confidenceThreshold,
        selectedClass: selectedClass,
        exportTimestamp: new Date().toLocaleString()
      },
      detectionHistory: detectionHistory,
      trajectoryHistory: trajectoryHistory,
      currentDetections: detections,
      filteredHistory: filteredHistory,
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
    link.download = `detection_history_${new Date().toISOString().split('T')[0]}_${timeRange}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  // --- Render ---
  return (
    <div className="detection-panel" style={{ height: '520px', overflow: 'auto', boxSizing: 'border-box' }}>
      {/* Panel header with export and filters */}
      <div className="panel-header">
        <div className="header-top">
          <h2>Detection Details</h2>
          <div className="header-controls">
            <button 
              className="export-button"
              onClick={exportHistory}
              title={`Export detection history (${filteredHistory.length} detections)`}
              disabled={!isConnected || filteredHistory.length === 0}
            >
              📊 Export ({filteredHistory.length})
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
        {/* Filters for class, confidence, and time range */}
        <div className="filters">
          <div className="filter-group">
            <label htmlFor="class-select">Class:</label>
            <select 
              id="class-select"
              value={selectedClass}
              onChange={(e) => setSelectedClass(e.target.value)}
              aria-label="Filter by class"
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
                aria-label="Filter by time range"
              >
                <option value="1h">Last Hour</option>
                <option value="6h">Last 6 Hours</option>
                <option value="24h">Last 24 Hours</option>
              </select>
            </div>
          )}
        </div>
      </div>
      {/* Panel content for current, history, and trajectories */}
      <div className="panel-content" style={{ height: 'calc(100% - 170px)', overflow: 'auto' }}>
        {activeTab === 'current' && (
          <div className="detections-table">
            <table>
              <thead>
                <tr>
                  <th>Object</th>
                  <th>Confidence</th>
                  <th>Position</th>
                </tr>
              </thead>
              <tbody>
                {filteredCurrentDetections.map((detection, index) => (
                  <tr key={index}>
                    <td>{detection.label}</td>
                    <td>{(detection.confidence * 100).toFixed(1)}%</td>
                    <td>({detection.x.toFixed(0)}, {detection.y.toFixed(0)})</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {activeTab === 'history' && (
          <div className="detections-table">
            {filteredHistory.length === 0 ? (
              <div className="no-data-message">
                <p>📊 No detections found for the selected criteria</p>
                <p>Period: {timeRange === '1h' ? 'Last hour' : timeRange === '6h' ? 'Last 6 hours' : 'Last 24 hours'}</p>
                <p>Confidence: ≥{(confidenceThreshold * 100).toFixed(0)}% | Class: {selectedClass === 'all' ? 'All' : selectedClass}</p>
              </div>
            ) : (
              <>
                <div className="history-summary">
                  <span>📈 {filteredHistory.length} detections in the {timeRange === '1h' ? 'last hour' : timeRange === '6h' ? 'last 6 hours' : 'last 24 hours'}</span>
                </div>
                <table>
                  <thead>
                    <tr>
                      <th>🕒 DateTime</th>
                      <th>🎯 Object</th>
                      <th>📊 Confidence</th>
                      <th>📍 Position (x, y)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredHistory
                      .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp)) // Trier par date décroissante
                      .map((detection, index) => (
                      <tr key={index} className={detection.confidence >= 0.8 ? 'high-confidence' : detection.confidence >= 0.6 ? 'medium-confidence' : 'low-confidence'}>
                        <td>{new Date(detection.timestamp).toLocaleString('en-US', {
                          year: 'numeric',
                          month: '2-digit',
                          day: '2-digit',
                          hour: '2-digit',
                          minute: '2-digit',
                          second: '2-digit'
                        })}</td>
                        <td><strong>{detection.label}</strong></td>
                        <td>
                          <span className={`confidence-badge ${detection.confidence >= 0.8 ? 'high' : detection.confidence >= 0.6 ? 'medium' : 'low'}`}>
                            {(detection.confidence * 100).toFixed(1)}%
                          </span>
                        </td>
                        <td>({detection.x.toFixed(0)}, {detection.y.toFixed(0)})</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </>
            )}
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