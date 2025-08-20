import { React, useState, useEffect } from 'react';
import PropTypes from 'prop-types';
import TrackingMap from './TrackingMap';
import axios from 'axios';
import './MapDemo.css';

const LiveTrackingView = ({ isConnected }) => {
  const [liveDetections, setLiveDetections] = useState([]);
  const [liveTrajectories, setLiveTrajectories] = useState({});
  const [alerts, setAlerts] = useState([]);
  
  // La position du rover est maintenant son propre état, mis à jour dynamiquement
  const [roverLocation, setRoverLocation] = useState([34.0, 9.0]); // Position par défaut

  // --- Dédié à la mise à jour de la position du rover ---
  useEffect(() => {
    if (!isConnected) return;

    // Fonction pour récupérer la dernière position du rover
    const fetchRoverLocation = () => {
      axios.get('/api/rover-location')
        .then(res => {
          if (res.data && res.data.latitude && res.data.longitude) {
            setRoverLocation([res.data.latitude, res.data.longitude]);
          }
        })
        .catch(err => console.error("Failed to fetch rover location:", err));
    };

    fetchRoverLocation(); // Appel initial
    const interval = setInterval(fetchRoverLocation, 3000); // Mise à jour toutes les 3 secondes

    return () => clearInterval(interval); // Nettoyage de l'intervalle
  }, [isConnected]);

  // --- Dédié à la récupération des détections, trajectoires et alertes ---
  useEffect(() => {
    if (!isConnected) return;

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
    const interval = setInterval(fetchData, 2000); // Mise à jour toutes les 2 secondes

    return () => clearInterval(interval);
  }, [isConnected]);

  return (
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
        mapCenter={roverLocation} // La carte utilise maintenant la position dynamique
        zoomLevel={15} // Zoom un peu plus proche
        alerts={alerts}
      />
    </div>
  );
};

LiveTrackingView.propTypes = {
  isConnected: PropTypes.bool.isRequired,
};

export default LiveTrackingView;