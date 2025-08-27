"""
Ce fichier instancie les extensions Flask pour les rendre disponibles
dans toute l'application et éviter les imports circulaires.
"""
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from prometheus_client import Counter, Gauge

# Crée une instance pour la base de données
db = SQLAlchemy()
#Crée une instance pour la gestion des CORS
cors = CORS()

METRICS = {
    'detections_total': Counter(
        'detections_total', 
        'Total number of detections by class', 
        ['class_name']
    ),
    'fps_gauge': Gauge('yolo_fps', 'YOLO Detector FPS'),
    'inference_gauge': Gauge('yolo_inference_ms', 'YOLO Detector Inference Time (ms)'),
    'system_cpu_percent': Gauge('system_cpu_percent', 'System CPU usage percentage'),
    'system_ram_percent': Gauge('system_ram_percent', 'System RAM usage percentage'),
    'yolo_gpu_usage_percent': Gauge('yolo_gpu_usage_percent', 'YOLO detector GPU usage percentage')

}

