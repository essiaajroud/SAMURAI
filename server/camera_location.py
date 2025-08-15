import json
import threading
import time
from typing import Optional, Tuple
from dataclasses import dataclass
from flask_socketio import SocketIO

@dataclass
class CameraPosition:
    latitude: float
    longitude: float
    altitude: Optional[float] = None
    heading: Optional[float] = None
    timestamp: str = None

class CameraLocationManager:
    def __init__(self, socketio: SocketIO):
        self.socketio = socketio
        self.current_position: Optional[CameraPosition] = None
        self.update_thread = None
        self.running = False
        self._load_last_position()

    def _load_last_position(self):
        """Charger la dernière position connue"""
        try:
            with open('data/last_camera_position.json', 'r') as f:
                data = json.load(f)
                self.current_position = CameraPosition(**data)
        except (FileNotFoundError, json.JSONDecodeError):
            pass

    def _save_position(self):
        """Sauvegarder la position actuelle"""
        if self.current_position:
            with open('data/last_camera_position.json', 'w') as f:
                json.dump(vars(self.current_position), f)

    def update_position(self, lat: float, lon: float, alt: Optional[float] = None):
        """Mettre à jour la position de la caméra"""
        self.current_position = CameraPosition(
            latitude=lat,
            longitude=lon,
            altitude=alt,
            timestamp=time.strftime('%Y-%m-%dT%H:%M:%S')
        )
        self._save_position()
        
        # Émettre la mise à jour via WebSocket
        self.socketio.emit('camera_position_update', vars(self.current_position))
