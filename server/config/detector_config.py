# Detection and tracking configuration
DETECTION_CONFIG = {
    'confidence_threshold': 0.5,
    'nms_threshold': 0.45,
    'input_size': (640, 640),
    'device': 'cuda:0',
    'max_detections': 100
}

TRACKING_CONFIG = {
    'max_age': 90,
    'min_hits': 5,
    'iou_threshold': 0.4,
    'use_appearance': True,
    'feature_similarity_threshold': 0.6
}

PERFORMANCE_CONFIG = {
    'batch_size': 1,
    'warmup_iterations': 10,
    'metrics_window': 100
}
