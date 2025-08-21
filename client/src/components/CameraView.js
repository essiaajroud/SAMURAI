// CameraView.js - Displays video feed and overlays detections
// Handles video selection, detection start/stop, and drawing overlays
import React, { useRef, useEffect, useState } from 'react';
import './CameraView.css';
import PropTypes from 'prop-types';

const API_BASE_URL = 'http://localhost:5000/api';

// Handle real-time detection drawing on canvas
function useDrawDetections(canvasRef, detections, videoElement) {
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !videoElement) return;
    const ctx = canvas.getContext('2d');

    // Synchronize canvas dimensions with video
    canvas.width = videoElement.clientWidth;
    canvas.height = videoElement.clientHeight;
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Process and draw each detection
    Array.isArray(detections) && detections.forEach(detection => {
      const scaleX = videoElement.clientWidth / (videoElement.videoWidth || videoElement.clientWidth);
      const scaleY = videoElement.clientHeight / (videoElement.videoHeight || videoElement.clientHeight);
      drawDetectionBox(ctx, detection, scaleX, scaleY);
    });
  }, [canvasRef, detections, videoElement]);
}

// Helper function to draw a single detection box with label
function drawDetectionBox(ctx, detection, scaleX, scaleY) {
  const { x, y, width, height, label, confidence } = detection;
  
  // Draw bounding box
  ctx.strokeStyle = '#00ff00';
  ctx.lineWidth = 2;
  ctx.strokeRect(x * scaleX, y * scaleY, width * scaleX, height * scaleY);
  
  // Draw label with confidence
  ctx.fillStyle = '#00ff00';
  ctx.font = '14px Arial';
  ctx.fillText(`${label} (${(confidence * 100).toFixed(1)}%)`, x * scaleX, y * scaleY - 5);
}

// Main camera view component
const CameraView = ({ 
  isConnected,
  systemStatus,
  isDetectionStarted,
  onStartStopDetection,
  networkUrl,
  setNetworkUrl,
  detections = []
}) => {
  const canvasRef = useRef(null);
  const videoRef = useRef(null);
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');

  // Draw detections overlay
  useDrawDetections(canvasRef, detections || [], videoRef.current);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (isConnected) {
        fetch(`${API_BASE_URL}/yolo/stream/stop`, { method: 'POST' })
          .catch(error => console.warn('Stream cleanup failed:', error));
      }
    };
  }, [isConnected]);

  // Handle start/stop detection
  const handleStartStopClick = async () => {
    setLoading(true);
    setErrorMessage('');
    try {
      const result = await onStartStopDetection();
      if (result?.error) setErrorMessage(result.error);
    } catch (error) {
      setErrorMessage(`Error: ${error.message || 'Unable to start detection'}`);
    } finally {
      setLoading(false);
    }
  };

  // Network URL input component
  const renderSourceSelector = () => (
    <div className="source-selector-container">
      <label htmlFor="network-url">Network URL:</label>
      <input
        type="text"
        id="network-url"
        value={networkUrl}
        onChange={e => setNetworkUrl(e.target.value)}
        placeholder="e.g., http://192.168.1.100:8080/video"
        disabled={isDetectionStarted}
      />
    </div>
  );

  // --- RENDER ---
  return (
    <div className="camera-view">
      {/* Video selection and control bar */}
      <div className="control-bar">
        {renderSourceSelector()}
        
        <button
          className={`control-button ${isDetectionStarted ? 'pause' : 'play'}`}
          onClick={handleStartStopClick}
          disabled={loading || !isConnected || !networkUrl}
          aria-busy={loading}
          style={{ marginLeft: 'auto', marginRight: 18 }}
        >
          {!isConnected
            ? 'Backend not available'
            : (loading ? 'Loading...' : (isDetectionStarted ? '⏸️ Stop detection' : '▶️ Start detection'))}
        </button>
      </div>
      <div className="status-bar">
        {loading && <span className="status-message">Processing...</span>}
        {errorMessage && (
          <div className="error-message" style={{ color: '#ff5555', padding: '8px', margin: '5px 0', backgroundColor: 'rgba(255,0,0,0.1)', borderRadius: '4px' }}>
            <strong>Error:</strong> {errorMessage}
          </div>
        )}
      </div>

      {/* Video feed and detection overlay */}
      <div className="video-container" style={{ height: '520px', width: '98%', minHeight: '520px', boxSizing: 'border-box' }}>
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
              ? "The backend is unavailable. The interface is in offline mode."
              : "Select a source and start detection to see the video stream."}
          </div>
        )}

        <canvas
          ref={canvasRef}
          className="detection-overlay"
        />
      </div>
      
    </div>
  );
};

// PropTypes validation for component props
CameraView.propTypes = {
  isConnected: PropTypes.bool.isRequired,
  systemStatus: PropTypes.string.isRequired,
  isDetectionStarted: PropTypes.bool.isRequired,
  onStartStopDetection: PropTypes.func.isRequired,
  networkUrl: PropTypes.string.isRequired,
  setNetworkUrl: PropTypes.func.isRequired,
  detections: PropTypes.array
};

export default CameraView;