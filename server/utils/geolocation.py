import numpy as np
from geopy.distance import geodesic

def calculate_object_gps(rover_lat, rover_lon, rover_heading, detection_x, frame_width, distance):
    """
    Estime la position GPS d'un objet détecté.
    
    :param rover_lat: Latitude du rover.
    :param rover_lon: Longitude du rover.
    :param rover_heading: Cap du rover en degrés (0=Nord, 90=Est).
    :param detection_x: Coordonnée X du centre de la détection en pixels.
    :param frame_width: Largeur de l'image en pixels.
    :param distance: Distance estimée de l'objet en mètres.
    :return: Tuple (latitude, longitude) de l'objet.
    """
    try:
        # Angle de vue horizontal de la caméra (à ajuster selon votre matériel)
        HORIZONTAL_FOV = 60  # en degrés

        # Calculer l'angle de la détection par rapport au centre de l'image
        angle_from_center = ((detection_x - frame_width / 2) / frame_width) * HORIZONTAL_FOV
        
        # Calculer le relèvement (bearing) absolu de l'objet
        bearing = (rover_heading + angle_from_center) % 360
        
        # Calculer le nouveau point GPS en utilisant la distance et le relèvement
        start_point = (rover_lat, rover_lon)
        destination = geodesic(meters=distance).destination(start_point, bearing)
        
        return destination.latitude, destination.longitude
    except Exception as e:
        print(f"Error in GPS calculation: {e}")
        return None, None