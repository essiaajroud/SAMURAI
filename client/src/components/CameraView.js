// CameraView.js - Displays video feed and overlays detections
// Handles video selection, detection start/stop, and drawing overlays
import React, { useRef, useEffect, useState } from 'react';
import './CameraView.css';
import PropTypes from 'prop-types';

const API_BASE_URL = 'http://localhost:5000/api';


// Custom hook to draw detections on the canvas overlay
function useDrawDetections(canvasRef, detections, videoElement) {
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !videoElement) return;
    const ctx = canvas.getContext('2d');

    // Match canvas size to video element size
    canvas.width = videoElement.clientWidth;
    canvas.height = videoElement.clientHeight;
    
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Draw each detection as a rectangle and label
    const detectionsArray = Array.isArray(detections) ? detections : [];
    detectionsArray.forEach(detection => {
      // Scale detection coords to video display size
      const scaleX = videoElement.clientWidth / (videoElement.videoWidth || videoElement.clientWidth);
      const scaleY = videoElement.clientHeight / (videoElement.videoHeight || videoElement.clientHeight);

      const { x, y, width, height, label, confidence } = detection;
      ctx.strokeStyle = '#00ff00';
      ctx.lineWidth = 2;
      ctx.strokeRect(x * scaleX, y * scaleY, width * scaleX, height * scaleY);
      ctx.fillStyle = '#00ff00';
      ctx.font = '14px Arial';
      ctx.fillText(`${label} (${(confidence * 100).toFixed(1)}%)`, x * scaleX, y * scaleY - 5);
    });
  }, [canvasRef, detections, videoElement]);
}

