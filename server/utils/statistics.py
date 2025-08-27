"""
Fonctions utilitaires pour calculer des statistiques à la demande
à partir des données de la base de données.
"""
import numpy as np
from ..models import Detection, Trajectory

def calculate_detection_stats(detections):
    """Calcule des statistiques pour une liste d'objets Detection."""
    if not detections:
        return {
            'count': 0,
            'avg_confidence': 0.0,
            'max_confidence': 0.0,
            'min_confidence': 0.0
        }
            
    confidences = [d.confidence for d in detections]
    return {
        'count': len(detections),
        'avg_confidence': float(np.mean(confidences)),
        'max_confidence': float(np.max(confidences)),
        'min_confidence': float(np.min(confidences))
    }

def calculate_tracking_stats(trajectories):
    """Calcule des statistiques pour une liste d'objets Trajectory."""
    if not trajectories:
        return {
            'total_tracks': 0,
            'active_tracks': 0,
            'avg_lifetime_sec': 0.0,
            'max_lifetime_sec': 0.0
        }
            
    lifetimes = [(t.last_seen - t.start_time).total_seconds() for t in trajectories]
    return {
        'total_tracks': len(trajectories),
        'active_tracks': len([t for t in trajectories if t.is_active]),
        'avg_lifetime_sec': float(np.mean(lifetimes)) if lifetimes else 0.0,
        'max_lifetime_sec': float(np.max(lifetimes)) if lifetimes else 0.0
    }