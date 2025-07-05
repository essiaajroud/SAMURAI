import React, { useState, useEffect, useCallback } from 'react';
import Header from './components/Header';
import CameraView from './components/CameraView';
import DetectionPanel from './components/DetectionPanel';
import PerformancePanel from './components/PerformancePanel';
import './App.css';

// Configuration de l'API
const API_BASE_URL = 'http://localhost:5000/api';

function App() {
  const [systemStatus, setSystemStatus] = useState('stopped');
  const [isPlaying, setIsPlaying] = useState(false);
  const [isConnected, setIsConnected] = useState(false);

  const [performanceData, setPerformanceData] = useState({
    fps: 30,
    inferenceTime: 33,
    objectCount: 5
  });

  // État pour l'historique des détections
  const [detectionHistory, setDetectionHistory] = useState([]);
  const [trajectoryHistory, setTrajectoryHistory] = useState({});
  const [currentDetections, setCurrentDetections] = useState([]);

  const [logs, setLogs] = useState([]);

  // Styles inline pour l'image de fond
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

  // Fonctions API
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

  // Supprimez ce hook inutilisé :
  // const saveDetectionToBackend = useCallback(async (detection) => {
  //   ...code...
  // }, [isConnected]);

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

  // Supprimez ces deux hooks inutilisés :
  // const addToDetectionHistory = useCallback(async (detections) => {
  //   ...code...
  // }, [saveDetectionToBackend]);

  // const updateTrajectories = useCallback((detections) => {
  //   ...code...
  // }, [trajectoryHistory]);

  // Vérifier la connexion au démarrage
  useEffect(() => {
    checkBackendConnection();
    
    // Vérifier la connexion toutes les 30 secondes
    const connectionInterval = setInterval(checkBackendConnection, 30000);
    
    return () => clearInterval(connectionInterval);
  }, [checkBackendConnection]);

  // Charger l'historique au démarrage et quand la connexion est établie
  useEffect(() => {
    if (isConnected) {
      loadDetectionHistory();
      loadTrajectoryHistory();
    }
  }, [isConnected, loadDetectionHistory, loadTrajectoryHistory]);

  // Charger les logs du backend
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

  // Charger les logs au démarrage et quand la connexion est établie
  useEffect(() => {
    if (isConnected) {
      loadLogs();
    }
  }, [isConnected, loadLogs]);

  // Nouvelle fonction pour charger les détections courantes depuis le backend
  const loadCurrentDetections = useCallback(async () => {
    if (!isConnected) return;
    try {
      const response = await fetch(`${API_BASE_URL}/detections/current`);
      if (response.ok) {
        const detections = await response.json();
        setCurrentDetections(detections);
      }
    } catch (error) {
      console.error('Erreur lors du chargement des détections courantes:', error);
    }
  }, [isConnected]);

  // Nouvelle fonction pour charger les performances depuis le backend
  const loadPerformanceData = useCallback(async () => {
    if (!isConnected) return;
    try {
      const response = await fetch(`${API_BASE_URL}/performance`);
      if (response.ok) {
        const perf = await response.json();
        setPerformanceData(perf);
      }
    } catch (error) {
      console.error('Erreur lors du chargement des performances:', error);
    }
  }, [isConnected]);

  // Charger les données courantes et performances au démarrage et périodiquement
  useEffect(() => {
    if (isConnected && systemStatus === 'running') {
      loadCurrentDetections();
      loadPerformanceData();
      // Rafraîchir toutes les secondes
      const interval = setInterval(() => {
        loadCurrentDetections();
        loadPerformanceData();
      }, 1000);
      return () => clearInterval(interval);
    }
  }, [isConnected, systemStatus, loadCurrentDetections, loadPerformanceData]);

  // Supprimer la simulation locale des détections et performances
  useEffect(() => {
    // Nettoyer l'historique toutes les heures
    const cleanupInterval = setInterval(cleanupOldData, 60 * 60 * 1000);
    return () => {
      clearInterval(cleanupInterval);
    };
  }, [systemStatus, isConnected, cleanupOldData]);

  const handleSystemToggle = () => {
    setSystemStatus(prev => {
      const newStatus = prev === 'running' ? 'stopped' : 'running';
      setLogs(logs => [
        {
          timestamp: Date.now(),
          level: 'INFO',
          message: newStatus === 'running' ? 'System started' : 'System stopped'
        },
        ...logs
      ]);
      return newStatus;
    });
    setIsPlaying(prev => !prev);
  };

  // Convertir les trajectoires en format attendu par CameraView
  const trajectories = Object.values(trajectoryHistory).map(trajectory => ({
    id: trajectory.id,
    points: trajectory.points.map(point => ({ x: point.x, y: point.y }))
  }));

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
              trajectories={trajectories}
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