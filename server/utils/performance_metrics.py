"""
Utility functions for calculating and tracking performance metrics.
Used by both detection and tracking systems.
"""

import numpy as np
from typing import List, Dict, Any

class PerformanceTracker:
    def __init__(self):
        self.metrics_history = []
        self.current_metrics = {}
        
    def update_metrics(self, metrics: Dict[str, Any]):
        """Update current performance metrics."""
        self.current_metrics.update(metrics)
        self.metrics_history.append(metrics)
        
        # Keep only last 1000 entries
        if len(self.metrics_history) > 1000:
            self.metrics_history = self.metrics_history[-1000:]
            
    def get_average_metrics(self, window: int = 100) -> Dict[str, float]:
        """Calculate average metrics over the specified window."""
        if not self.metrics_history:
            return {}
            
        recent = self.metrics_history[-window:]
        averages = {}
        
        for key in recent[0].keys():
            values = [m[key] for m in recent if key in m]
            if values:
                averages[key] = float(np.mean(values))
                
        return averages
