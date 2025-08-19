import serial
import threading
import time
from typing import Optional, Tuple, Callable
import platform # <-- AJOUT : Pour détecter le système d'exploitation

class GPSTracker:
    def __init__(self, port: str = None):
        # --- MODIFICATION : Rendre le port optionnel et plus intelligent ---
        if port is None:
            # Définir un port par défaut en fonction de l'OS
            if platform.system() == "Windows":
                self.port = "COM3"
            else: # Pour Linux/macOS
                self.port = "/dev/ttyUSB0"
        else:
            self.port = port
        
        self.current_position: Optional[Tuple[float, float]] = None
        self.running = False
        self.position_callbacks = []
        
    def start(self):
        """Démarrer le suivi GPS"""
        self.running = True
        self.thread = threading.Thread(target=self._read_gps)
        self.thread.daemon = True
        self.thread.start()
        
    def _read_gps(self):
        """Lire les données GPS en continu"""
        try:
            # Le 'with' gère l'ouverture et la fermeture du port
            with serial.Serial(self.port, 9600, timeout=1) as ser:
                print(f"✅ GPS port {self.port} opened successfully.")
                while self.running:
                    line = ser.readline().decode('ascii', errors='replace')
                    if line.startswith('$GPGGA'):
                        position = self._parse_gpgga(line)
                        if position:
                            self.current_position = position
                            self._notify_position()
        except serial.SerialException as e:
            # Gère spécifiquement l'erreur d'ouverture de port
            print(f"❌ GPS ERROR: Could not open port '{self.port}'. Is the device connected? Error: {e}")
        except Exception as e:
            # Gère les autres erreurs potentielles
            print(f"❌ An unexpected GPS error occurred: {e}")
            
    def _parse_gpgga(self, nmea: str) -> Optional[Tuple[float, float]]:
        """Parser une ligne NMEA GPGGA"""
        try:
            parts = nmea.split(',')
            # Convertir de DDMM.MMMM en degrés décimaux
            lat_raw = float(parts[2])
            lat_deg = int(lat_raw / 100)
            lat_min = lat_raw - lat_deg * 100
            latitude = lat_deg + lat_min / 60
            if parts[3] == 'S':
                latitude = -latitude

            lon_raw = float(parts[4])
            lon_deg = int(lon_raw / 100)
            lon_min = lon_raw - lon_deg * 100
            longitude = lon_deg + lon_min / 60
            if parts[5] == 'W':
                longitude = -longitude
            
            return (latitude, longitude)
        except (ValueError, IndexError):
            # Ignore les trames GPGGA mal formées ou incomplètes
            return None

    def _notify_position(self):
        """Notifier les callbacks de position"""
        for callback in self.position_callbacks:
            callback(self.current_position)

    def add_position_callback(self, callback: Callable[[Optional[Tuple[float, float]]], None]):
        """Ajouter un callback pour les mises à jour de position"""
        self.position_callbacks.append(callback)

    def stop(self):
        """Arrêter le suivi GPS"""
        self.running = False
        if hasattr(self, 'thread'):
            self.thread.join()