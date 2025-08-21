// Detection panel component for displaying current and historical detections
import React, { useState, useMemo } from 'react';
import './DetectionPanel.css';
import PropTypes from 'prop-types';

// Filtering logic hook
function useDetectionFilters(detections, detectionHistory, confidenceThreshold, selectedClass, timeRange) {
  const detectionsArray = useMemo(() => 
    Array.isArray(detections) ? detections : (detections?.detections || []),
    [detections]
  );
  
  const uniqueClasses = useMemo(
    () => ['all', 'person', 'soldier', 'weapon', 'military_vehicles', 'civilian_vehicles', 'military_aircraft', 'civilian_aircraft'],
    []
  );

  const filteredCurrentDetections = useMemo(() =>
    detectionsArray.filter(detection => {
      const matchesClass = selectedClass === 'all' || detection.label === selectedClass;
      const matchesConfidence = detection.confidence >= confidenceThreshold;
      return matchesClass && matchesConfidence;
    }),
    [detectionsArray, selectedClass, confidenceThreshold]
  );
  
  const filteredHistory = useMemo(() => {
    const nowMs = Date.now();
    let timeLimitMs = 0;
    
    switch(timeRange) {
      case '1h': timeLimitMs = nowMs - (60 * 60 * 1000); break;
      case '6h': timeLimitMs = nowMs - (6 * 60 * 60 * 1000); break;
      case '24h': timeLimitMs = nowMs - (24 * 60 * 60 * 1000); break;
      default: timeLimitMs = 0;
    }

    return detectionHistory.filter(detection => {
      const timestampMs = new Date(detection.timestamp).getTime();
      return timestampMs >= timeLimitMs &&
             (selectedClass === 'all' || detection.label === selectedClass) &&
             detection.confidence >= confidenceThreshold;
    });
  }, [detectionHistory, selectedClass, confidenceThreshold, timeRange]);

  return { uniqueClasses, filteredCurrentDetections, filteredHistory };
}

const DetectionPanel = ({ detections = [], detectionHistory = [], isConnected = false }) => {
  const [filters, setFilters] = useState({
    confidenceThreshold: 0.5,
    selectedClass: 'all',
    timeRange: '24h'
  });
  const [activeTab, setActiveTab] = useState('current');

  const { uniqueClasses, filteredCurrentDetections, filteredHistory } = useDetectionFilters(
    detections, detectionHistory, filters.confidenceThreshold, filters.selectedClass, filters.timeRange
  );

  const exportHistory = () => {
    const exportData = {
      exportDate: new Date().toISOString(),
      filters: { timeRange: filters.timeRange, confidenceThreshold: filters.confidenceThreshold, selectedClass: filters.selectedClass },
      detectionCount: filteredHistory.length,
      detections: filteredHistory,
    };
    const dataStr = JSON.stringify(exportData, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `detection_export_${new Date().toISOString().split('T')[0]}.json`;
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="detection-panel" style={{ height: '622px', width: '100%', maxWidth: '100%', overflow: 'hidden', boxSizing: 'border-box' }}>
      <div className="panel-header">
        <div className="header-top">
          <h2>Detection Details</h2>
          <button 
            className="export-button" 
            onClick={exportHistory}
            disabled={!isConnected || filteredHistory.length === 0}
            title={`Export ${filteredHistory.length} detections from history`}
          >
            📊 Export ({filteredHistory.length})
          </button>
        </div>
        <div className="panel-tabs">
          <button className={`tab-button ${activeTab === 'current' ? 'active' : ''}`} onClick={() => setActiveTab('current')}>
            Current ({filteredCurrentDetections.length})
          </button>
          <button className={`tab-button ${activeTab === 'history' ? 'active' : ''}`} onClick={() => setActiveTab('history')}>
            History ({filteredHistory.length})
          </button>
        </div>
        <div className="filters">
          <div className="filter-group">
            <label htmlFor="class-select">Class:</label>
            <select id="class-select" value={filters.selectedClass} onChange={(e) => setFilters({ ...filters, selectedClass: e.target.value })}>
              {uniqueClasses.map(cls => (
                <option key={cls} value={cls}>{cls.charAt(0).toUpperCase() + cls.slice(1).replace('_', ' ')}</option>
              ))}
            </select>
          </div>
          <div className="filter-group">
            <label htmlFor="confidence-range">Confidence:</label>
            <input id="confidence-range" type="range" min="0" max="1" step="0.05" value={filters.confidenceThreshold} onChange={(e) => setFilters({ ...filters, confidenceThreshold: parseFloat(e.target.value) })} />
            <span>{Math.round(filters.confidenceThreshold * 100)}%</span>
          </div>
          {activeTab === 'history' && (
            <div className="filter-group">
              <label htmlFor="time-range-select">Time Range:</label>
              <select id="time-range-select" value={filters.timeRange} onChange={(e) => setFilters({ ...filters, timeRange: e.target.value })}>
                <option value="1h">Last Hour</option>
                <option value="6h">Last 6 Hours</option>
                <option value="24h">Last 24 Hours</option>
              </select>
            </div>
          )}
        </div>
      </div>

      <div className="panel-content" style={{ height: 'calc(100% - 170px)', overflow: 'hidden', width: '100%' }}>
        {activeTab === 'current' && (
          <div className="detections-table">
            {filteredCurrentDetections.length === 0 ? (
              <div className="no-data-message"><p>Waiting for new detections...</p></div>
            ) : (
              <div className="table-container">
                <table>
                  <thead><tr><th>ID</th><th>Object</th><th>Confidence</th><th>📍GPS(Lat, Lon)</th></tr></thead>
                  <tbody>
                    {filteredCurrentDetections.map((d) => (
                      <tr key={d.historyId}>
                        <td>{d.id}</td>
                        <td><strong>{d.label}</strong></td>
                        <td><span className={`confidence-badge ${d.confidence >= 0.8 ? 'high' : 'medium'}`}>{(d.confidence * 100).toFixed(1)}%</span></td>
                        <td>{d.latitude ? `${d.latitude.toFixed(4)}, ${d.longitude.toFixed(4)}` : 'Calculating...'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
        {activeTab === 'history' && (
          <div className="detections-table">
            {filteredHistory.length === 0 ? (
              <div className="no-data-message"><p>No historical detections match the current filters.</p></div>
            ) : (
              <div className="table-container">
                <table>
                  <thead><tr><th>ID</th><th>🕒 DateTime</th><th>Object</th><th>Confidence</th><th>📍GPS(Lat, Lon)</th></tr></thead>
                  <tbody>
                    {filteredHistory.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp)).map((d) => (
                      <tr key={d.historyId}>
                        <td>{d.id}</td>
                        <td>{new Date(d.timestamp).toLocaleString()}</td>
                        <td><strong>{d.label}</strong></td>
                        <td><span className={`confidence-badge ${d.confidence >= 0.8 ? 'high' : 'medium'}`}>{(d.confidence * 100).toFixed(1)}%</span></td>
                        <td>{d.latitude ? `${d.latitude.toFixed(4)}, ${d.longitude.toFixed(4)}` : 'N/A'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

DetectionPanel.propTypes = {
  detections: PropTypes.oneOfType([PropTypes.array, PropTypes.object]),
  detectionHistory: PropTypes.array,
  isConnected: PropTypes.bool
};

export default DetectionPanel;