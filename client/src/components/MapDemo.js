import {React, useState, useEffect } from 'react';
import PropTypes from 'prop-types';
import TrackingMap from './TrackingMap';
import axios from 'axios';
import './MapDemo.css';

// Ce composant n'est plus une démo, mais la vue principale de la carte en direct.
const LiveTrackingView = ({ isConnected }) => {
  // --- ÉTATS POUR LES DONNÉES EN DIRECT ---
  const [liveDetections, setLiveDetections] = useState([]);
  const [liveTrajectories, setLiveTrajectories] = useState({});
  const [alerts, setAlerts] = useState([]);
  
  // --- CORRECTION : Démarrer la carte directement en Tunisie ---
  const [roverLocation, setRoverLocation] = useState([35.72, 10.58]); // Default Tunisie

  // --- RÉCUPÉRATION DES DONNÉES EN DIRECT DE L'API ---

  // 1. Récupérer la position du rover (une fois au début, puis pourrait être mis à jour par WebSocket)
  useEffect(() => {
    if (isConnected) {
      axios.get('/api/rover-location')
        .then(res => {
          if (res.data && res.data.latitude && res.data.longitude) {
            setRoverLocation([res.data.latitude, res.data.longitude]);
          }
        })
        .catch(err => console.error("Failed to fetch rover location:", err));
    }
  }, [isConnected]);

  // 2. Récupérer les détections actuelles, les trajectoires et les alertes toutes les 2 secondes
  useEffect(() => {
    if (!isConnected) return; // Ne rien faire si le backend n'est pas connecté

    const fetchData = () => {
      // Détections actuelles
      axios.get('/api/detections/current')
        .then(res => setLiveDetections(res.data.detections || []))
        .catch(err => console.error("Failed to fetch current detections:", err));

      // Trajectoires complètes
      axios.get('/api/trajectories')
        .then(res => setLiveTrajectories(res.data || {}))
        .catch(err => console.error("Failed to fetch trajectories:", err));

      // Alertes
      axios.get('/api/alerts')
        .then(res => setAlerts(res.data.alerts || []))
        .catch(() => setAlerts([]));
    };

    fetchData(); // Appel initial
    const interval = setInterval(fetchData, 2000); // Mettre à jour toutes les 2 secondes

    return () => clearInterval(interval); // Nettoyer l'intervalle à la fin
  }, [isConnected]);

  return (
    // --- L'AFFICHAGE EST SIMPLIFIÉ, PLUS DE BOUTONS "DEMO" ---
    <div className="map-demo-container">
      <div className="demo-header">
        <h3> Real-Time Tracking Map</h3>
        <div className="demo-controls">
          <span className="demo-status">
            {isConnected ? '🟢 Backend connected' : '🔴 Backend disconnected'}
          </span>
        </div>
      </div>
      
      <TrackingMap
        detections={liveDetections}
        trajectoryHistory={liveTrajectories}
        isConnected={isConnected}
        mapCenter={roverLocation}
        zoomLevel={13}
        alerts={alerts}
      />
    </div>
  );
};

LiveTrackingView.propTypes = {
  isConnected: PropTypes.bool.isRequired,
};

// Exporter le nouveau nom de composant
export default LiveTrackingView;