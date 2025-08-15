from typing import Dict, List
import folium
import json

class MapTracker:
    def __init__(self):
        self.detections = []
        self.zones = {}
        self.map = None
        
    def initialize_map(self, center: tuple):
        """Initialiser la carte"""
        self.map = folium.Map(location=center, zoom_start=15)
        
    def add_detection(self, detection: Dict, location: tuple):
        """Ajouter une détection sur la carte"""
        lat, lon = location
        
        # Choisir l'icône selon le type de détection
        icon_color = 'red' if detection['label'] in ['soldier', 'weapon'] else 'blue'
        
        folium.Marker(
            [lat, lon],
            popup=f"{detection['label']} ({detection['confidence']:.2f})",
            icon=folium.Icon(color=icon_color)
        ).add_to(self.map)
        
        # Ajouter à l'historique
        self.detections.append({
            "location": location,
            "detection": detection,
            "timestamp": detection["timestamp"]
        })
        
    def draw_zone(self, zone_id: str, coordinates: List[tuple], color: str):
        """Dessiner une zone sur la carte"""
        folium.Polygon(
            locations=coordinates,
            color=color,
            fill=True,
            popup=zone_id
        ).add_to(self.map)
