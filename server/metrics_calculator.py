"""
Metrics Calculator for AI Model Performance
Calculates Precision, Recall, F1-Score, and generates performance curves
"""

import numpy as np
import json
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Tuple, Optional, Any
from collections import defaultdict, deque
import math

class MetricsCalculator:
    def __init__(self, history_size: int = 1000):
        """
        Initialize metrics calculator
        
        Args:
            history_size: Number of recent detections to keep for calculations
        """
        self.history_size = history_size
        self.detection_history = deque(maxlen=history_size)
        self.ground_truth_history = deque(maxlen=history_size)
        self.performance_history = deque(maxlen=100)  # Keep last 100 performance snapshots
        
        # Current metrics
        self.current_metrics = {
            'precision': 0.0,
            'recall': 0.0,
            'f1_score': 0.0,
            'accuracy': 0.0,
            'true_positives': 0,
            'false_positives': 0,
            'false_negatives': 0,
            'true_negatives': 0,
            'total_detections': 0,
            'total_ground_truth': 0
        }
        
        # Performance tracking
        self.fps_history = deque(maxlen=50)
        self.inference_time_history = deque(maxlen=50)
        self.confidence_history = deque(maxlen=100)
        
        # Class-specific metrics
        self.class_metrics = defaultdict(lambda: {
            'precision': 0.0,
            'recall': 0.0,
            'f1_score': 0.0,
            'count': 0
        })
        
        # Timestamp for last calculation
        self.last_calculation = None
        self.calculation_interval = 5.0  # Recalculate every 5 seconds
    
    def add_detection(self, detection: Dict):
        """
        Add a detection result to the history
        
        Args:
            detection: Dictionary containing detection data
                - label: str
                - confidence: float
                - bbox: [x, y, width, height]
                - timestamp: datetime
                - is_correct: bool (optional, for supervised learning)
        """
        # Add timestamp if not present
        if 'timestamp' not in detection:
            detection['timestamp'] = datetime.now(timezone.utc)
        
        # Add to history
        self.detection_history.append(detection)
        
        # Update class metrics
        label = detection.get('label', 'unknown')
        confidence = detection.get('confidence', 0.0)
        
        self.class_metrics[label]['count'] += 1
        self.confidence_history.append(confidence)
        
        # Mark for recalculation
        self.last_calculation = None
    
    def add_ground_truth(self, ground_truth: Dict):
        """
        Add ground truth data for supervised evaluation
        
        Args:
            ground_truth: Dictionary containing ground truth data
                - label: str
                - bbox: [x, y, width, height]
                - timestamp: datetime
        """
        if 'timestamp' not in ground_truth:
            ground_truth['timestamp'] = datetime.now(timezone.utc)
        
        self.ground_truth_history.append(ground_truth)
        self.last_calculation = None
    
    def add_performance_metrics(self, fps: float, inference_time: float):
        """Add performance metrics"""
        self.fps_history.append(fps)
        self.inference_time_history.append(inference_time)
    
    def calculate_metrics(self, force: bool = False) -> Dict[str, Any]:
        """
        Calculate current performance metrics
        
        Args:
            force: Force recalculation even if recent
            
        Returns:
            Dictionary containing all metrics
        """
        current_time = time.time()
        
        # Check if we need to recalculate
        if (not force and self.last_calculation and 
            current_time - self.last_calculation < self.calculation_interval):
            return self.current_metrics
        
        # Calculate basic metrics
        self._calculate_basic_metrics()
        
        # Calculate class-specific metrics
        self._calculate_class_metrics()
        
        # Calculate performance trends
        performance_trends = self._calculate_performance_trends()
        
        # Store performance snapshot
        snapshot = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'metrics': self.current_metrics.copy(),
            'class_metrics': dict(self.class_metrics),
            'performance_trends': performance_trends
        }
        self.performance_history.append(snapshot)
        
        self.last_calculation = current_time
        
        return {
            **self.current_metrics,
            'class_metrics': dict(self.class_metrics),
            'performance_trends': performance_trends,
            'history_size': len(self.detection_history)
        }
    
    def _calculate_basic_metrics(self):
        """Calculate basic precision, recall, F1 metrics"""
        if not self.detection_history:
            return
        
        # Count detections by confidence threshold
        confidence_thresholds = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
        threshold_metrics = {}
        
        for threshold in confidence_thresholds:
            tp, fp, fn, tn = self._calculate_confusion_matrix(threshold)
            
            precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
            
            threshold_metrics[threshold] = {
                'precision': precision,
                'recall': recall,
                'f1_score': f1,
                'tp': tp,
                'fp': fp,
                'fn': fn,
                'tn': tn
            }
        
        # Use threshold 0.5 for current metrics
        current_threshold = 0.5
        if current_threshold in threshold_metrics:
            metrics = threshold_metrics[current_threshold]
            self.current_metrics.update(metrics)
        
        # Store threshold metrics for curves
        self.current_metrics['threshold_curves'] = threshold_metrics
    
    def _calculate_confusion_matrix(self, confidence_threshold: float) -> Tuple[int, int, int, int]:
        """Calculate confusion matrix for given confidence threshold"""
        tp, fp, fn, tn = 0, 0, 0, 0
        
        # Count high-confidence detections
        high_conf_detections = [
            d for d in self.detection_history 
            if d.get('confidence', 0.0) >= confidence_threshold
        ]
        
        # For now, assume all detections are true positives if no ground truth
        # In a real implementation, you would compare with ground truth
        if self.ground_truth_history:
            # Compare with ground truth
            tp, fp, fn, tn = self._compare_with_ground_truth(high_conf_detections)
        else:
            # Estimate based on confidence and historical patterns
            tp = len([d for d in high_conf_detections if d.get('confidence', 0.0) > 0.7])
            fp = len([d for d in high_conf_detections if d.get('confidence', 0.0) <= 0.7])
            fn = 0  # Can't estimate without ground truth
            tn = 0  # Can't estimate without ground truth
        
        return tp, fp, fn, tn
    
    def _compare_with_ground_truth(self, detections: List[Dict]) -> Tuple[int, int, int, int]:
        """Compare detections with ground truth data"""
        tp, fp, fn, tn = 0, 0, 0, 0
        
        # Simple IoU-based matching
        for detection in detections:
            matched = False
            for gt in self.ground_truth_history:
                if self._calculate_iou(detection.get('bbox', []), gt.get('bbox', [])) > 0.5:
                    if detection.get('label') == gt.get('label'):
                        tp += 1
                    else:
                        fp += 1
                    matched = True
                    break
            
            if not matched:
                fp += 1
        
        # Count unmatched ground truth as false negatives
        for gt in self.ground_truth_history:
            matched = False
            for detection in detections:
                if self._calculate_iou(detection.get('bbox', []), gt.get('bbox', [])) > 0.5:
                    matched = True
                    break
            
            if not matched:
                fn += 1
        
        return tp, fp, fn, tn
    
    def _calculate_iou(self, bbox1: List[float], bbox2: List[float]) -> float:
        """Calculate Intersection over Union between two bounding boxes"""
        if len(bbox1) != 4 or len(bbox2) != 4:
            return 0.0
        
        x1, y1, w1, h1 = bbox1
        x2, y2, w2, h2 = bbox2
        
        # Calculate intersection
        x_left = max(x1, x2)
        y_top = max(y1, y2)
        x_right = min(x1 + w1, x2 + w2)
        y_bottom = min(y1 + h1, y2 + h2)
        
        if x_right < x_left or y_bottom < y_top:
            return 0.0
        
        intersection = (x_right - x_left) * (y_bottom - y_top)
        
        # Calculate union
        area1 = w1 * h1
        area2 = w2 * h2
        union = area1 + area2 - intersection
        
        return intersection / union if union > 0 else 0.0
    
    def _calculate_class_metrics(self):
        """Calculate metrics for each class"""
        if not self.detection_history:
            return
        
        # Group detections by class
        class_detections = defaultdict(list)
        for detection in self.detection_history:
            label = detection.get('label', 'unknown')
            class_detections[label].append(detection)
        
        # Calculate metrics for each class
        for label, detections in class_detections.items():
            if not detections:
                continue
            
            # Calculate average confidence
            confidences = [d.get('confidence', 0.0) for d in detections]
            avg_confidence = sum(confidences) / len(confidences)
            
            # Estimate precision based on confidence (simplified)
            high_conf_detections = [d for d in detections if d.get('confidence', 0.0) > 0.7]
            precision = len(high_conf_detections) / len(detections) if detections else 0.0
            
            # Estimate recall (simplified)
            recall = min(1.0, len(detections) / max(1, len(detections) * 0.8))
            
            # Calculate F1 score
            f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
            
            self.class_metrics[label].update({
                'precision': precision,
                'recall': recall,
                'f1_score': f1_score,
                'avg_confidence': avg_confidence,
                'count': len(detections)
            })
    
    def _calculate_performance_trends(self) -> Dict[str, Any]:
        """Calculate performance trends over time"""
        trends = {}
        
        # FPS trend
        if len(self.fps_history) >= 2:
            recent_fps = list(self.fps_history)[-10:]  # Last 10 measurements
            trends['fps'] = {
                'current': recent_fps[-1] if recent_fps else 0.0,
                'average': sum(recent_fps) / len(recent_fps),
                'trend': 'stable'
            }
            
            if len(recent_fps) >= 3:
                # Simple trend calculation
                first_half = sum(recent_fps[:len(recent_fps)//2]) / (len(recent_fps)//2)
                second_half = sum(recent_fps[len(recent_fps)//2:]) / (len(recent_fps)//2)
                
                if second_half > first_half * 1.1:
                    trends['fps']['trend'] = 'increasing'
                elif second_half < first_half * 0.9:
                    trends['fps']['trend'] = 'decreasing'
        
        # Inference time trend
        if len(self.inference_time_history) >= 2:
            recent_times = list(self.inference_time_history)[-10:]
            trends['inference_time'] = {
                'current': recent_times[-1] if recent_times else 0.0,
                'average': sum(recent_times) / len(recent_times),
                'trend': 'stable'
            }
        
        # Confidence trend
        if len(self.confidence_history) >= 2:
            recent_conf = list(self.confidence_history)[-20:]
            trends['confidence'] = {
                'current': recent_conf[-1] if recent_conf else 0.0,
                'average': sum(recent_conf) / len(recent_conf),
                'min': min(recent_conf) if recent_conf else 0.0,
                'max': max(recent_conf) if recent_conf else 0.0
            }
        
        return trends
    
    def get_performance_curves(self) -> Dict[str, Any]:
        """Get performance curves data for plotting"""
        if not self.current_metrics.get('threshold_curves'):
            self.calculate_metrics(force=True)
        
        curves = self.current_metrics.get('threshold_curves', {})
        
        # Prepare data for plotting
        thresholds = sorted(curves.keys())
        precision_values = [curves[t]['precision'] for t in thresholds]
        recall_values = [curves[t]['recall'] for t in thresholds]
        f1_values = [curves[t]['f1_score'] for t in thresholds]
        
        return {
            'thresholds': thresholds,
            'precision': precision_values,
            'recall': recall_values,
            'f1_score': f1_values,
            'pr_curve': list(zip(recall_values, precision_values)),  # For PR curve
            'roc_curve': self._generate_roc_curve()  # Simplified ROC curve
        }
    
    def _generate_roc_curve(self) -> List[Tuple[float, float]]:
        """Generate simplified ROC curve data"""
        # This is a simplified ROC curve generation
        # In practice, you would need true positive rates and false positive rates
        
        curves = self.current_metrics.get('threshold_curves', {})
        if not curves:
            return []
        
        # Use precision as TPR and (1 - precision) as FPR for demonstration
        roc_points = []
        for threshold, metrics in sorted(curves.items()):
            tpr = metrics['precision']  # Simplified
            fpr = 1 - metrics['precision']  # Simplified
            roc_points.append((fpr, tpr))
        
        return roc_points
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get a comprehensive metrics summary"""
        metrics = self.calculate_metrics()
        curves = self.get_performance_curves()
        
        return {
            'current_metrics': metrics,
            'performance_curves': curves,
            'class_performance': dict(self.class_metrics),
            'performance_history': list(self.performance_history)[-10:],  # Last 10 snapshots
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
    
    def reset(self):
        """Reset all metrics and history"""
        self.detection_history.clear()
        self.ground_truth_history.clear()
        self.performance_history.clear()
        self.fps_history.clear()
        self.inference_time_history.clear()
        self.confidence_history.clear()
        self.class_metrics.clear()
        self.last_calculation = None
        
        # Reset current metrics
        for key in self.current_metrics:
            if isinstance(self.current_metrics[key], (int, float)):
                self.current_metrics[key] = 0.0

# Global metrics calculator instance
metrics_calculator = MetricsCalculator()

def get_performance_metrics() -> Dict[str, Any]:
    """Get current performance metrics"""
    return metrics_calculator.get_metrics_summary()

def add_detection_result(detection: Dict):
    """Add detection result to metrics calculator"""
    metrics_calculator.add_detection(detection)

def add_performance_data(fps: float, inference_time: float):
    """Add performance data to metrics calculator"""
    metrics_calculator.add_performance_metrics(fps, inference_time) 