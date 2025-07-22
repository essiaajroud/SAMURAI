// Header.js - Displays dashboard header, system status, and controls
// Shows logo, system status, connection, and time
import React, { useState, useEffect } from 'react';
import './Header.css';
import PropTypes from 'prop-types';
import logo from '../Assets/logo.png';

// Main Header component
const Header = ({ onSystemToggle, systemStatus, isConnected = false, isDetectionStarted }) => {
  const [currentTime, setCurrentTime] = useState(new Date());

  // Update clock every second
  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentTime(new Date());
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  // Get emoji for system status
  const getStatusColor = () => {
    switch (systemStatus) {
      case 'running':
        return '🟢';
      case 'stopped':
        return '🔴';
      case 'testing':
        return '🟡';
      default:
        return '⚪';
    }
  };

  // Get connection status string
  const getConnectionStatus = () => {
    return isConnected ? '🟢 Connected' : '🔴 Disconnected';
  };

  // --- Render ---
  return (
    <header className="dashboard-header">
      <div className="header-left">
        <img src={logo} alt="Military Dashboard" className="logo" />
        <h1>Military Detection System</h1>
      </div>
      <div className="header-center">
        <span className="status-indicator">
          {getStatusColor()} {systemStatus.toUpperCase()}
        </span>
        <span className="connection-status">
          {getConnectionStatus()}
        </span>
        <span className="clock">
          {currentTime.toLocaleTimeString()}
        </span>
      </div>
      <div className="header-right">
        <button 
          className={`system-toggle ${systemStatus}`}
          onClick={onSystemToggle}
        >
          {isDetectionStarted ? 'STOP SYSTEM' : 'START SYSTEM'}
        </button>
      </div>
    </header>
  );
};

Header.propTypes = {
  onSystemToggle: PropTypes.func.isRequired,
  systemStatus: PropTypes.string.isRequired,
  isConnected: PropTypes.bool,
  isDetectionStarted: PropTypes.bool.isRequired
};

export default Header; 