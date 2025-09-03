// App.js (AJUSTÉ POUR LA NOUVELLE CameraView)

import React, { useState, useEffect, useCallback } from 'react';
import Header from './components/Header';
import CameraView from './components/CameraView';
import DetectionPanel from './components/DetectionPanel';
import PerformancePanel from './components/PerformancePanel';
import TrackingMap from './components/TrackingMap';
import './App.css';

const API_BASE_URL = 'http://localhost:5000/api';

function App() {
  const [isConnected, setIsConnected] = useState(false);
  const [systemStatus, setSystemStatus] = useState('stopped');
  const [isDetectionStarted, setIsDetectionStarted] = useState(false);
  const [networkUrl, setNetworkUrl] = useState('http://192.168.1.16:8080/video');

  // États de données
  const [currentDetections, setCurrentDetections] = useState([]);
  const [detectionHistory, setDetectionHistory] = useState([]);
  const [roverLocation, setRoverLocation] = useState([34.0, 9.0]);
  const [logs, setLogs] = useState([]);
  const [performanceData, setPerformanceData] = useState({});
  const [generalSystemMetrics, setGeneralSystemMetrics] = useState({});
  const [modelMetricsHistory, setModelMetricsHistory] = useState([]);
  const [systemMetricsHistory, setSystemMetricsHistory] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [liveTrajectories, setLiveTrajectories] = useState({});
  // Logique de fetch et effets secondaires (inchangés, ils sont corrects)
  const fetchData = useCallback(async (endpoint) => {
    try {
      const response = await fetch(`${API_BASE_URL}/${endpoint}`);
      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
      return await response.json();
    } catch (error) {
      if (endpoint === 'health') setIsConnected(false);
      console.error(`Failed to fetch ${endpoint}:`, error);
      return null;
    }
  }, []);

  useEffect(() => {
    const fetchAllData = () => {
      fetchData('health').then(data => setIsConnected(!!data));
      fetchData('rover-location').then(data => data && setRoverLocation([data.latitude, data.longitude]));
      fetchData('system-metrics').then(data => {
        if (data) {
          const newMetrics = { ...data, timestamp: new Date().toLocaleTimeString() };
          setGeneralSystemMetrics(newMetrics);
          setSystemMetricsHistory(prev => [...prev, newMetrics].slice(-60));
        }
      });
      fetchData('detections?timeRange=24h').then(data => setDetectionHistory(data || []));
      fetchData('logs').then(data => setLogs(data?.logs || []));
      fetchData('alerts').then(data => setAlerts(data?.alerts || []));
      fetchData('trajectories').then(data => setLiveTrajectories(data || {}));
      if (isDetectionStarted) {
        fetchData('detections/current').then(data => setCurrentDetections(data?.detections || []));
        fetchData('performance').then(data => {
          if (data) {
            const newMetrics = { ...data, timestamp: new Date().toLocaleTimeString() };
            setPerformanceData(newMetrics);
            setModelMetricsHistory(prev => [...prev, newMetrics].slice(-60));
          }
        });
      }
    };
    
    fetchAllData();
    const intervalId = setInterval(fetchAllData, 2000);
    return () => clearInterval(intervalId);
  }, [fetchData, isDetectionStarted]);


  // Gestionnaire de start/stop (inchangé, il est correct)
  const handleStartStopDetection = useCallback(async () => {
    const endpoint = isDetectionStarted ? 'yolo/stream/stop' : 'yolo/stream/start';
    
    if (isDetectionStarted) {
      try {
        await fetch(`${API_BASE_URL}/${endpoint}`, { method: 'POST' });
        setIsDetectionStarted(false);
        setSystemStatus('stopped');
        setCurrentDetections([]);
      } catch (error) { console.error("Error stopping stream:", error); }
      return;
    }
    
    if (!networkUrl) {
      alert('Please enter a network URL.');
      return;
    }

    const payload = { network_url: networkUrl };

    try {
      const response = await fetch(`${API_BASE_URL}/${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (response.ok) {
        setIsDetectionStarted(true);
        setSystemStatus('running');
      } else {
        const errData = await response.json();
        alert(`Failed to start stream: ${errData.error || 'Unknown error'}`);
      }
    } catch (error) {
      alert(`Error starting stream: ${error.message}`);
    }
  }, [isDetectionStarted, networkUrl]);

  return (
    <div className="app">
      <Header 
        systemStatus={systemStatus} 
        onSystemToggle={handleStartStopDetection} 
        isConnected={isConnected} 
        isDetectionStarted={isDetectionStarted} 
      />
      <div className="main-content">
        <div className="content-area">
          <div className="camera-section">
            <CameraView
              isConnected={isConnected}
              isDetectionStarted={isDetectionStarted}
              onStartStopDetection={handleStartStopDetection}
              networkUrl={networkUrl}
              setNetworkUrl={setNetworkUrl}
              systemStatus={systemStatus}
              detections={currentDetections}

            />
          </div>
          <div className="right-panel">
            <DetectionPanel 
              detections={currentDetections} 
              detectionHistory={detectionHistory} 
              isConnected={isConnected} 
            />
          </div>
        </div>
        <div className="map-section">
          <TrackingMap
            detections={currentDetections}
            trajectoryHistory={liveTrajectories}
            isConnected={isConnected}
            mapCenter={roverLocation}
            zoomLevel={15}
            alerts={alerts}
          />
        </div>
      </div>
      <div className="bottom-panel">
        <PerformancePanel 
          modelMetrics={performanceData} 
          modelMetricsHistory={modelMetricsHistory} 
          systemMetrics={generalSystemMetrics} 
          systemMetricsHistory={systemMetricsHistory} 
          logs={logs} 
          detectionHistory={detectionHistory}
          isConnected={isConnected}
          isDetectionStarted={isDetectionStarted}
        />
      </div>
    </div>
  );
}

export default App;