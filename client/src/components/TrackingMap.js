// TrackingMap.js (VERSION FINALE FUSIONNÉE ET CORRIGÉE)

import React, { useState, useEffect, useRef } from 'react';
import PropTypes from 'prop-types';
import './TrackingMap.css';

// --- FONCTIONS UTILITAIRES ---
const getMarkerColor = (label = 'unknown') => {
  const knownClasses = ['person', 'soldier', 'weapon', 'military_vehicles', 'civilian_vehicles', 'military_aircraft', 'civilian_aircraft'];
  const index = knownClasses.indexOf(label.toLowerCase().replace(' ', '_'));
  if (index === -1) return '#888888';
  return `hsl(${(index * 360) / knownClasses.length}, 70%, 50%)`;
};

const getTrajectoryColor = (label = 'unknown') => {
  const markerColor = getMarkerColor(label);
  if (markerColor.startsWith('hsl')) return markerColor.replace('50%)', '40%)');
  return '#666666';
};

// --- COMPOSANT PRINCIPAL ---
const TrackingMap = ({ 
  detections, trajectoryHistory, isConnected,
  mapCenter, zoomLevel, alerts
}) => {
  // Refs pour le conteneur et les instances Leaflet
  const mapContainerRef = useRef(null);
  const mapInstance = useRef(null);
  const layersRef = useRef({
    markers: null,
    trajectories: null,
    alerts: null,
    camera: null,
  });

  // Initialisation de la carte (une seule fois)
  useEffect(() => {
    if (mapContainerRef.current && !mapInstance.current) {
      const map = window.L.map(mapContainerRef.current).setView(mapCenter, zoomLevel);
      window.L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors'
      }).addTo(map);
      
      layersRef.current.markers = window.L.layerGroup().addTo(map);
      layersRef.current.trajectories = window.L.layerGroup().addTo(map);
      layersRef.current.alerts = window.L.layerGroup().addTo(map);
      mapInstance.current = map;
    }
    return () => {
      if (mapInstance.current && mapCenter) {
      mapInstance.current.setView(mapCenter, mapInstance.current.getZoom());
    }
    };
  }, [mapCenter, zoomLevel]); // S'exécute si les props initiales changent

  // États locaux pour les checkboxes
  const [showTrajectories, setShowTrajectories] = useState(true);
  const [showCurrentDetections, setShowCurrentDetections] = useState(true);
  const [showAlerts, setShowAlerts] = useState(true);

  // Mises à jour dynamiques des couches
  useEffect(() => {
    const map = mapInstance.current;
    if (!map) return;

    // Mise à jour du Rover
    if (!layersRef.current.camera) {
      layersRef.current.camera = window.L.marker(mapCenter, {
        icon: window.L.divIcon({ className: 'camera-marker', html: '<div style="font-size: 24px; transform: rotate(-45deg);">🛰️</div>', iconSize: [24, 24], iconAnchor: [12, 12] })
      }).addTo(map).bindPopup('<b>Rover Position</b>');
    } else {
      layersRef.current.camera.setLatLng(mapCenter);
    }
  }, [mapCenter]);

  useEffect(() => {
    const layer = layersRef.current.markers;
    if (layer) {
      layer.clearLayers();
      if (showCurrentDetections && detections) {
        detections.forEach((d) => {
          if (d.latitude && d.longitude) {
            const marker = window.L.circleMarker([d.latitude, d.longitude], { radius: 8, fillColor: getMarkerColor(d.label), color: '#fff', weight: 2, opacity: 1, fillOpacity: 0.8 });
            marker.bindPopup(`<h4>${d.label || 'Objet'}</h4><p>Confiance: ${(d.confidence * 100).toFixed(1)}%</p>`);
            layer.addLayer(marker);
          }
        });
      }
    }
  }, [detections, showCurrentDetections]);

  useEffect(() => {
    const layer = layersRef.current.trajectories;
    if (layer) {
      layer.clearLayers();
      if (showTrajectories && trajectoryHistory) {
        Object.values(trajectoryHistory).forEach((t) => {
          if (t?.points?.length > 1) {
            const coords = t.points.filter(p => p?.latitude && p?.longitude).map(p => [p.latitude, p.longitude]);
            if (coords.length > 1) layer.addLayer(window.L.polyline(coords, { color: getTrajectoryColor(t.label), weight: 3, opacity: 0.7 }));
          }
        });
      }
    }
  }, [trajectoryHistory, showTrajectories]);

  useEffect(() => {
    const layer = layersRef.current.alerts;
    if (layer) {
      layer.clearLayers();
      if (showAlerts && alerts) {
        alerts.forEach((alert) => {
          if (alert?.lat && alert?.lon) {
            const marker = window.L.circleMarker([alert.lat, alert.lon], { radius: 12, fillColor: alert.color || '#ff0000', color: '#222', weight: 3, opacity: 1, fillOpacity: 0.9 });
            marker.bindPopup(`<h4 style="color:${alert.color}">${alert.type?.toUpperCase()}</h4><p>${alert.message}</p>`);
            layer.addLayer(marker);
          }
        });
      }
    }
  }, [alerts, showAlerts]);

  // Fonctions de contrôle
  const centerOnDetections = () => {
    const map = mapInstance.current;
    if (!map || !detections || detections.length === 0) return;
    const bounds = window.L.latLngBounds(detections.filter(d => d.latitude && d.longitude).map(d => [d.latitude, d.longitude]));
    if (bounds.isValid()) map.fitBounds(bounds, { padding: [50, 50] });
  };
  const resetView = () => {
    const map = mapInstance.current;
    if (map) map.setView(mapCenter, zoomLevel);
  };

  // --- RENDER (RESTAURÉ DE VOTRE ANCIENNE VERSION) ---
  return (
    <div className="tracking-map-container">
      <div className="map-controls">
        <div className="control-group">
          <label className="control-label">
            <input type="checkbox" checked={showCurrentDetections} onChange={(e) => setShowCurrentDetections(e.target.checked)} />
            Current detections
          </label>
          <label className="control-label">
            <input type="checkbox" checked={showTrajectories} onChange={(e) => setShowTrajectories(e.target.checked)} />
            Trajectories
          </label>
        </div>
        <div className="control-group">
          <label className="control-label">
            <input type="checkbox" checked={showAlerts} onChange={(e) => setShowAlerts(e.target.checked)} />
            Alerts IA/cartography
          </label>
        </div>
        <div className="control-group">
          <button className="map-btn" onClick={centerOnDetections} disabled={!detections || detections.length === 0}>
            Center on detections
          </button>
          <button className="map-btn" onClick={resetView}>
            Default view
          </button>
        </div>
      </div>
      
      <div className="map-status">
        <span className={`status-indicator ${isConnected ? 'connected' : 'disconnected'}`}>●</span>
        <span className="status-text">{isConnected ? 'connected' : 'disconnected'}</span>
        <span className="detection-count">{detections ? detections.length : 0} object(s) detected</span>
      </div>

      <div ref={mapContainerRef} className="tracking-map"></div>

      <div className="map-legend">
        <h4>Légende</h4>
        <div className="legend-items">
          <div className="legend-item"><span style={{ fontSize: '18px' }}>🛰️</span><span>Rover</span></div>
          {['Person', 'Soldier', 'Civilian vehicles', 'Military vehicles', 'Military aircarft', 'Civilian aircarft', 'Weapon'].map(label => (
            <div className="legend-item" key={label}>
              <span className="legend-color" style={{ backgroundColor: getMarkerColor(label) }}></span>
              <span>{label}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

// --- VALIDATION ET VALEURS PAR DÉFAUT ---
TrackingMap.propTypes = {
  detections: PropTypes.array,
  trajectoryHistory: PropTypes.object,
  isConnected: PropTypes.bool,
  mapCenter: PropTypes.array,
  zoomLevel: PropTypes.number,
  alerts: PropTypes.array,
};

// Pas de defaultProps, les valeurs sont dans la signature

export default TrackingMap;