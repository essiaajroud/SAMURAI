import React, { useState, useEffect, useRef } from 'react';
import PropTypes from 'prop-types';
import './TrackingMap.css';

// Composant de carte pour le tracking en temps réel
const TrackingMap = ({ 
  detections = [], 
  trajectoryHistory = {}, 
  isConnected = false,
  mapCenter = [48.8566, 2.3522], // Paris par défaut
  zoomLevel = 13 
}) => {
  const mapRef = useRef(null);
  const [map, setMap] = useState(null);
  const [markers, setMarkers] = useState([]);
  const [trajectories, setTrajectories] = useState([]);
  const [showTrajectories, setShowTrajectories] = useState(true);
  const [showCurrentDetections, setShowCurrentDetections] = useState(true);

  // Initialiser la carte
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (!mapRef.current) return;

    // Attendre que Leaflet soit chargé
    const initMap = () => {
      if (typeof window.L === 'undefined') {
        console.warn('Leaflet not loaded. Please install leaflet and react-leaflet');
        return;
      }

      // Vérifier que le conteneur existe toujours
      if (!mapRef.current) return;

      try {
        // Créer la carte
        const newMap = window.L.map(mapRef.current).setView(mapCenter, zoomLevel);

        // Ajouter la couche de tuiles OpenStreetMap
        window.L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
          attribution: '© OpenStreetMap contributors'
        }).addTo(newMap);

        setMap(newMap);
      } catch (error) {
        console.error('Error initializing map:', error);
      }
    };

    // Essayer d'initialiser immédiatement
    if (typeof window.L !== 'undefined') {
      initMap();
    } else {
      // Attendre que Leaflet soit chargé
      const checkLeaflet = setInterval(() => {
        if (typeof window.L !== 'undefined') {
          clearInterval(checkLeaflet);
          initMap();
        }
      }, 100);

      // Timeout de sécurité
      setTimeout(() => {
        clearInterval(checkLeaflet);
        if (typeof window.L === 'undefined') {
          console.error('Leaflet failed to load after 5 seconds');
        }
      }, 5000);
    }

    // Nettoyer la carte lors du démontage
    return () => {
      if (map) {
        try {
          map.remove();
        } catch (error) {
          console.error('Error removing map:', error);
        }
      }
    };
  }, []);

  // Mettre à jour les marqueurs des détections courantes
  useEffect(() => {
    if (!map || !showCurrentDetections || typeof window.L === 'undefined') return;

    try {
      // Supprimer les anciens marqueurs
      markers.forEach(marker => {
        if (marker && marker.remove) {
          try {
            marker.remove();
          } catch (error) {
            console.warn('Error removing marker:', error);
          }
        }
      });

      const newMarkers = [];

      detections.forEach((detection, index) => {
        if (detection.latitude && detection.longitude) {
          try {
            // Créer un marqueur coloré selon le type d'objet
            const markerColor = getMarkerColor(detection.label || 'unknown');
            
            const marker = window.L.circleMarker([detection.latitude, detection.longitude], {
              radius: 8,
              fillColor: markerColor,
              color: '#fff',
              weight: 2,
              opacity: 1,
              fillOpacity: 0.8
            }).addTo(map);

            // Ajouter un popup avec les informations de détection
            const popupContent = `
              <div class="detection-popup">
                <h4>${detection.label || 'Objet détecté'}</h4>
                <p><strong>Confiance:</strong> ${(detection.confidence * 100).toFixed(1)}%</p>
                <p><strong>Position:</strong> ${detection.latitude.toFixed(6)}, ${detection.longitude.toFixed(6)}</p>
                <p><strong>ID:</strong> ${detection.id || index}</p>
                <p><strong>Temps:</strong> ${new Date(detection.timestamp || Date.now()).toLocaleTimeString()}</p>
              </div>
            `;

            marker.bindPopup(popupContent);
            newMarkers.push(marker);
          } catch (error) {
            console.warn('Error creating marker:', error);
          }
        }
      });

      setMarkers(newMarkers);
    } catch (error) {
      console.error('Error updating markers:', error);
    }
  }, [map, detections, showCurrentDetections, markers]);

  // Mettre à jour les trajectoires
  useEffect(() => {
    if (!map || !showTrajectories || typeof window.L === 'undefined') return;

    try {
      // Supprimer les anciennes trajectoires
      trajectories.forEach(trajectory => {
        if (trajectory && trajectory.remove) {
          try {
            trajectory.remove();
          } catch (error) {
            console.warn('Error removing trajectory:', error);
          }
        }
      });

      const newTrajectories = [];

      Object.values(trajectoryHistory).forEach((trajectory) => {
        if (trajectory.points && trajectory.points.length > 1) {
          try {
            // Filtrer les points invalides
            const coordinates = trajectory.points
              .filter(point => typeof point.latitude === 'number' && typeof point.longitude === 'number')
              .map(point => [point.latitude, point.longitude]);

            // Créer la polyline seulement si on a au moins 2 points valides
            if (coordinates.length > 1) {
              const polyline = window.L.polyline(coordinates, {
                color: getTrajectoryColor(trajectory.label || 'unknown'),
                weight: 3,
                opacity: 0.7
              }).addTo(map);

              // Ajouter un popup pour la trajectoire
              const popupContent = `
                <div class="trajectory-popup">
                  <h4>Trajectoire: ${trajectory.label || 'Objet'}</h4>
                  <p><strong>ID:</strong> ${trajectory.id}</p>
                  <p><strong>Début:</strong> ${new Date(trajectory.startTime).toLocaleString()}</p>
                  <p><strong>Fin:</strong> ${new Date(trajectory.lastSeen).toLocaleString()}</p>
                  <p><strong>Points:</strong> ${trajectory.points.length}</p>
                </div>
              `;

              polyline.bindPopup(popupContent);
              newTrajectories.push(polyline);
            }
          } catch (error) {
            console.warn('Error creating trajectory:', error);
          }
        }
      });

      setTrajectories(newTrajectories);
    } catch (error) {
      console.error('Error updating trajectories:', error);
    }
  }, [map, trajectoryHistory, showTrajectories, trajectories]);

  // Fonction pour obtenir la couleur du marqueur selon le type d'objet
  const getMarkerColor = (label) => {
    const colorMap = {
      'person': '#ff4444',
      'soldier': '#4444ff',
      'civ_vehicles': '#44ff44',
      'mil_vehicles': '#ffff44',
      'mil_aircraft': '#ff44ff',
      'civ_aircraft': '#44ffff',
      'weapon': '#888888'
    };
    return colorMap[label.toLowerCase()] || colorMap['unknown'];
  };

  // Fonction pour obtenir la couleur de la trajectoire
  const getTrajectoryColor = (label) => {
    const colorMap = {
      'person': '#cc0000',
      'soldier': '#0000cc',
      'civ_vehicles': '#00cc00',
      'mil_vehicles': '#cccc00',
      'mil_aircraft': '#cc00cc',
      'civ_aircraft': '#00cccc',
      'weapon': '#666666'
    };
    return colorMap[label.toLowerCase()] || colorMap['unknown'];
  };

  // Fonction pour centrer la carte sur les détections
  const centerOnDetections = () => {
    if (!map || detections.length === 0 || typeof window.L === 'undefined') return;

    try {
      const bounds = window.L.latLngBounds(
        detections
          .filter(d => d.latitude && d.longitude)
          .map(d => [d.latitude, d.longitude])
      );

      if (!bounds.isEmpty()) {
        map.fitBounds(bounds, { padding: [20, 20] });
      }
    } catch (error) {
      console.error('Error centering on detections:', error);
    }
  };

  // Fonction pour réinitialiser la vue
  const resetView = () => {
    if (map && typeof window.L !== 'undefined') {
      try {
        map.setView(mapCenter, zoomLevel);
      } catch (error) {
        console.error('Error resetting view:', error);
      }
    }
  };

  return (
    <div className="tracking-map-container">
      <div className="map-controls">
        <div className="control-group">
          <label className="control-label">
            <input
              type="checkbox"
              checked={showCurrentDetections}
              onChange={(e) => setShowCurrentDetections(e.target.checked)}
            />
            Détections actuelles
          </label>
          <label className="control-label">
            <input
              type="checkbox"
              checked={showTrajectories}
              onChange={(e) => setShowTrajectories(e.target.checked)}
            />
            Trajectoires
          </label>
        </div>
        <div className="control-group">
          <button 
            className="map-btn"
            onClick={centerOnDetections}
            disabled={detections.length === 0}
          >
            Centrer sur détections
          </button>
          <button 
            className="map-btn"
            onClick={resetView}
          >
            Vue par défaut
          </button>
        </div>
      </div>
      
      <div className="map-status">
        <span className={`status-indicator ${isConnected ? 'connected' : 'disconnected'}`}>
          {isConnected ? '●' : '○'}
        </span>
        <span className="status-text">
          {isConnected ? 'Connecté' : 'Déconnecté'}
        </span>
        <span className="detection-count">
          {detections.length} objet(s) détecté(s)
        </span>
      </div>

      <div 
        ref={mapRef} 
        className="tracking-map"
        style={{ 
          height: '400px', 
          width: '100%',
          border: '2px solid #333',
          borderRadius: '8px'
        }}
      >
        {(!map || typeof window.L === 'undefined') && (
          <div className="map-placeholder">
            <div className="loading-spinner"></div>
            <p>Chargement de la carte...</p>
            {typeof window.L === 'undefined' && (
              <>
                <p>Veuillez installer leaflet et react-leaflet:</p>
                <code>npm install leaflet react-leaflet</code>
              </>
            )}
          </div>
        )}
      </div>

      <div className="map-legend">
        <h4>Légende</h4>
        <div className="legend-items">
          <div className="legend-item">
            <span className="legend-color" style={{ backgroundColor: '#ff4444' }}></span>
            <span>Person</span>
          </div>
          <div className="legend-item">
            <span className="legend-color" style={{ backgroundColor: '#4444ff' }}></span>
            <span>Soldier</span>
          </div>
          <div className="legend-item">
            <span className="legend-color" style={{ backgroundColor: '#44ff44' }}></span>
            <span>Civilain vehicles</span>
          </div>
          <div className="legend-item">
            <span className="legend-color" style={{ backgroundColor: '#ffff44' }}></span>
            <span>Military vehicles</span>
          </div>
          <div className="legend-item">
            <span className="legend-color" style={{ backgroundColor: '#ff44ff' }}></span>
            <span>Military aircarft</span>
          </div>
          <div className="legend-item">
            <span className="legend-color" style={{ backgroundColor: '#44ffff' }}></span>
            <span>Civilian aircarft</span>
          </div>
          <div className="legend-item">
            <span className="legend-color" style={{ backgroundColor: '#888888' }}></span>
            <span>Weapon</span>
          </div>
        </div>
      </div>
    </div>
  );
};

// Validation des props
TrackingMap.propTypes = {
  detections: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
      label: PropTypes.string,
      confidence: PropTypes.number,
      latitude: PropTypes.number,
      longitude: PropTypes.number,
      timestamp: PropTypes.number,
      bbox: PropTypes.shape({
        x: PropTypes.number,
        y: PropTypes.number,
        width: PropTypes.number,
        height: PropTypes.number
      })
    })
  ),
  trajectoryHistory: PropTypes.objectOf(
    PropTypes.shape({
      id: PropTypes.string,
      label: PropTypes.string,
      startTime: PropTypes.number,
      lastSeen: PropTypes.number,
      points: PropTypes.arrayOf(
        PropTypes.shape({
          latitude: PropTypes.number,
          longitude: PropTypes.number,
          timestamp: PropTypes.number
        })
      )
    })
  ),
  isConnected: PropTypes.bool,
  mapCenter: PropTypes.arrayOf(PropTypes.number),
  zoomLevel: PropTypes.number
};

// Valeurs par défaut
TrackingMap.defaultProps = {
  detections: [],
  trajectoryHistory: {},
  isConnected: false,
  mapCenter: [48.8566, 2.3522], // Paris par défaut
  zoomLevel: 13
};

export default TrackingMap; 