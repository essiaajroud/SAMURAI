import serial
import threading
import time
from typing import Optional, Tuple, Callable

class GPSTracker:
    def __init__(self, port: str = "COM3"):
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
            with serial.Serial(self.port, 9600, timeout=1) as ser:
                while self.running:
                    line = ser.readline().decode('ascii', errors='replace')
                    if line.startswith('$GPGGA'):
                        position = self._parse_gpgga(line)
                        if position:
                            self.current_position = position
                            self._notify_position()
        except Exception as e:
            print(f"Erreur GPS: {e}")
            
    def _parse_gpgga(self, nmea: str) -> Optional[Tuple[float, float]]:
        """Parser une ligne NMEA GPGGA"""
        try:
            parts = nmea.split(',')
            latitude = float(parts[2]) / 100.0
            longitude = float(parts[4]) / 100.0
            return (latitude, longitude)
        except Exception as e:
            print(f"Erreur de parsing GPS: {e}")
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

# Exemple d'utilisation
if __name__ == "__main__":
    def position_callback(position):
        print(f"Position actuelle: {position}")

    gps_tracker = GPSTracker()
    gps_tracker.add_position_callback(position_callback)
    gps_tracker.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        gps_tracker.stop()
        print("Suivi GPS arrêté.")