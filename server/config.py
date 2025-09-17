"""
config.py - Centralized configuration for the military detection server.
All dynamic parameters are defined here for easy management.
"""

import os
from datetime import timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
YOLO_TRACKER_CONFIG = os.path.join(BASE_DIR, 'botsort.yaml')

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'une-cle-secrete-difficile-a-deviner'
    """Base configuration for the server."""
    # Server configuration
    HOST = '0.0.0.0'
    PORT = 5000
    DEBUG = True

    ENABLE_LOGS = True

    # Database configuration
    DATABASE_PATH = 'instance/detection_history.db'
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'database.sqlite')}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # YOLO configuration
    YOLO_MODEL_PATH = os.path.join(BASE_DIR, 'models', 'best2.onnx')
    YOLO_CONFIDENCE_THRESHOLD = 0.5
    

    # Detection configuration
    DETECTION_CLEANUP_HOURS = 24  # Clean up detections after X hours
    DETECTION_LOW_CONFIDENCE_THRESHOLD = 0.3  # Threshold for cleaning up low-confidence detections
    DETECTION_EXPORT_LIMIT = 1000  # Limit for detection export

    # Trajectory configuration
    TRAJECTORY_INACTIVE_HOURS = 1  # Mark as inactive after X hours
    TRAJECTORY_POINT_CLEANUP_DAYS = 3  # Clean up trajectory points after X days

    # Streaming configuration
    STREAM_FPS = 30
    STREAM_FRAME_DELAY = 1.0 / STREAM_FPS
    
    
    # Time windows for statistics
    TIME_WINDOWS = {
        'last_second': timedelta(seconds=1),
        'last_minute': timedelta(minutes=1),
        'last_5_minutes': timedelta(minutes=5),
        'last_hour': timedelta(hours=1),
        'last_24h': timedelta(hours=24)
    }

    # Maintenance configuration
    MAINTENANCE_CLEANUP_INTERVAL_MINUTES = 30
    MAINTENANCE_OPTIMIZATION_INTERVAL_HOURS = 2
    MAINTENANCE_HEALTH_CHECK_INTERVAL_MINUTES = 15
    MAINTENANCE_BACKUP_TIME = "02:00"  # Daily backup time

    # Logging configuration
    LOG_LEVEL = 'INFO'
    LOG_FILE = 'server.log'
    LOG_MAX_SIZE = 10 * 1024 * 1024  # 10 MB
    LOG_BACKUP_COUNT = 5

    # Security configuration
    CORS_ORIGINS = ['http://localhost:3000', 'http://127.0.0.1:3000']
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max for uploads

    # Performance configuration
    MAX_DETECTIONS_PER_REQUEST = 1000
    DETECTION_CACHE_TTL_SECONDS = 60
    STATISTICS_CACHE_TTL_SECONDS = 30

    # ReID configuration
    WITH_REID = True  # Active le modèle ReID si True

    @classmethod
    def get_detection_filters(cls):
        """Return default detection filters."""
        return {
            'confidence_threshold': cls.YOLO_CONFIDENCE_THRESHOLD,
            'time_range': '24h',
            'limit': cls.MAX_DETECTIONS_PER_REQUEST
        }

    @classmethod
    def get_export_config(cls):
        """Return export configuration."""
        return {
            'max_detections': cls.DETECTION_EXPORT_LIMIT,
            'include_metadata': True,
            'include_trajectories': True,
            'format': 'json'
        }

    @classmethod
    def get_cleanup_config(cls):
        """Return cleanup configuration."""
        return {
            'detection_cleanup_hours': cls.DETECTION_CLEANUP_HOURS,
            'low_confidence_threshold': cls.DETECTION_LOW_CONFIDENCE_THRESHOLD,
            'trajectory_inactive_hours': cls.TRAJECTORY_INACTIVE_HOURS,
            'trajectory_point_cleanup_days': cls.TRAJECTORY_POINT_CLEANUP_DAYS
        }

class DevelopmentConfig(Config):
    """Configuration for development environment."""
    DEBUG = True
    LOG_LEVEL = 'DEBUG'

class ProductionConfig(Config):
    """Configuration for production environment."""
    DEBUG = False
    LOG_LEVEL = 'WARNING'
    HOST = '0.0.0.0'
    # Stricter production parameters
    DETECTION_CLEANUP_HOURS = 12  # More frequent cleanup
    MAINTENANCE_CLEANUP_INTERVAL_MINUTES = 15  # More frequent maintenance
    MAX_DETECTIONS_PER_REQUEST = 500  # Stricter limit

class TestingConfig(Config):
    """Configuration for testing environment."""
    DEBUG = True
    DATABASE_PATH = 'instance/test_detection_history.db'
    SQLALCHEMY_DATABASE_URI = f'sqlite:///{DATABASE_PATH}'
    LOG_LEVEL = 'DEBUG'

# Select default configuration based on environment

def get_config():
    """Return the configuration class based on the environment variable."""
    env = os.getenv('FLASK_ENV', 'development')
    if env == 'production':
        return ProductionConfig
    elif env == 'testing':
        return TestingConfig
    else:
        return DevelopmentConfig