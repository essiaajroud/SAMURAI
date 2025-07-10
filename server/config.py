"""
Configuration centralisée pour le serveur de détection militaire.
Tous les paramètres dynamiques sont définis ici.
"""

import os
from datetime import timedelta

class Config:
    """Configuration de base"""
    
    # Configuration du serveur
    HOST = '0.0.0.0'
    PORT = 5000
    DEBUG = True
    
    # Configuration de la base de données
    DATABASE_PATH = 'instance/detection_history.db'
    SQLALCHEMY_DATABASE_URI = f'sqlite:///{DATABASE_PATH}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Configuration YOLO
    YOLO_MODEL_PATH = 'models/best.onnx'
    YOLO_CONFIDENCE_THRESHOLD = 0.5
    YOLO_VIDEOS_DIR = 'videos'
    
    # Configuration des détections
    DETECTION_CLEANUP_HOURS = 24  # Nettoyer les détections après X heures
    DETECTION_LOW_CONFIDENCE_THRESHOLD = 0.3  # Seuil pour nettoyer les détections de faible confiance
    DETECTION_EXPORT_LIMIT = 1000  # Limite pour l'export des détections
    
    # Configuration des trajectoires
    TRAJECTORY_INACTIVE_HOURS = 1  # Marquer comme inactif après X heures
    TRAJECTORY_POINT_CLEANUP_DAYS = 3  # Nettoyer les points après X jours
    
    # Configuration du streaming
    STREAM_FPS = 30
    STREAM_FRAME_DELAY = 0.033  # ~30 FPS
    
    # Configuration des fenêtres temporelles pour les statistiques
    TIME_WINDOWS = {
        'last_second': timedelta(seconds=1),
        'last_minute': timedelta(minutes=1),
        'last_5_minutes': timedelta(minutes=5),
        'last_hour': timedelta(hours=1),
        'last_24h': timedelta(hours=24)
    }
    
    # Configuration de la maintenance
    MAINTENANCE_CLEANUP_INTERVAL_MINUTES = 30
    MAINTENANCE_OPTIMIZATION_INTERVAL_HOURS = 2
    MAINTENANCE_HEALTH_CHECK_INTERVAL_MINUTES = 15
    MAINTENANCE_BACKUP_TIME = "02:00"  # Heure de sauvegarde quotidienne
    
    # Configuration des logs
    LOG_LEVEL = 'INFO'
    LOG_FILE = 'server.log'
    LOG_MAX_SIZE = 10 * 1024 * 1024  # 10 MB
    LOG_BACKUP_COUNT = 5
    
    # Configuration de sécurité
    CORS_ORIGINS = ['http://localhost:3000', 'http://127.0.0.1:3000']
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max pour les uploads
    
    # Configuration des performances
    MAX_DETECTIONS_PER_REQUEST = 1000
    DETECTION_CACHE_TTL_SECONDS = 60
    STATISTICS_CACHE_TTL_SECONDS = 30
    
    @classmethod
    def get_detection_filters(cls):
        """Retourne les filtres de détection par défaut"""
        return {
            'confidence_threshold': cls.YOLO_CONFIDENCE_THRESHOLD,
            'time_range': '24h',
            'limit': cls.MAX_DETECTIONS_PER_REQUEST
        }
    
    @classmethod
    def get_export_config(cls):
        """Retourne la configuration d'export"""
        return {
            'max_detections': cls.DETECTION_EXPORT_LIMIT,
            'include_metadata': True,
            'include_trajectories': True,
            'format': 'json'
        }
    
    @classmethod
    def get_cleanup_config(cls):
        """Retourne la configuration de nettoyage"""
        return {
            'detection_cleanup_hours': cls.DETECTION_CLEANUP_HOURS,
            'low_confidence_threshold': cls.DETECTION_LOW_CONFIDENCE_THRESHOLD,
            'trajectory_inactive_hours': cls.TRAJECTORY_INACTIVE_HOURS,
            'trajectory_point_cleanup_days': cls.TRAJECTORY_POINT_CLEANUP_DAYS
        }

class DevelopmentConfig(Config):
    """Configuration pour le développement"""
    DEBUG = True
    LOG_LEVEL = 'DEBUG'

class ProductionConfig(Config):
    """Configuration pour la production"""
    DEBUG = False
    LOG_LEVEL = 'WARNING'
    HOST = '0.0.0.0'
    
    # Paramètres de production plus stricts
    DETECTION_CLEANUP_HOURS = 12  # Nettoyage plus fréquent
    MAINTENANCE_CLEANUP_INTERVAL_MINUTES = 15  # Maintenance plus fréquente
    MAX_DETECTIONS_PER_REQUEST = 500  # Limite plus stricte

class TestingConfig(Config):
    """Configuration pour les tests"""
    DEBUG = True
    DATABASE_PATH = 'instance/test_detection_history.db'
    SQLALCHEMY_DATABASE_URI = f'sqlite:///{DATABASE_PATH}'
    LOG_LEVEL = 'DEBUG'

# Configuration par défaut selon l'environnement
def get_config():
    """Retourne la configuration selon l'environnement"""
    env = os.getenv('FLASK_ENV', 'development')
    
    if env == 'production':
        return ProductionConfig
    elif env == 'testing':
        return TestingConfig
    else:
        return DevelopmentConfig 