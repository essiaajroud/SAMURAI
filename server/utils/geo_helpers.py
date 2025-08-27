# Fichier: server/utils/geo_helpers.py
"""
Fonctions utilitaires liées à la géolocalisation et aux zones géographiques.
"""
import shapely.geometry
import osmnx as ox
from flask import current_app

# Note: zone_polygons est maintenant géré dans le __init__.py principal
# pour éviter un état global dans un module utilitaire.

def load_osm_zones(zone_polygons, center_lat, center_lon, dist_m=5000):
    try:
        tags = {'landuse': 'military'}
        gdf_mil = ox.features.features_from_point((center_lat, center_lon), tags, dist=dist_m)
        zone_polygons['military'] = list(gdf_mil.geometry.values)
        current_app.logger.info(f"Loaded {len(zone_polygons['military'])} military zones from OSM.")
    except Exception as e:
        current_app.logger.error(f"Could not load OSM zones: {e}")

def point_in_military_zone(zone_polygons, lat, lon):
    pt = shapely.geometry.Point(lon, lat)
    # Vérifier si la clé existe avant d'itérer
    for poly in zone_polygons.get('military', []):
        if poly is not None and poly.is_valid and poly.contains(pt):
            return True
    return False