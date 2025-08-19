// App.js (VERSION FINALE ET NETTOYÉE)

import React, { useState, useEffect, useCallback } from 'react';
import Header from './components/Header';
import CameraView from './components/CameraView';
import DetectionPanel from './components/DetectionPanel';
import PerformancePanel from './components/PerformancePanel';
import TrackingMap from './components/TrackingMap';
import './App.css';

const API_BASE_URL = 'http://localhost:5000/api';

function App() {
  // --- GESTION DES ÉTATS ---
  const [systemStatus, setSystemStatus] = useState('stopped');
  const [isPlaying, setIsPlaying] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const [isDetectionStarted, setIsDetectionStarted] = useState(false);
  const [sourceType, setSourceType] = useState('video');
  const [networkUrl, setNetworkUrl] = useState('http://192.168.1.16:8080/video');
  
  const [performanceData, setPerformanceData] = useState({
    fps: 0, inferenceTime: 0, cpuUsage: 0, gpuUsage: 0, gpuMemoryUsage: 0,
    memoryUsage: 0, objectCount: 0, totalTracks: 0, active_trajectories: 0,
    objectsByClass: {}, timestamp: new Date().toLocaleTimeString()
  });
  const [generalSystemMetrics, setGeneralSystemMetrics] = useState({});
  const [modelMetricsHistory, setModelMetricsHistory] = useState([]);
  const [systemMetricsHistory, setSystemMetricsHistory] = useState([]);
  const [detectionHistory, setDetectionHistory] = useState([]);
  const [trajectoryHistory, setTrajectoryHistory] = useState({});
  const [currentDetections, setCurrentDetections] = useState([]);
  const [logs, setLogs] = useState([]);
  const [videos, setVideos] = useState([]);
  const [selectedVideo, setSelectedVideo] = useState('');

  // --- FONCTIONS DE RÉCUPÉRATION DES DONNÉES (useCallback) ---

  const checkBackendConnection = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/health`);
      setIsConnected(response.ok);
    } catch (error) { setIsConnected(false); }
  }, []);
  
  const loadCurrentDetections = useCallback(async () => {
    if (!isConnected) return;
    try {
      const response = await fetch(`${API_BASE_URL}/detections/current`);
      if (response.ok) setCurrentDetections((await response.json()).detections || []);
    } catch (error) { console.error('Error loading current detections:', error); }
  }, [isConnected]);

  const loadPerformanceData = useCallback(async () => {
    if (!isConnected) return;
    try {
      const response = await fetch(`${API_BASE_URL}/performance`);
      if (!response.ok) throw new Error(`Server responded with status: ${response.status}`);
      const newMetrics = await response.json();
      newMetrics.timestamp = new Date().toLocaleTimeString();
      setPerformanceData(newMetrics);
      setModelMetricsHistory(prev => [...prev, newMetrics].slice(-60));
    } catch (error) { console.error('CRITICAL FETCH ERROR (performance):', error); }
  }, [isConnected]);

  const loadGeneralSystemMetrics = useCallback(async () => {
    if (!isConnected) return;
    try {
      const response = await fetch(`${API_BASE_URL}/system-metrics`);
      if (!response.ok) throw new Error(`Server responded with status: ${response.status}`);
      const newMetrics = await response.json();
      newMetrics.timestamp = new Date().toLocaleTimeString();
      setGeneralSystemMetrics(newMetrics);
      setSystemMetricsHistory(prev => [...prev, newMetrics].slice(-60));
    } catch (error) { console.error('CRITICAL FETCH ERROR (system):', error); }
  }, [isConnected]);

  const loadDetectionHistory = useCallback(async () => {
    if (!isConnected) return;
    try {
      const response = await fetch(`${API_BASE_URL}/detections?limit=1000`);
      if (response.ok) setDetectionHistory(await response.json());
    } catch (error) { console.error('Error loading detection history:', error); }
  }, [isConnected]);

  const loadTrajectoryHistory = useCallback(async () => {
    if (!isConnected) return;
    try {
      const response = await fetch(`${API_BASE_URL}/trajectories`);
      if (response.ok) setTrajectoryHistory(await response.json());
    } catch (error) { console.error('Error loading trajectory history:', error); }
  }, [isConnected]);

  const loadLogs = useCallback(async () => {
    if (!isConnected) return;
    try {
      const response = await fetch(`${API_BASE_URL}/logs`);
      if (response.ok) setLogs((await response.json()).logs || []);
    } catch (error) { console.error('Error loading logs:', error); }
  }, [isConnected]);

  const fetchVideos = useCallback(async () => {
    if (!isConnected) return;
    try {
      const response = await fetch(`${API_BASE_URL}/yolo/videos`);
      if (response.ok) {
        const data = await response.json();
        const videoNames = data.videos.map(v => v.replace(/^videos[/\\]/, ''));
        setVideos(videoNames);
        if (videoNames.length > 0 && !selectedVideo) setSelectedVideo(videoNames[0]);
      }
    } catch (error) { console.error('Error loading videos:', error); }
  }, [isConnected, selectedVideo]);

  const [roverLocation, setRoverLocation] = useState([34.0, 9.0]);
   const loadRoverLocation = useCallback(async () => {
    if (!isConnected) return;
    try {
      const response = await fetch(`${API_BASE_URL}/rover-location`);
      if (response.ok) {
        const data = await response.json();
        setRoverLocation([data.latitude, data.longitude]);
      }
    } catch (error) {
      console.error('Error loading rover location:', error);
    }
  }, [isConnected]);

  // --- GESTION DES EFFETS SECONDAIRES (useEffect) ---

  // Connexion au backend
  useEffect(() => {
    checkBackendConnection();
    const interval = setInterval(checkBackendConnection, 10000);
    return () => clearInterval(interval);
  }, [checkBackendConnection]);

  // Chargement des données initiales une fois connecté
  useEffect(() => {
    if (isConnected) {
      fetchVideos();
      loadDetectionHistory();
      loadTrajectoryHistory();
      loadLogs();
      loadRoverLocation();
    }
  }, [isConnected, fetchVideos, loadDetectionHistory, loadTrajectoryHistory, loadLogs, loadRoverLocation]);

  // Intervalles pour les données temps réel
  useEffect(() => {
    let detectionIntervalId = null;
    let metricsIntervalId = null;
    let systemMetricsIntervalId = null;

    if (isConnected) {
      loadGeneralSystemMetrics();
      systemMetricsIntervalId = setInterval(loadGeneralSystemMetrics, 2000);

      if (systemStatus === 'running') {
        loadCurrentDetections();
        loadPerformanceData();
        detectionIntervalId = setInterval(loadCurrentDetections, 200);
        metricsIntervalId = setInterval(loadPerformanceData, 1000);
      }
    }
    return () => {
      clearInterval(detectionIntervalId);
      clearInterval(metricsIntervalId);
      clearInterval(systemMetricsIntervalId);
    };
  }, [isConnected, systemStatus, loadCurrentDetections, loadPerformanceData, loadGeneralSystemMetrics]);

  // Handler pour démarrer/arrêter
  const handleStartStopDetection = useCallback(async () => {
    if (isDetectionStarted) {
      try {
        await fetch(`${API_BASE_URL}/yolo/stream/stop`, { method: 'POST' });
        setIsDetectionStarted(false);
        setIsPlaying(false);
        setSystemStatus('stopped');
        return { success: true };
      } catch (error) { return { error: `Error stopping: ${error.message}` }; }
    }
    const isReady = (sourceType === 'video' && selectedVideo) || (sourceType === 'network' && networkUrl);
    if (!isReady) return { error: 'No video source selected.' };
    try {
      const payload = sourceType === 'video' ? { video_path: `videos/${selectedVideo}` } : { network_url: networkUrl };
      const response = await fetch(`${API_BASE_URL}/yolo/stream/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (response.ok) {
        setIsDetectionStarted(true);
        setIsPlaying(true);
        setSystemStatus('running');
        return { success: true };
      } else {
        return { error: (await response.json()).error || 'Startup failure' };
      }
    } catch (error) { return { error: `Error starting: ${error.message}` }; }
  }, [isDetectionStarted, sourceType, selectedVideo, networkUrl]);

  // --- RENDER ---
  return (
    <div className="app" style={{ /* ... */ }}>
      <Header {...{ systemStatus, onSystemToggle: handleStartStopDetection, isConnected, isDetectionStarted }} />
      <div className="main-content">
        <div className="content-area">
          <div className="camera-section">
            <CameraView
                  isPlaying={isPlaying}
                  setIsPlaying={setIsPlaying} 
                  onPause={() => setIsPlaying(false)} 
                  detections={currentDetections}
                  isConnected={isConnected}
                  systemStatus={systemStatus}
                  videos={videos}
                  selectedVideo={selectedVideo}
                  setSelectedVideo={setSelectedVideo}
                  isDetectionStarted={isDetectionStarted}
                  onStartStopDetection={handleStartStopDetection}
                  sourceType={sourceType}
                  setSourceType={setSourceType}
                  networkUrl={networkUrl}
                  setNetworkUrl={setNetworkUrl}
                />
          </div>
          <div className="right-panel">
            <DetectionPanel {...{ detections: currentDetections, detectionHistory, trajectoryHistory, isConnected }} />
          </div>
        </div>
        <div className="map-section">
          <TrackingMap
            detections={currentDetections}
            trajectoryHistory={trajectoryHistory}
            isConnected={isConnected}
            mapCenter={roverLocation} // <--- UTILISER L'ÉTAT DYNAMIQUE
            zoomLevel={7}
          />
        </div>
      </div>
      <div className="bottom-panel">
        <PerformancePanel {...{ modelMetrics: performanceData, modelMetricsHistory, systemMetrics: generalSystemMetrics, systemMetricsHistory, logs, detectionHistory, isConnected }} 
        isConnected={isConnected}
        isDetectionStarted={isDetectionStarted}
        sourceType={sourceType}/>
      </div>
    </div>
  );
}

export default App;