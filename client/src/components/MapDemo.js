import React, { useState, useEffect } from 'react';
import PropTypes from 'prop-types';
import TrackingMap from './TrackingMap';
import { generateTestDetections, generateTestTrajectories } from '../utils/mapUtils';
import axios from 'axios';
import './MapDemo.css';

const MapDemo = () => {
  const [demoDetections, setDemoDetections] = useState([]);
  const [demoTrajectories, setDemoTrajectories] = useState({});
  const [isDemoRunning, setIsDemoRunning] = useState(false);
  const [demoInterval, setDemoInterval] = useState(null);
  const [cameraLocation, setCameraLocation] = useState([48.8566, 2.3522]); // Default Paris
  // Fetch camera GPS location from backend
  useEffect(() => {
    axios.get('/api/camera-location')
      .then(res => {
        if (res.data && res.data.latitude && res.data.longitude) {
          setCameraLocation([res.data.latitude, res.data.longitude]);
        }
      })
      .catch(() => {});
  }, []);

  // Démarrer la démonstration
  const startDemo = () => {
    setIsDemoRunning(true);
    
    // Générer des données initiales
    setDemoDetections(generateTestDetections(8));
    setDemoTrajectories(generateTestTrajectories(5));
    
    // Mettre à jour les données toutes les 3 secondes
    const interval = setInterval(() => {
      setDemoDetections(generateTestDetections(5 + Math.floor(Math.random() * 5)));
      setDemoTrajectories(generateTestTrajectories(3 + Math.floor(Math.random() * 3)));
    }, 3000);
    
    setDemoInterval(interval);
  };

  // Arrêter la démonstration
  const stopDemo = () => {
    setIsDemoRunning(false);
    if (demoInterval) {
      clearInterval(demoInterval);
      setDemoInterval(null);
    }
  };

  // Nettoyer l'intervalle lors du démontage
  useEffect(() => {
    return () => {
      if (demoInterval) {
        clearInterval(demoInterval);
      }
    };
  }, [demoInterval]);

  return (
    <div className="map-demo-container">
      <div className="demo-header">
        <h3>🎯 Démonstration de la Carte de Tracking</h3>
        <div className="demo-controls">
          <button 
            className={`demo-btn ${isDemoRunning ? 'stop' : 'start'}`}
            onClick={isDemoRunning ? stopDemo : startDemo}
          >
            {isDemoRunning ? '⏹️ Arrêter Demo' : '▶️ Démarrer Demo'}
          </button>
          <span className="demo-status">
            {isDemoRunning ? '🟢 Simulation en cours' : '🔴 Simulation arrêtée'}
          </span>
        </div>
      </div>
      
      <div className="demo-info">
        <p>
          Cette démonstration simule un système de tracking en temps réel avec des objets 
          se déplaçant autour de Paris. Les données sont générées automatiquement pour 
          tester les fonctionnalités de la carte.
        </p>
        <ul>
          <li>📍 <strong>Marqueurs colorés:</strong> Chaque type d'objet a sa propre couleur</li>
          <li>🛤️ <strong>Trajectoires:</strong> Historique des déplacements des objets</li>
          <li>📊 <strong>Informations détaillées:</strong> Cliquez sur les marqueurs pour plus d'infos</li>
          <li>🎛️ <strong>Contrôles:</strong> Activez/désactivez les couches et centrez la vue</li>
        </ul>
      </div>

      <TrackingMap
        detections={demoDetections}
        trajectoryHistory={demoTrajectories}
        isConnected={true}
        mapCenter={cameraLocation}
        zoomLevel={13}
      />
    </div>
  );
};

export default MapDemo; 