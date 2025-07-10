import React, { useRef, useEffect, useState, useCallback } from 'react';
import './CameraView.css';
import PropTypes from 'prop-types';

const API_BASE_URL = 'http://localhost:5000/api';

// Hook personnalisé pour récupérer la liste des vidéos
function useVideos() {
  const [videos, setVideos] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchVideos = async () => {
      setLoading(true);
      setError('');
      try {
        const res = await fetch(`${API_BASE_URL}/yolo/videos`);
        const data = await res.json();
        if (data.videos) {
          const videoNames = data.videos.map(v => {
            // Supprimer le préfixe 'videos/' ou 'videos\' selon le système d'exploitation
            return v.replace(/^videos[/\\]/, '');
          });
          setVideos(videoNames);
        }
      } catch (err) {
        setError('Error loading videos');
      }
      setLoading(false);
    };
    fetchVideos();
  }, []);

  return { videos, loading, error };
}

// Hook personnalisé pour dessiner les détections sur le canvas
function useDrawDetections(canvasRef, detections) {
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    // S'assurer que detections est un tableau
    const detectionsArray = Array.isArray(detections) ? detections : [];
    detectionsArray.forEach(detection => {
      const { x, y, width, height, label, confidence } = detection;
      ctx.strokeStyle = '#00ff00';
      ctx.lineWidth = 2;
      ctx.strokeRect(x, y, width, height);
      ctx.fillStyle = '#00ff00';
      ctx.font = '14px Arial';
      ctx.fillText(`${label} (${(confidence * 100).toFixed(1)}%)`, x, y - 5);
    });
  }, [canvasRef, detections]);
}

const CameraView = ({ 
  isPlaying, 
  onPause, 
  detections = [], 
  isConnected,
  systemStatus,
  setCurrentDetections
}) => {
  const canvasRef = useRef(null);

  // Utilisation du hook pour la liste des vidéos
  const { videos, loading: videosLoading, error: videosError } = useVideos();
  const [selectedVideo, setSelectedVideo] = useState('');
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState('');
  const [isDetectionStarted, setIsDetectionStarted] = useState(false);

  // Sélectionner la première vidéo disponible par défaut
  useEffect(() => {
    if (videos.length > 0 && !selectedVideo) {
      setSelectedVideo(videos[0]);
    }
  }, [videos, selectedVideo]);

  // Utilisation du hook pour dessiner les détections
  useDrawDetections(canvasRef, detections || []);

  // Lancer/Arrêter la détection sur la vidéo sélectionnée
  const handleStartDetection = useCallback(async () => {
    if (!selectedVideo) return;
    setLoading(true);
    setStatus('');
    
    try {
      if (!isDetectionStarted) {
        // Démarrer la détection
        const res = await fetch(`${API_BASE_URL}/yolo/stream/start`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ video_path: `videos/${selectedVideo}` })
        });
        const data = await res.json();
        if (res.ok) {
          setStatus('Detection started!');
          setIsDetectionStarted(true);
        } else {
          setStatus(data.error || 'Error starting detection');
        }
      } else {
        // Arrêter la détection
        const res = await fetch(`${API_BASE_URL}/yolo/stream/stop`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' }
        });
        if (res.ok) {
          setStatus('Detection stopped!');
          setIsDetectionStarted(false);
        } else {
          setStatus('Error stopping detection');
        }
      }
    } catch (err) {
      setStatus('Error managing detection');
    }
    setLoading(false);
  }, [selectedVideo, isDetectionStarted]);

  useEffect(() => {
    if (isConnected && systemStatus === 'running') {
      const interval = setInterval(async () => {
        try {
          const res = await fetch(`${API_BASE_URL}/detections/current`);
          if (res.ok) {
            const data = await res.json();
            // Extraire le tableau de détections de la réponse
            const detections = data.detections || data || [];
            setCurrentDetections(detections);
          }
        } catch (error) {
          console.error('Error retrieving detections:', error);
        }
      }, 1000);
      return () => clearInterval(interval);
    }
  }, [isConnected, systemStatus, setCurrentDetections]);

  return (
    <div className="camera-view">
      <div style={{ marginBottom: 16, display: 'flex', alignItems: 'center', gap: 0 }}>
        <label htmlFor="video-select" style={{ marginLeft: 18, marginRight: 18 }}>Video: </label>
        <select
          id="video-select"
          value={selectedVideo}
          onChange={e => setSelectedVideo(e.target.value)}
          style={{ marginRight: 0 }}
          aria-label="Video selection"
        >
          {videos.map(video => (
            <option key={video} value={video}>{video}</option>
          ))}
        </select>
        <button
          className={`control-button ${isDetectionStarted ? 'pause' : 'play'}`}
          onClick={handleStartDetection}
          disabled={loading || !selectedVideo}
          aria-busy={loading}
          style={{ marginLeft: 'auto', marginRight: 18 }}
        >
          {loading ? 'Loading...' : (isDetectionStarted ? '⏸️ Stop Detection' : '▶️ Start Detection')}
        </button>
        {videosLoading && <span style={{ marginLeft: 12 }}>Loading videos...</span>}
        {videosError && <span style={{ marginLeft: 12, color: 'red' }}>{videosError}</span>}
        {status && <span style={{ marginLeft: 12, color: '#00ff00' }}>{status}</span>}
      </div>
      <div className="video-container">
        {isDetectionStarted && (
          <img
            className="video-feed"
            src={`http://localhost:5000/video_feed?video_path=videos/${selectedVideo}`}
            alt="Video stream"
            style={{ width: '100%', height: '100%', objectFit: 'cover', borderRadius: 8 }}
          />
        )}
        <canvas
          ref={canvasRef}
          className="detection-overlay"
        />
      </div>
      <div className="video-controls">
        <button 
          className={`control-button ${isPlaying ? 'pause' : 'play'}`}
          onClick={onPause}
          disabled={!isDetectionStarted}
        >
          {isPlaying ? '⏸️ Pause' : '▶️ Play'}
        </button>
      </div>
    </div>
  );
};

CameraView.propTypes = {
  isPlaying: PropTypes.bool.isRequired,
  onPause: PropTypes.func.isRequired,
  onStep: PropTypes.func.isRequired,
  detections: PropTypes.array,
  isConnected: PropTypes.bool.isRequired,
  systemStatus: PropTypes.string.isRequired,
  setCurrentDetections: PropTypes.func.isRequired
};

export default CameraView;