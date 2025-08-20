import json
import os
import time
from typing import Optional
from dataclasses import dataclass
from flask_socketio import SocketIO

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, 'data')
POSITION_FILE = os.path.join(DATA_DIR, 'last_camera_position.json')

@dataclass
class CameraPosition:
    latitude: float
    longitude: float
    altitude: Optional[float] = None
    heading: Optional[float] = None
    timestamp: str = None

class CameraLocationManager:
    def __init__(self, socketio: SocketIO = None):
        self.socketio = socketio
        self.current_position: Optional[CameraPosition] = None
        # --- NOUVEAU : Un drapeau pour savoir si la position est réelle ---
        self.is_real_position = False 
        self._load_last_position()

    def _load_last_position(self):
        """Charge la dernière position et met le drapeau à jour."""
        try:
            with open(POSITION_FILE, 'r') as f:
                data = json.load(f)
                self.current_position = CameraPosition(**data)
                # Si on charge depuis un fichier, la position est considérée comme réelle
                self.is_real_position = True
                print(f"✅ Last known position loaded: ({self.current_position.latitude}, {self.current_position.longitude}). GPS is REAL.")
        except (FileNotFoundError, json.JSONDecodeError):
            # Si pas de fichier, on utilise une position par défaut MAIS le drapeau reste FAUX
            self.current_position = CameraPosition(latitude=34.0, longitude=9.0)
            self.is_real_position = False
            print("⚠️ No last known position file. Using default position. GPS is NOT REAL yet.")

    def _save_position(self):
        """Sauvegarde la position actuelle dans un fichier."""
        if self.current_position:
            try:
                os.makedirs(DATA_DIR, exist_ok=True)
                with open(POSITION_FILE, 'w') as f:
                    json.dump(vars(self.current_position), f, indent=2)
            except Exception as e:
                print(f"❌ CRITICAL ERROR saving camera position: {e}")

    def update_position(self, lat: float, lon: float, alt: Optional[float] = None):
        """Met à jour la position, la sauvegarde, et confirme qu'elle est réelle."""
        self.current_position = CameraPosition(
            latitude=lat, longitude=lon, altitude=alt,
            timestamp=time.strftime('%Y-%m-%dT%H:%M:%S')
        )
        # --- NOUVEAU : Dès qu'on reçoit une mise à jour, la position devient réelle ---
        if not self.is_real_position:
            print("✅ First real GPS position received. Geolocation is now active.")
        self.is_real_position = True
        self._save_position()
        
        if self.socketio:
            self.socketio.emit('camera_position_update', vars(self.current_position))