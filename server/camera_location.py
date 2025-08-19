import json
import threading
import time
from typing import Optional, Tuple
from dataclasses import dataclass
from flask_socketio import SocketIO
import os

# --- NOUVEAU : Définir le chemin du script pour des chemins de fichiers robustes ---
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
        self.update_thread = None
        self.running = False
        self._load_last_position()

    def _load_last_position(self):
        """Charger la dernière position connue."""
        try:
            # Utilise le chemin absolu
            with open(POSITION_FILE, 'r') as f:
                data = json.load(f)
                self.current_position = CameraPosition(**data)
        except (FileNotFoundError, json.JSONDecodeError):
            pass

    def _save_position(self):
        """Sauvegarder la position actuelle."""
        if self.current_position:
            try:
                # --- CORRECTION DÉFINITIVE : Créer le répertoire s'il n'existe pas ---
                os.makedirs(DATA_DIR, exist_ok=True)
                
                # Écrire dans le fichier en utilisant le chemin absolu
                with open(POSITION_FILE, 'w') as f:
                    json.dump(vars(self.current_position), f)
            except Exception as e:
                print(f"❌ CRITICAL ERROR saving camera position: {e}")


    def update_position(self, lat: float, lon: float, alt: Optional[float] = None):
        """Mettre à jour la position de la caméra."""
        self.current_position = CameraPosition(
            latitude=lat,
            longitude=lon,
            altitude=alt,
            timestamp=time.strftime('%Y-%m-%dT%H:%M:%S')
        )
        self._save_position()
        
        # Émettre la mise à jour via WebSocket
        if self.socketio:
            self.socketio.emit('camera_position_update', vars(self.current_position))