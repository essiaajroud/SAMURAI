// App.js - Main application component for the Military Detection System Dashboard
// Handles backend connection, data fetching, and layout
import React, { useState, useEffect, useCallback } from 'react';
import Header from './components/Header';
import CameraView from './components/CameraView';
import DetectionPanel from './components/DetectionPanel';
import PerformancePanel from './components/PerformancePanel';
import TrackingMap from './components/TrackingMap';
import './App.css';

// API base URL configuration
const API_BASE_URL = 'http://localhost:5000/api';

function App() {
  // --- State Management ---
  const [systemStatus, setSystemStatus] = useState('stopped'); // System running/stopped
  const [isPlaying, setIsPlaying] = useState(false); // Video play state
  const [isConnected, setIsConnected] = useState(false); // Backend connection status

  const [performanceData, setPerformanceData] = useState({
    fps: 30,
    inferenceTime: 33,
    objectCount: 5
  });

  const [detectionHistory, setDetectionHistory] = useState([]); // Detection history
  const [trajectoryHistory, setTrajectoryHistory] = useState({}); // Trajectory history
  const [currentDetections, setCurrentDetections] = useState([]); // Current detections
  const [logs, setLogs] = useState([]); // System logs

  // --- Inline Styles ---
  const appStyle = {
    minHeight: '100vh',
    background: `linear-gradient(rgba(0, 0, 0, 0.7), rgba(0, 0, 0, 0.7)), url('/BG.jfif')`,
    backgroundSize: 'cover',
    backgroundPosition: 'center',
    backgroundAttachment: 'fixed',
    color: '#ffffff',
    display: 'flex',
    flexDirection: 'column'
  };

  // --- Backend Connection Check ---
  const checkBackendConnection = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/health`);
      if (response.ok) {
        setIsConnected(true);
        console.log('Backend connected successfully');
      } else {
        setIsConnected(false);
        console.warn('Backend health check failed');
      }
    } catch (error) {
      setIsConnected(false);
      console.error('Backend connection error:', error);
    }
  }, []);

  // --- Detection History Fetch ---
  const loadDetectionHistory = useCallback(async () => {
    if (!isConnected) return;
    try {
      const response = await fetch(`${API_BASE_URL}/detections?limit=1000`);
      if (response.ok) {
        const history = await response.json();
        setDetectionHistory(history);
        console.log('Detection history loaded:', history.length, 'records');
      }
    } catch (error) {
      console.error('Error loading detection history:', error);
    }
  }, [isConnected]);

  // --- Trajectory History Fetch ---
  const loadTrajectoryHistory = useCallback(async () => {
    if (!isConnected) return;
    try {
      const response = await fetch(`${API_BASE_URL}/trajectories`);
      if (response.ok) {
        const trajectories = await response.json();
        const trajectoryMap = {};
        trajectories.forEach(trajectory => {
          trajectoryMap[trajectory.id] = {
            id: trajectory.id,
            label: trajectory.label,
            startTime: new Date(trajectory.startTime).getTime(),
            lastSeen: new Date(trajectory.lastSeen).getTime(),
            points: trajectory.points
          };
        });
        setTrajectoryHistory(trajectoryMap);
        console.log('Trajectory history loaded:', trajectories.length, 'trajectories');
      }
    } catch (error) {
      console.error('Error loading trajectory history:', error);
    }
  }, [isConnected]);

  // --- Cleanup Old Data ---
  const cleanupOldData = useCallback(async () => {
    if (!isConnected) return;
    try {
      const response = await fetch(`${API_BASE_URL}/cleanup`, {
        method: 'POST'
      });
      if (response.ok) {
        const result = await response.json();
        console.log('Cleanup completed:', result);
        await loadDetectionHistory();
        await loadTrajectoryHistory();
      }
    } catch (error) {
      console.error('Error during cleanup:', error);
    }
  }, [isConnected, loadDetectionHistory, loadTrajectoryHistory]);

  // --- Effects: Backend Connection Polling ---
  useEffect(() => {
    checkBackendConnection();
    const connectionInterval = setInterval(checkBackendConnection, 30000); // Every 30s
    return () => clearInterval(connectionInterval);
  }, [checkBackendConnection]);

  // --- Effects: Load History on Connect ---
  useEffect(() => {
    if (isConnected) {
      loadDetectionHistory();
      loadTrajectoryHistory();
    }
  }, [isConnected, loadDetectionHistory, loadTrajectoryHistory]);

  // --- Backend Logs Fetch ---
  const loadLogs = useCallback(async () => {
    if (!isConnected) return;
    try {
      const response = await fetch(`${API_BASE_URL}/logs`);
      if (response.ok) {
        const data = await response.json();
        // Try to parse each log line as JSON, fallback to string
        const parsedLogs = (data.logs || []).map(line => {
          try {
            const obj = JSON.parse(line);
            if (obj.timestamp && obj.level && obj.message) return obj;
            return { timestamp: Date.now(), level: 'INFO', message: line };
          } catch {
            return { timestamp: Date.now(), level: 'INFO', message: line };
          }
        });
        setLogs(parsedLogs);
      }
    } catch (error) {
      setLogs([{ timestamp: Date.now(), level: 'ERROR', message: 'Failed to load logs: ' + error }]);
    }
  }, [isConnected]);

  // --- Effects: Load Logs on Connect ---
  useEffect(() => {
    if (isConnected) {
      loadLogs();
    }
  }, [isConnected, loadLogs]);

  // --- Current Detections Fetch ---
  const loadCurrentDetections = useCallback(async () => {
    if (!isConnected) return;
    try {
      const response = await fetch(`${API_BASE_URL}/detections/current`);
      if (response.ok) {
        const data = await response.json();
        // Extract detections array from response
        const detections = data.detections || data || [];
        setCurrentDetections(detections);
      }
    } catch (error) {
      console.error('Error loading current detections:', error);
      setCurrentDetections([]);
    }
  }, [isConnected]);

  // --- Performance Data Fetch ---
  const loadPerformanceData = useCallback(async () => {
    if (!isConnected) return;
    try {
      const response = await fetch(`${API_BASE_URL}/performance`);
      if (response.ok) {
        const perf = await response.json();
        setPerformanceData(perf);
      }
    } catch (error) {
      console.error('Error loading performance data:', error);
    }
  }, [isConnected]);

  // --- Effects: Periodic Data Refresh when Running ---
  useEffect(() => {
    if (isConnected && systemStatus === 'running') {
      loadCurrentDetections();
      loadPerformanceData();
      loadDetectionHistory(); // Also refresh history
      // Refresh every second
      const interval = setInterval(() => {
        loadCurrentDetections();
        loadPerformanceData();
        loadDetectionHistory();
      }, 1000);
      return () => clearInterval(interval);
    }
  }, [isConnected, systemStatus, loadCurrentDetections, loadPerformanceData, loadDetectionHistory]);

  // --- Effects: Periodic Cleanup ---
  useEffect(() => {
    // Clean up history every hour
    const cleanupInterval = setInterval(cleanupOldData, 60 * 60 * 1000);
    return () => {
      clearInterval(cleanupInterval);
    };
  }, [systemStatus, isConnected, cleanupOldData]);

  // --- System Start/Stop Handler ---
  const handleSystemToggle = async () => {
    try {
      const newStatus = systemStatus === 'running' ? 'stopped' : 'running';
      if (newStatus === 'running') {
        // Start streaming
        const response = await fetch(`${API_BASE_URL}/yolo/stream/start`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ video_path: 'videos/people.mp4' }) // Default video
        });
        if (response.ok) {
          setSystemStatus('running');
          setIsPlaying(true);
          setLogs(logs => [
            {
              timestamp: Date.now(),
              level: 'INFO',
              message: 'System started - Detection streaming activated'
            },
            ...logs
          ]);
        } else {
          console.error('Failed to start streaming');
        }
      } else {
        // Stop streaming
        const response = await fetch(`${API_BASE_URL}/yolo/stream/stop`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' }
        });
        if (response.ok) {
          setSystemStatus('stopped');
          setIsPlaying(false);
          setLogs(logs => [
            {
              timestamp: Date.now(),
              level: 'INFO',
              message: 'System stopped - Detection streaming deactivated'
            },
            ...logs
          ]);
        } else {
          console.error('Failed to stop streaming');
        }
      }
    } catch (error) {
      console.error('Error toggling system:', error);
      setLogs(logs => [
        {
          timestamp: Date.now(),
          level: 'ERROR',
          message: 'Error toggling system: ' + error.message
        },
        ...logs
      ]);
    }
  };

  // --- Main Render ---
  return (
    <div className="app" style={appStyle}>
      <Header 
        systemStatus={systemStatus}
        onSystemToggle={handleSystemToggle}
        isConnected={isConnected}
      />
      <div className="main-content">
        <div className="content-area">
          <div className="camera-section">
            <CameraView
              isPlaying={isPlaying}
              onPause={() => setIsPlaying(false)}
              onStep={() => {}}
              detections={currentDetections}
              // Pass setCurrentDetections for child updates
              setCurrentDetections={setCurrentDetections}
              isConnected={isConnected}
              systemStatus={systemStatus}
            />
          </div>
          <div className="right-panel">
            <DetectionPanel 
              detections={currentDetections}
              detectionHistory={detectionHistory}
              trajectoryHistory={trajectoryHistory}
              isConnected={isConnected}
            />
          </div>
        </div>
        {/* Tracking map section */}
        <div className="map-section">
          <TrackingMap
            detections={currentDetections}
            trajectoryHistory={trajectoryHistory}
            isConnected={isConnected}
            mapCenter={[48.8566, 2.3522]} // Default: Paris
            zoomLevel={13}
          />
        </div>
      </div>
      <div className="bottom-panel">
        <PerformancePanel
          fps={performanceData.fps}
          inferenceTime={performanceData.inferenceTime}
          objectCount={performanceData.objectCount}
          logs={logs}
          detectionHistory={detectionHistory}
          isConnected={isConnected}
        />
      </div>
    </div>
  );
}

export default App;