// Main CameraView component
const CameraView = ({ 
  isPlaying,
  onPause,
  detections = [],
  isConnected,
  systemStatus,
  videos = [],
  selectedVideo,
  setSelectedVideo,
  isDetectionStarted,
  onStartStopDetection,
  sourceType,
  setSourceType,
  networkUrl,
  setNetworkUrl
}) => {
  const canvasRef = useRef(null);
  const videoRef = useRef(null); // For local camera feed
  // SUPPRIMER : const detectionIntervalRef = useRef(null);

  // This component is now mostly controlled by App.js
  // Local state can be for UI feedback, like loading, if needed.
  const [loading, setLoading] = useState(false); // Can still be useful for local UI feedback
  const [errorMessage, setErrorMessage] = useState(''); // Pour afficher les messages d'erreur

  // --- HOOKS ---

  // Draw detections overlay, now with video element reference
  useDrawDetections(canvasRef, detections || [], videoRef.current);

  // Stop all streams when component unmounts
  useEffect(() => {
    return () => {
      // Ensure detection is stopped on server as well, mais seulement si le backend est connecté
      if (isConnected) {
        try {
          fetch(`${API_BASE_URL}/yolo/stream/stop`, { method: 'POST' });
        } catch (error) {
          console.warn('Failed to stop stream on unmount:', error);
        }
      }
    };
  }, [isConnected]);


  // The main detection handler is now passed from App.js
  const handleStartStopClick = async () => {
    setLoading(true);
    setErrorMessage(''); // Réinitialiser le message d'erreur
    
    try {
      const result = await onStartStopDetection();
      // Si onStartStopDetection renvoie un objet avec une erreur, l'afficher
      if (result && result.error) {
        setErrorMessage(result.error);
      }
    } catch (error) {
      setErrorMessage(`Erreur: ${error.message || 'Impossible de démarrer la détection'}`);
    } finally {
      setLoading(false);
    }
  };

  // Polling logic is now in App.js, so this useEffect is no longer needed here.


  // --- RENDER ---
  const renderSourceSelector = () => (
    <div className="source-selector-container">
       <label htmlFor="source-type-select">Source:</label>
       <select 
         id="source-type-select"
         value={sourceType}
         onChange={e => setSourceType(e.target.value)}
         disabled={isDetectionStarted}
       >
         <option value="network">Network Camera (Phone/Rover)</option>
         <option value="video">Server Video</option>
       </select>
       
       {sourceType === 'video' && (
         <>
           <label htmlFor="video-select" style={{ marginLeft: 18 }}>Video:</label>
           <select
             id="video-select"
             value={selectedVideo}
             onChange={e => setSelectedVideo(e.target.value)}
             disabled={isDetectionStarted}
             aria-label="Video selection"
           >
             {videos.map(video => (
               <option key={video} value={video}>{video}</option>
             ))}
           </select>
         </>
       )}
       {sourceType === 'network' && (
         <>
           <label htmlFor="network-url" style={{ marginLeft: 18 }}>Network URL:</label>
           <input
             type="text"
             id="network-url"
             value={networkUrl}
             onChange={e => setNetworkUrl(e.target.value)}
             placeholder="e.g., http://192.168.1.100:8080/video"
             disabled={isDetectionStarted}
             style={{ marginLeft: 18 }}
           />
         </>
       )}
    </div>
  );

  return (
    <div className="camera-view">
      {/* Video selection and control bar */}
      <div className="control-bar">
        {renderSourceSelector()}
        
        <button
          className={`control-button ${isDetectionStarted ? 'pause' : 'play'}`}
          onClick={handleStartStopClick}
          disabled={loading || !isConnected || (sourceType === 'video' && !selectedVideo) || (sourceType === 'network' && !networkUrl)}
          aria-busy={loading}
          style={{ marginLeft: 'auto', marginRight: 18 }}
        >
          {!isConnected
            ? 'Backend non disponible'
            : (loading ? 'Chargement...' : (isDetectionStarted ? '⏸️ Arrêter la détection' : '▶️ Démarrer la détection'))}
        </button>
      </div>
      <div className="status-bar">
        {loading && <span className="status-message">Processing...</span>}
        {errorMessage && (
          <div className="error-message" style={{ color: '#ff5555', padding: '8px', margin: '5px 0', backgroundColor: 'rgba(255,0,0,0.1)', borderRadius: '4px' }}>
            <strong>Erreur:</strong> {errorMessage}
          </div>
        )}
      </div>

      {/* Video feed and detection overlay */}
      <div className="video-container" style={{ height: '520px', width: '100%', minHeight: '520px', boxSizing: 'border-box' }}>
        {/* Server-processed Feed (for Video and Network Camera) */}
        {isDetectionStarted && isConnected && (
          <img
            ref={videoRef} // Also use ref here to get dimensions for canvas
            className="video-feed"
            src={`http://localhost:5000/video_feed?t=${Date.now()}`} // Added timestamp to avoid caching
            alt="Video stream"
            style={{ width: '100%', height: '100%', objectFit: 'cover', borderRadius: 8 }}
            onError={(e) => {
              console.warn('Failed to load video feed');
              e.target.style.display = 'none'; // Cacher l'image en cas d'erreur
            }}
          />
        )}

        {/* Fallback display when no stream is active or backend is not connected */}
        {(!isDetectionStarted || !isConnected) && (
          <div className="video-placeholder">
            {!isConnected
              ? "Le backend n'est pas disponible. L'interface est en mode hors ligne."
              : "Sélectionnez une source et démarrez la détection pour voir le flux vidéo."}
          </div>
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
          disabled={!isDetectionStarted || !isConnected}
        >
          {isPlaying ? '⏸️ Pause' : '▶️ Lecture'}
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
  videos: PropTypes.array.isRequired,
  selectedVideo: PropTypes.string.isRequired,
  setSelectedVideo: PropTypes.func.isRequired,
  isDetectionStarted: PropTypes.bool.isRequired,
  onStartStopDetection: PropTypes.func.isRequired,
  sourceType: PropTypes.string.isRequired,
  setSourceType: PropTypes.func.isRequired,
  networkUrl: PropTypes.string.isRequired,
  setNetworkUrl: PropTypes.func.isRequired
};

export default CameraView;