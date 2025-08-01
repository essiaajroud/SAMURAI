"""
Camera GPS Location Management
Handles real GPS coordinates for camera positioning and geolocation
"""

import json
import os
import time
from datetime import datetime, timezone
from typing import Dict, Optional, Tuple
import requests
from dataclasses import dataclass

@dataclass
class GPSCoordinates:
    latitude: float
    longitude: float
    altitude: Optional[float] = None
    accuracy: Optional[float] = None
    timestamp: Optional[datetime] = None
    source: str = "manual"  # manual, gps_device, network

class CameraGPSManager:
    def __init__(self, config_file: str = "camera_gps_config.json"):
        self.config_file = config_file
        self.current_location = None
        self.gps_history = []
        self.max_history = 100
        
        # Default location (Tunis, Tunisia)
        self.default_location = GPSCoordinates(
            latitude=36.8065,
            longitude=10.1815,
            altitude=0.0,
            accuracy=10.0,
            timestamp=datetime.now(timezone.utc),
            source="default"
        )
        
        self.load_config()
    
    def load_config(self):
        """Load GPS configuration from file"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                
                if 'current_location' in config:
                    loc = config['current_location']
                    self.current_location = GPSCoordinates(
                        latitude=loc['latitude'],
                        longitude=loc['longitude'],
                        altitude=loc.get('altitude'),
                        accuracy=loc.get('accuracy'),
                        timestamp=datetime.fromisoformat(loc['timestamp']),
                        source=loc.get('source', 'config')
                    )
                else:
                    self.current_location = self.default_location
            else:
                self.current_location = self.default_location
                self.save_config()
                
        except Exception as e:
            print(f"⚠️ Error loading GPS config: {e}")
            self.current_location = self.default_location
    
    def save_config(self):
        """Save GPS configuration to file"""
        try:
            config = {
                'current_location': {
                    'latitude': self.current_location.latitude,
                    'longitude': self.current_location.longitude,
                    'altitude': self.current_location.altitude,
                    'accuracy': self.current_location.accuracy,
                    'timestamp': self.current_location.timestamp.isoformat(),
                    'source': self.current_location.source
                },
                'last_updated': datetime.now(timezone.utc).isoformat()
            }
            
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
                
        except Exception as e:
            print(f"⚠️ Error saving GPS config: {e}")
    
    def set_location(self, latitude: float, longitude: float, 
                    altitude: Optional[float] = None, 
                    accuracy: Optional[float] = None,
                    source: str = "manual"):
        """Set camera GPS location"""
        # Add to history
        if self.current_location:
            self.gps_history.append(self.current_location)
            if len(self.gps_history) > self.max_history:
                self.gps_history.pop(0)
        
        # Set new location
        self.current_location = GPSCoordinates(
            latitude=latitude,
            longitude=longitude,
            altitude=altitude,
            accuracy=accuracy,
            timestamp=datetime.now(timezone.utc),
            source=source
        )
        
        self.save_config()
        print(f"📍 Camera location updated: {latitude:.6f}, {longitude:.6f}")
    
    def get_location(self) -> GPSCoordinates:
        """Get current camera location"""
        return self.current_location or self.default_location
    
    def get_location_dict(self) -> Dict:
        """Get current location as dictionary"""
        loc = self.get_location()
        return {
            'latitude': loc.latitude,
            'longitude': loc.longitude,
            'altitude': loc.altitude,
            'accuracy': loc.accuracy,
            'timestamp': loc.timestamp.isoformat() if loc.timestamp else None,
            'source': loc.source
        }
    
    def get_location_history(self) -> list:
        """Get GPS location history"""
        return [self.get_location_dict()] + [
            {
                'latitude': loc.latitude,
                'longitude': loc.longitude,
                'altitude': loc.altitude,
                'accuracy': loc.accuracy,
                'timestamp': loc.timestamp.isoformat() if loc.timestamp else None,
                'source': loc.source
            }
            for loc in self.gps_history
        ]
    
    def get_location_from_ip(self) -> Optional[GPSCoordinates]:
        """Get approximate location from IP address"""
        try:
            response = requests.get('http://ip-api.com/json/', timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data['status'] == 'success':
                    return GPSCoordinates(
                        latitude=data['lat'],
                        longitude=data['lon'],
                        accuracy=5000.0,  # IP geolocation is not very accurate
                        timestamp=datetime.now(timezone.utc),
                        source="ip_geolocation"
                    )
        except Exception as e:
            print(f"⚠️ IP geolocation failed: {e}")
        return None
    
    def auto_update_location(self):
        """Automatically update location from IP if no manual location set"""
        if not self.current_location or self.current_location.source == "default":
            ip_location = self.get_location_from_ip()
            if ip_location:
                self.set_location(
                    ip_location.latitude,
                    ip_location.longitude,
                    ip_location.altitude,
                    ip_location.accuracy,
                    "ip_geolocation"
                )
                return True
        return False

# Global GPS manager instance
gps_manager = CameraGPSManager()

def get_camera_location() -> Dict:
    """Get current camera location for API"""
    return gps_manager.get_location_dict()

def set_camera_location(latitude: float, longitude: float, 
                       altitude: Optional[float] = None,
                       accuracy: Optional[float] = None) -> Dict:
    """Set camera location from API"""
    gps_manager.set_location(latitude, longitude, altitude, accuracy, "api")
    return gps_manager.get_location_dict()

def auto_detect_location() -> Dict:
    """Auto-detect location from IP"""
    if gps_manager.auto_update_location():
        return gps_manager.get_location_dict()
    return {"error": "Could not detect location from IP"} 