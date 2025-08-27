from .stream_routes import stream_bp
from .detection_routes import detection_bp
from .yolo_routes import yolo_bp
from .system_routes import system_bp


all_blueprints = [
    stream_bp,
    detection_bp,
    system_bp,
    yolo_bp
]