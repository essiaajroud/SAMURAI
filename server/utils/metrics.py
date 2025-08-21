# Performance metrics calculation utilities
import numpy as np
from datetime import datetime, timezone

class MetricsCalculator:
    @staticmethod
    def calculate_detection_metrics(detections):
        if not detections:
            return {}
            
        confidences = [d.confidence for d in detections]
        return {
            'count': len(detections),
            'avg_confidence': float(np.mean(confidences)),
            'max_confidence': float(np.max(confidences)),
            'min_confidence': float(np.min(confidences))
        }

    @staticmethod
    def calculate_tracking_metrics(trajectories):
        if not trajectories:
            return {}
            
        lifetimes = [(t.last_seen - t.start_time).total_seconds() for t in trajectories]
        return {
            'active_tracks': len([t for t in trajectories if t.is_active]),
            'avg_lifetime': float(np.mean(lifetimes)) if lifetimes else 0,
            'max_lifetime': float(np.max(lifetimes)) if lifetimes else 0
        }
