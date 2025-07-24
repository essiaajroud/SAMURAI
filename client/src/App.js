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
  const [isDetectionStarted, setIsDetectionStarted] = useState(false);
  const [sourceType, setSourceType] = useState('video'); // Default to video
  const [networkUrl, setNetworkUrl] = useState('http://192.168.1.16:8080/video'); // Format pour IP Webcam

  const [performanceData, setPerformanceData] = useState({});
  const [systemMetricsHistory, setSystemMetricsHistory] = useState([]);
  const [modelMetricsHistory, setModelMetricsHistory] = useState([]);

  const [detectionHistory, setDetectionHistory] = useState([]); // Detection history
  const [trajectoryHistory, setTrajectoryHistory] = useState({}); // Trajectory history
  const [currentDetections, setCurrentDetections] = useState([]); // Current detections
  const [logs, setLogs] = useState([]); // System logs
  const [videos, setVideos] = useState([]); // Available videos
  const [selectedVideo, setSelectedVideo] = useState('war.mp4'); // Selected video par défaut

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
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 2000); // Timeout après 2 secondes
      
      const response = await fetch(`${API_BASE_URL}/health`, {
        signal: controller.signal
      });
      
      clearTimeout(timeoutId);
      
      if (response.ok) {
        setIsConnected(true);
        console.log('Backend connected successfully');
      } else {
        setIsConnected(false);
        console.warn('Backend health check failed');
      }
    } catch (error) {
      setIsConnected(false);
      if (error.name === 'AbortError') {
        console.warn('Backend connection timeout');
      } else {
        console.error('Backend connection error:', error);
      }
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
      // Retourner un tableau vide en cas d'erreur pour éviter les erreurs d'affichage
      setDetectionHistory([]);
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
      // Retourner un objet vide en cas d'erreur pour éviter les erreurs d'affichage
      setTrajectoryHistory({});
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
      // Ne pas bloquer l'interface en cas d'erreur
    }
  }, [isConnected, loadDetectionHistory, loadTrajectoryHistory]);

  // --- Available Videos Fetch ---
  const fetchVideos = useCallback(async () => {
    if (!isConnected) return;
    try {
      const response = await fetch(`${API_BASE_URL}/yolo/videos`);
      if (response.ok) {
        const data = await response.json();
        if (data.videos) {
          const videoNames = data.videos.map(v => v.replace(/^videos[/\\]/, ''));
          setVideos(videoNames);
          if (videoNames.length > 0) {
            setSelectedVideo(videoNames[0]); // Select first video by default
          }
        }
      }
    } catch (error) {
      console.error('Error loading videos:', error);
      // Définir une liste vide de vidéos en cas d'erreur
      setVideos([]);
    }
  }, [isConnected]);

  // --- Effects: Load Videos on Connect ---
  useEffect(() => {
    if (isConnected) {
      fetchVideos();
    }
  }, [isConnected, fetchVideos]);

  // --- Effects: Backend Connection Polling ---
  useEffect(() => {
    checkBackendConnection();
    // Vérifier la connexion plus fréquemment (toutes les 10 secondes)
    const connectionInterval = setInterval(checkBackendConnection, 10000);
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
          // Enhanced log parsing logic
          line = line.trim();
          if (!line) return null;

          // Regex for Werkzeug access logs (e.g., "127.0.0.1 - - [...] GET /api/health ...")
          const werkzeugRegex = /"(\w+)\s(.*?)\s(HTTP.*?)"\s(\d+)/;
          const werkzeugMatch = line.match(werkzeugRegex);
          
          // Ne pas inclure les logs des statuts des APIs
          if (werkzeugMatch) {
            // Retourner null pour filtrer ce log
            return null;
          }

          // Regex for my custom logs (e.g., "✅ YOLO detector loaded successfully.")
          const customLogRegex = /(✅|▶️|🛑|❌|⚠️)\s(.*)/;
          const customMatch = line.match(customLogRegex);
          if (customMatch) {
            // Filtrer les logs liés à l'output de terminal
            const message = customMatch[2];
            if (message.includes("GET /api/") ||
                message.includes("Status 200") ||
                message.includes("Backend connecté") ||
                message.includes("Streaming started") ||
                message.includes("Streaming stopped") ||
                message.includes("Détections trouvées")) {
              return null;
            }
            
            const levelMap = { '✅': 'SUCCESS', '▶️': 'INFO', '🛑': 'INFO', '❌': 'ERROR', '⚠️': 'WARNING' };
            return {
              timestamp: new Date().toISOString(),
              level: levelMap[customMatch[1]] || 'INFO',
              message: message
            };
          }

          // Fallback for generic lines
          // Filtrer les lignes génériques qui contiennent des informations d'API ou de terminal
          if (line.includes("GET /api/") ||
              line.includes("Status 200") ||
              line.includes("Backend connecté") ||
              line.includes("Streaming started") ||
              line.includes("Streaming stopped") ||
              line.includes("Détections trouvées") ||
              line.includes("Detected change in") ||
              line.includes("reloading")) {
            return null;
          }
          
          return {
            timestamp: new Date().toISOString(),
            level: 'INFO',
            message: line
          };
        }).filter(Boolean); // Remove any null entries from empty lines

        setLogs(parsedLogs.reverse()); // Show newest first
      }
    } catch (error) {
      // Ajouter un message d'erreur aux logs mais ne pas bloquer l'interface
      setLogs([
        { timestamp: Date.now(), level: 'ERROR', message: 'Failed to load logs: ' + error },
        { timestamp: Date.now(), level: 'INFO', message: 'Interface running in offline mode - backend not available' }
      ]);
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
      // Définir une liste vide de détections en cas d'erreur
      setCurrentDetections([]);
    }
  }, [isConnected]);

  // --- Performance Data Fetch ---
  const loadPerformanceData = useCallback(async () => {
    if (!isConnected) return;
    try {
      const response = await fetch(`${API_BASE_URL}/performance`);
      if (response.ok) {
        const newMetrics = await response.json();
        newMetrics.timestamp = new Date().toLocaleTimeString();
        setPerformanceData(newMetrics);
        setModelMetricsHistory(prevHistory => {
          const newHistory = [...prevHistory, newMetrics];
          return newHistory.slice(-60); // Keep last 60 points
        });
      }
    } catch (error) {
      console.error('Error loading performance data:', error);
      // Initialiser les données de performance avec des valeurs par défaut
      setPerformanceData({
        fps: 0,
        inferenceTime: 0,
        objectCount: 0,
        detectionRate: 0,
        precision: 0,
        recall: 0,
        f1Score: 0,
        timestamp: new Date().toLocaleTimeString()
      });
    }
  }, [isConnected]);

  // --- System Metrics Fetch ---
  const loadSystemMetrics = useCallback(async () => {
    if (!isConnected) return;
    try {
      const response = await fetch(`${API_BASE_URL}/system-metrics`);
      if (response.ok) {
        const newMetrics = await response.json();
        newMetrics.timestamp = new Date().toLocaleTimeString(); // Add timestamp for chart labels
        setSystemMetricsHistory(prevHistory => {
          const newHistory = [...prevHistory, newMetrics];
          // Keep the last 60 data points
          return newHistory.slice(-60);
        });
      }
    } catch (error) {
      console.error('Error loading system metrics:', error);
      // Initialiser les métriques système avec des valeurs par défaut
      const defaultMetrics = {
        cpu_percent: 0,
        ram_percent: 0,
        disk_percent: 0,
        timestamp: new Date().toLocaleTimeString()
      };
      setSystemMetricsHistory(prevHistory => {
        const newHistory = [...prevHistory, defaultMetrics];
        return newHistory.slice(-60);
      });
    }
  }, [isConnected]);

  // --- Effects: Periodic Data Refresh when Running ---
  useEffect(() => {
    if (isConnected && systemStatus === 'running') {
      loadCurrentDetections();
      loadPerformanceData();
      loadDetectionHistory(); // Also refresh history
      // Refresh every second
      // Récupérer les détections plus fréquemment pour une meilleure réactivité
      const detectionInterval = setInterval(() => {
        loadCurrentDetections();
      }, 200); // 5 fois par seconde
      
      // Récupérer les autres données moins fréquemment
      const metricsInterval = setInterval(() => {
        loadPerformanceData();
        loadDetectionHistory();
        loadSystemMetrics();
      }, 1000);
      
      return () => {
        clearInterval(detectionInterval);
        clearInterval(metricsInterval);
      };
    }
  }, [isConnected, systemStatus, loadCurrentDetections, loadPerformanceData, loadDetectionHistory, loadSystemMetrics]);

  // --- Effects: Periodic Cleanup ---
  useEffect(() => {
    // Clean up history every hour
    const cleanupInterval = setInterval(cleanupOldData, 60 * 60 * 1000);
    return () => {
      clearInterval(cleanupInterval);
    };
  }, [systemStatus, isConnected, cleanupOldData]);

  // --- Unified Stream Control Handler ---
  const handleStartStopDetection = useCallback(async () => {
    // Stop logic
    if (isDetectionStarted) {
      try {
        await fetch(`${API_BASE_URL}/yolo/stream/stop`, { method: 'POST' });
        setIsDetectionStarted(false);
        setIsPlaying(false);
        setSystemStatus('stopped');
        setCurrentDetections([]);
        return { success: true };
      } catch (error) {
        console.error('Error stopping detection:', error);
        return { error: `Erreur lors de l'arrêt de la détection: ${error.message}` };
      }
    }

    // Start logic
    const isReadyToStart = (sourceType === 'video' && selectedVideo) || (sourceType === 'network' && networkUrl);
    if (!isReadyToStart) {
      console.warn('Cannot start: No video selected or network URL provided.');
      return { error: 'Aucune vidéo sélectionnée ou URL réseau fournie.' };
    }

    try {
      const payload = sourceType === 'video'
        ? { video_path: `videos/${selectedVideo}` }
        : { network_url: networkUrl };

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
        const errorData = await response.json();
        console.error('Failed to start streaming:', errorData.error);
        return {
          error: errorData.error || 'Échec du démarrage du flux vidéo',
          details: errorData.last_logs
        };
      }
    } catch (error) {
      console.error('Error starting detection:', error);
      return { error: `Erreur lors du démarrage de la détection: ${error.message}` };
    }
  }, [isDetectionStarted, sourceType, selectedVideo, networkUrl, setCurrentDetections]);

  // --- Main Render ---
  return (
    <div className="app" style={appStyle}>
      <Header
        systemStatus={systemStatus}
        onSystemToggle={handleStartStopDetection} // Use the new unified handler
        isConnected={isConnected}
        isDetectionStarted={isDetectionStarted}
      />
      <div className="main-content">
        <div className="content-area">
          <div className="camera-section">
            <CameraView
              isPlaying={isPlaying}
              onPause={() => setIsPlaying(false)}
              detections={currentDetections}
              isConnected={isConnected}
              systemStatus={systemStatus}
              videos={videos}
              selectedVideo={selectedVideo}
              setSelectedVideo={setSelectedVideo}
              isDetectionStarted={isDetectionStarted}
              onStartStopDetection={handleStartStopDetection} // Pass handler down
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
            mapCenter={[34.0, 9.0]} // Correction: Tunisie
            zoomLevel={7} // Zoom adapté pour voir une plus grande partie du pays
          />
        </div>
      </div>
      <div className="bottom-panel">
        <PerformancePanel
          modelMetrics={performanceData}
          modelMetricsHistory={modelMetricsHistory}
          systemMetrics={systemMetricsHistory.length > 0 ? systemMetricsHistory[systemMetricsHistory.length - 1] : {}}
          systemMetricsHistory={systemMetricsHistory}
          logs={logs}
          detectionHistory={detectionHistory}
          isConnected={isConnected}
        />
      </div>
    </div>
  );
}

export default App;