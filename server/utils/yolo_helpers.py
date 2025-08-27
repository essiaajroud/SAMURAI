"""
Fonctions utilitaires liées au traitement des résultats de YOLO.
"""
from flask import current_app
from ..models import Detection, Trajectory, TrajectoryPoint
from ..extensions import db, METRICS
from .geolocation import calculate_object_gps
import uuid
from datetime import datetime, timezone

def save_yolo_detection(detection_data):
    """
    Sauvegarde une détection de YOLO dans la base de données, met à jour les
    trajectoires et incrémente les métriques Prometheus.
    Cette fonction est conçue pour être appelée comme un callback depuis le détecteur.
    """
    app = current_app._get_current_object()
    with app.app_context():
        try:
            camera_location_manager = app.camera_location_manager
            alert_manager = app.alert_manager
            metrics = app.metrics
            object_id = detection_data.get('id')
            if object_id is None: 
                return

            lat, lon = None, None
            if camera_location_manager and camera_location_manager.is_real_position:
                rover_pos = camera_location_manager.current_position
                rover_heading = 90  # Valeur par défaut, à améliorer plus tard
                frame_width = detection_data.get('frame_width', 640)
                distance = detection_data.get('distance', 10)
                lat, lon = calculate_object_gps(
                    rover_lat=rover_pos.latitude, rover_lon=rover_pos.longitude, rover_heading=rover_heading,
                    detection_x=detection_data['x'], frame_width=frame_width, distance=detection_data.get('distance', 10)
                )

            # --- Logique de la Base de Données ---
            trajectory = Trajectory.query.filter_by(object_id=object_id).first()
            if not trajectory:
                trajectory = Trajectory(object_id=object_id, label=detection_data.get('label'))
                db.session.add(trajectory)
                db.session.flush()

            trajectory.last_seen = datetime.now(timezone.utc)
            trajectory.is_active = True
            
            trajectory_point = TrajectoryPoint(
                trajectory_id=trajectory.id, x=detection_data.get('x'), y=detection_data.get('y'),
                speed=detection_data.get('speed'), distance=detection_data.get('distance'),
                latitude=lat, longitude=lon
            )
            db.session.add(trajectory_point)

            detection = Detection(
                object_id=detection_data['id'], label=detection_data['label'], confidence=detection_data['confidence'],
                x=detection_data['x'], y=detection_data['y'], speed=trajectory_point.speed,
                distance=trajectory_point.distance, history_id=f"yolo_{uuid.uuid4()}",
                latitude=lat, longitude=lon
            )
            db.session.add(detection)
            
            db.session.commit()

            METRICS['detections_total'].labels(
                class_name=detection_data.get('label', 'unknown')
            ).inc()


            if lat is not None and alert_manager:
                alert_manager.check_threat(detection_data, (lat, lon))

            if lat:
                gps_log = f"with REAL GPS ({lat:.4f}, {lon:.4f})"
            else:
                gps_log = "(no real GPS from rover yet, position not saved)"
            current_app.logger.info(f"✅ Detection saved: {detection_data['label']} (ID: {object_id}) {gps_log}")

        except Exception as e:
            exc_info=True
            current_app.logger.error(f"❌ Error in save_yolo_detection: {e}", exc_info=exc_info)
            db.session.rollback()