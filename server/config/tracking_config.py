"""
Configuration settings for BotSORT tracking system.
Includes all parameters for detection and tracking optimization.
"""

BOTSORT_CONFIG = {
    # Core tracking parameters
    'tracker_type': 'botsort',
    'track_high_thresh': 0.7,    # High confidence threshold for reliable tracks
    'track_low_thresh': 0.4,     # Low confidence threshold for maintaining tracks
    'new_track_thresh': 0.3,     # Threshold for initializing new tracks
    'track_buffer': 120,         # Frames to keep track alive without detection
    'match_thresh': 0.8,         # IOU threshold for matching
    
    # Motion and Appearance
    'gmc_method': 'sparseOptFlow', # Global Motion Compensation method
    'with_reid': False,            # Enable ReID features
    
    
    # Track Management
    'min_hits': 5,               # Minimum detections before track confirmation
    'max_age': 90,               # Maximum frames to keep lost tracks
    'motion_weight': 0.2,        # Weight for motion model in matching
    'appearance_weight': 0.8,    # Weight for appearance model in matching
    
    # Association Metrics
    'proximity_thresh': 0.6,     # Spatial distance threshold
    'appearance_thresh': 0.4,    # Feature similarity threshold
    
    # System Settings
    'frame_rate': 30,           # Target frame rate for processing
    'gpu_enabled': True,        # Enable GPU acceleration
    'batch_size': 1            # Batch size for processing
}

# Detection Configuration
DETECTION_CONFIG = {
    'conf_thres': 0.5,          # Confidence threshold for detections
    'iou_thres': 0.45,          # NMS IOU threshold
    'classes': None,            # Filter by class
    'max_det': 100             # Maximum detections per frame
}

# Logging Configuration
LOGGING_CONFIG = {
    'enable_debug': False,
    'save_tracking_results': True,
    'log_metrics': True
}
