from typing import Dict, List
from datetime import datetime
import json
from flask_socketio import SocketIO
import geopy.distance

class AlertManager:
    def __init__(self, socketio: SocketIO = None):
        self.zones = {}  # Zones civiles, militaires, etc.
        self.active_alerts = []
        self.alert_callbacks = []
        self.socketio = socketio
        self.camera_position = None
        self.threat_radius = 100  # rayon en mètres

    def add_zone(self, zone_id: str, zone_type: str, coordinates: List[tuple]):
        """Ajouter une zone (civile, militaire, etc)"""
        self.zones[zone_id] = {
            "type": zone_type,
            "coordinates": coordinates
        }

    def update_camera_position(self, lat: float, lon: float):
        """Mettre à jour la position de la caméra"""
        self.camera_position = (lat, lon)
        if self.socketio:
            self.socketio.emit('camera_position_update', {
                'lat': lat,
                'lon': lon,
                'timestamp': datetime.now().isoformat()
            })

    def check_threat(self, detection: Dict, location: tuple) -> bool:
        if not self.camera_position:
            return False

        lat, lon = location
        
        # Calculer la distance par rapport à la caméra
        distance = geopy.distance.distance(
            self.camera_position,
            (lat, lon)
        ).meters

        # Vérifier si la détection est dans le rayon de surveillance
        if distance > self.threat_radius:
            return False

        # Vérifier chaque zone
        for zone_id, zone in self.zones.items():
            if self._point_in_zone(lat, lon, zone["coordinates"]):
                if self._is_threat(detection, zone):
                    self._create_alert("THREAT", 
                        f"{detection['label']} detected in area {zone['type']}", 
                        location, detection, distance)
                    return True
        return False

    def _is_threat(self, detection: Dict, zone: Dict) -> bool:
        """Vérifier si la détection est une menace dans la zone donnée"""
        threats = {
            'civilian': ['soldier', 'weapon', 'military_vehicles'],
            'restricted': ['person', 'civilian_vehicles'],
            'military': ['civilian_vehicles']
        }
        return zone["type"] in threats and detection["label"] in threats[zone["type"]]

    def _create_alert(self, level: str, message: str, location: tuple, detection: Dict, distance: float):
        """Créer et diffuser une alerte"""
        alert = {
            "level": level,
            "message": message,
            "location": location,
            "distance": distance,
            "timestamp": datetime.now().isoformat(),
            "detection": detection,
            "camera_position": self.camera_position
        }
        self.active_alerts.append(alert)
        
        # Émettre l'alerte via WebSocket
        if self.socketio:
            self.socketio.emit('new_alert', alert)

        # Notifier les callbacks
        for callback in self.alert_callbacks:
            callback(alert)

    def _point_in_zone(self, lat: float, lon: float, zone_coords: List[tuple]) -> bool:
        """Vérifier si un point est dans une zone polygonale"""
        # Implémentation de l'algorithme ray casting
        x, y = lon, lat
        inside = False
        for (poly_x, poly_y) in zone_coords:
            if ((poly_y > y) != (poly_x > x)):
                inside = not inside
        return inside

# Create global instance
alert_manager = AlertManager()

# Ensure the instance is available for import
__all__ = ['alert_manager']