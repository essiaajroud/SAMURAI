// CameraView.js - Displays video feed and overlays detections
// Handles video selection, detection start/stop, and drawing overlays
import React, { useRef, useEffect, useState, useCallback } from 'react';
import './CameraView.css';
import PropTypes from 'prop-types';

const API_BASE_URL = 'http://localhost:5000/api';

// Custom hook to fetch available videos from backend
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
          // Remove 'videos/' or 'videos\' prefix for display
          const videoNames = data.videos.map(v => v.replace(/^videos[/\\]/, ''));
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

// Custom hook to draw detections on the canvas overlay
function useDrawDetections(canvasRef, detections) {
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    // Draw each detection as a rectangle and label
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

// Main CameraView component
const CameraView = ({ 
  isPlaying, 
  onPause, 
  detections = [], 
  isConnected,
  systemStatus,
  setCurrentDetections
}) => {
  const canvasRef = useRef(null);

  // Fetch video list from backend
  const { videos, loading: videosLoading, error: videosError } = useVideos();
  const [selectedVideo, setSelectedVideo] = useState('');
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState('');
  const [isDetectionStarted, setIsDetectionStarted] = useState(false);
  

  // Select the first available video by default
  useEffect(() => {
    if (videos.length > 0 && !selectedVideo) {
      setSelectedVideo(videos[0]);
    }
  }, [videos, selectedVideo]);

  // Draw detections overlay
  useDrawDetections(canvasRef, detections || []);

  // Start/stop detection for the selected video
  const handleStartDetection = useCallback(async () => {
    if (!selectedVideo) return;
    setLoading(true);
    setStatus('');
    try {
      if (!isDetectionStarted) {
        // Start detection
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
        // Stop detection
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

  // Poll current detections from backend when running
  useEffect(() => {
    if (isConnected && systemStatus === 'running') {
      const interval = setInterval(async () => {
        try {
          const res = await fetch(`${API_BASE_URL}/detections/current`);
          if (res.ok) {
            const data = await res.json();
            // Extract detections array from response
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

  // --- Render ---
  return (
    <div className="camera-view">
      {/* Video selection and control bar */}
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
      {/* Video feed and detection overlay */}
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
      {/* Video controls */}
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
  onStep: PropTypes.func,
  detections: PropTypes.array,
  isConnected: PropTypes.bool.isRequired,
  systemStatus: PropTypes.string.isRequired,
  setCurrentDetections: PropTypes.func.isRequired
};

export default CameraView;