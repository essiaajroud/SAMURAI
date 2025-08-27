import os
from flask import Flask
from .extensions import db, cors, METRICS
from prometheus_flask_exporter import PrometheusMetrics

def create_app(config_object_name='server.config.DevelopmentConfig'):
    """Application Factory: Crée et configure l'instance de l'application."""
    
    app = Flask(__name__, instance_relative_config=True)
    
    # Charger la configuration depuis le fichier/objet config
    app.config.from_object(config_object_name)
    
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # --- Initialiser les extensions ---
    db.init_app(app)
    cors.init_app(app, resources={r"/api/*": {"origins": app.config.get("CORS_ORIGINS", "*")}})
    PrometheusMetrics(app)
    app.metrics = METRICS
    initialize_components(app)
    
    # --- Enregistrer les Blueprints (routes) ---
    from .routes import all_blueprints
    for bp in all_blueprints:
        app.register_blueprint(bp)
        
    # --- Créer les tables de la BDD ---
    with app.app_context():
        db.create_all()
    

    return app

def initialize_components(app):
    """Initialise les composants non-Flask de l'application."""
   
    from .camera_location import CameraLocationManager
    from .alert_manager import AlertManager
    from .yolo_detector import YOLODetector
    from .utils.yolo_helpers import save_yolo_detection
    #from .services.stream_monitor import StreamMonitor
    
    app.camera_location_manager = CameraLocationManager(socketio=None)
    app.alert_manager = AlertManager(socketio=None)
    app.detector = None
    app.yolo_available = False
    app.zone_polygons = {'military': []}
    #app.stream_monitor = StreamMonitor()

    try:
        # Passer la configuration de l'app au constructeur de YOLO
        app.detector = YOLODetector(location_manager=app.camera_location_manager, config=app.config, app_for_context=app)
        app.yolo_available = app.detector.model is not None
        if app.yolo_available:
            app.detector.set_detection_callback(save_yolo_detection)
    except Exception as e:
        app.logger.error(f"❌ YOLO detector failed to load: {e}", exc_info=True)