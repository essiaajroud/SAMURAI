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
  // --- ÉTATS ---
  const [isConnected, setIsConnected] = useState(false);
  const [systemStatus, setSystemStatus] = useState('stopped');
  const [isPlaying, setIsPlaying] = useState(false);
  const [isDetectionStarted, setIsDetectionStarted] = useState(false);
  const [sourceType, setSourceType] = useState('video');
  const [networkUrl, setNetworkUrl] = useState('http://192.168.1.16:8080/video');
  const [videos, setVideos] = useState([]);
  const [selectedVideo, setSelectedVideo] = useState('');
  const [alerts, setAlerts] = useState([]);
  // Données dynamiques
  const [currentDetections, setCurrentDetections] = useState([]);
  const [detectionHistory, setDetectionHistory] = useState([]);
  const [roverLocation, setRoverLocation] = useState([34.0, 9.0]);
  const [logs, setLogs] = useState([]);

  // Données de performance
  const [performanceData, setPerformanceData] = useState({});
  const [generalSystemMetrics, setGeneralSystemMetrics] = useState({});
  const [modelMetricsHistory, setModelMetricsHistory] = useState([]);
  const [systemMetricsHistory, setSystemMetricsHistory] = useState([]);

  // --- FONCTION DE FETCH GÉNÉRIQUE ---
  const fetchData = useCallback(async (endpoint) => {
    try {
      const response = await fetch(`${API_BASE_URL}/${endpoint}`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      return await response.json();
    } catch (error) {
      if (endpoint === 'health') setIsConnected(false);
      console.error(`Failed to fetch ${endpoint}:`, error);
      return null;
    }
  }, []);

  // --- EFFETS SECONDAIRES ---

  // Effet principal pour gérer tous les rafraîchissements de données via un seul intervalle
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
      // Ces données ne sont pertinentes que si la détection est active
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
    
    fetchAllData(); // Appel initial
    const intervalId = setInterval(fetchAllData, 2000); // Rafraîchit tout toutes les 2 secondes

    return () => clearInterval(intervalId); // Nettoyage
  }, [fetchData, isDetectionStarted]);

  // Chargement des données statiques (liste des vidéos) une seule fois
  useEffect(() => {
    if (isConnected) {
      fetchData('yolo/videos').then(data => {
        if (data?.videos) {
          const videoNames = data.videos.map(v => v.replace(/^videos[/\\]/, ''));
          setVideos(videoNames);
          if (videoNames.length > 0 && !selectedVideo) {
            setSelectedVideo(videoNames[0]);
          }
        }
      });
    }
  }, [isConnected, fetchData, selectedVideo]);


  // --- GESTIONNAIRE D'ÉVÉNEMENTS ---
  const handleStartStopDetection = useCallback(async () => {
    const endpoint = isDetectionStarted ? 'yolo/stream/stop' : 'yolo/stream/start';
    
    if (isDetectionStarted) {
      try {
        await fetch(`${API_BASE_URL}/${endpoint}`, { method: 'POST' });
        setIsDetectionStarted(false);
        setIsPlaying(false);
        setSystemStatus('stopped');
        setCurrentDetections([]);
      } catch (error) { console.error("Error stopping stream:", error); }
      return;
    }
    
    const isReady = (sourceType === 'video' && selectedVideo) || (sourceType === 'network' && networkUrl);
    if (!isReady) {
      alert('Please select a video or enter a network URL.');
      return;
    }

    const payload = sourceType === 'video' ? { video_path: `videos/${selectedVideo}` } : { network_url: networkUrl };

    try {
      const response = await fetch(`${API_BASE_URL}/${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (response.ok) {
        setIsDetectionStarted(true);
        setIsPlaying(true);
        setSystemStatus('running');
      } else {
        const errData = await response.json();
        alert(`Failed to start stream: ${errData.error || 'Unknown error'}`);
      }
    } catch (error) {
      alert(`Error starting stream: ${error.message}`);
    }
  }, [isDetectionStarted, sourceType, selectedVideo, networkUrl]);

  // --- RENDER ---
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
              isPlaying={isPlaying}
              setIsPlaying={setIsPlaying}
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