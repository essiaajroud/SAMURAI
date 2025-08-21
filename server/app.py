# Main Flask application for military detection system
# Handles API endpoints, database models, YOLO integration, and streaming

from flask import Flask, request, jsonify, send_from_directory, Response
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime, timedelta
import json
import os
import io
from PIL import Image
import numpy as np
import cv2
import time
from datetime import datetime, timezone
import uuid
import logging
from logging.handlers import RotatingFileHandler
import shapely.geometry
import osmnx as ox
import psutil
from alert_manager import alert_manager
from geolocation import calculate_object_gps
from camera_location import CameraLocationManager

from config import get_config
config = get_config()
ENABLE_LOGS = config.ENABLE_LOGS

# App initialization
app = Flask(__name__)
app.config.update({
    'SQLALCHEMY_DATABASE_URI': f"sqlite:///{os.path.join(app.instance_path, 'detection_history.db')}",
    'SQLALCHEMY_TRACK_MODIFICATIONS': False,
    'SECRET_KEY': 'your-secret-key-here'
})

# Core components initialization
db = SQLAlchemy(app)
CORS(app)
camera_location_manager = CameraLocationManager(socketio=None)

zone_polygons = {'military': []}

# --- YOLO Detector Initialization ---
try:
    from yolo_detector import detector, YOLODetector
    detector = YOLODetector(app=app, location_manager=camera_location_manager)
    YOLO_AVAILABLE = detector.model is not None
    app.logger.info("✅ YOLO detector loaded successfully.")
except Exception as e:
    app.logger.error(f"❌ YOLO detector failed to load: {e}")
    YOLO_AVAILABLE = False
    detector = None

# --- Logging ---
if not app.debug or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
    file_handler = RotatingFileHandler('server.log', maxBytes=1024 * 1024 * 10, backupCount=5, encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info('SAMURAI Server startup')

# --- Database Models ---
class Detection(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    object_id = db.Column(db.Integer, nullable=False)
    label = db.Column(db.String(50), nullable=False)
    confidence = db.Column(db.Float, nullable=False)
    x = db.Column(db.Float, nullable=False)
    y = db.Column(db.Float, nullable=False)
    speed = db.Column(db.Float)
    distance = db.Column(db.Float)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    history_id = db.Column(db.String(100), unique=True)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)

    def to_dict(self):
        return {
            'id': self.object_id, 'label': self.label, 'confidence': self.confidence,
            'x': self.x, 'y': self.y, 'speed': self.speed, 'distance': self.distance,
            'timestamp': self.timestamp.isoformat(), 'historyId': self.history_id,
            'latitude': self.latitude, 'longitude': self.longitude
        }

class Trajectory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    object_id = db.Column(db.Integer, nullable=False)
    label = db.Column(db.String(50), nullable=False)
    start_time = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    last_seen = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    is_active = db.Column(db.Boolean, default=True)

    def to_dict(self):
        return {
            'id': self.object_id, 'label': self.label,
            'startTime': self.start_time.isoformat(),
            'lastSeen': self.last_seen.isoformat(), 'isActive': self.is_active
        }

class TrajectoryPoint(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    trajectory_id = db.Column(db.Integer, db.ForeignKey('trajectory.id'), nullable=False)
    x = db.Column(db.Float, nullable=False)
    y = db.Column(db.Float, nullable=False)
    speed = db.Column(db.Float)
    distance = db.Column(db.Float)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    latitude = db.Column(db.Float, nullable=True) 
    longitude = db.Column(db.Float, nullable=True)

    def to_dict(self):
        return {
            'x': self.x, 'y': self.y, 'speed': self.speed, 'distance': self.distance,
            'timestamp': self.timestamp.isoformat(),
            'latitude': self.latitude, 'longitude': self.longitude
        }

def save_yolo_detection(detection_data):
    with app.app_context():
        try:
            object_id = detection_data.get('id')
            if object_id is None: return

            lat, lon = None, None
            if camera_location_manager.is_real_position:
                if camera_location_manager.current_position:
                    rover_pos = camera_location_manager.current_position
                    rover_heading = 90
                    frame_width = detection_data.get('frame_width', 640)
                    lat, lon = calculate_object_gps(
                        rover_lat=rover_pos.latitude, rover_lon=rover_pos.longitude, rover_heading=rover_heading,
                        detection_x=detection_data['x'], frame_width=frame_width, distance=detection_data.get('distance', 10)
                    )
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

            if lat is not None:
                alert_manager.check_threat(detection_data, (lat, lon))

            if ENABLE_LOGS:
                if lat:
                    gps_log = f"with REAL GPS ({lat:.4f}, {lon:.4f})"
                else:
                    gps_log = "(no real GPS from rover yet, position not saved)"
                app.logger.info(f"✅ Detection saved: {detection_data['label']} (ID: {object_id}) {gps_log}")

        except Exception as e:
            app.logger.error(f"❌ Error in save_yolo_detection: {e}")
            import traceback
            traceback.print_exc()
            db.session.rollback()

if YOLO_AVAILABLE:
    detector.set_detection_callback(save_yolo_detection)

def load_osm_zones(center_lat, center_lon, dist_m=5000):
    try:
        tags = {'landuse': 'military'}
        gdf_mil = ox.features.features_from_point((center_lat, center_lon), tags, dist=dist_m)
        zone_polygons['military'] = list(gdf_mil.geometry.values)
        if ENABLE_LOGS: app.logger.info(f"Loaded {len(zone_polygons['military'])} military zones from OSM.")
    except Exception as e:
        app.logger.error(f"Could not load OSM zones: {e}")

def point_in_military_zone(lat, lon):
    pt = shapely.geometry.Point(lon, lat)
    for poly in zone_polygons['military']:
        if poly is not None and poly.is_valid and poly.contains(pt):
            return True
    return False

# --- API Routes ---
@app.route('/api/detections', methods=['GET'])
def get_detections_history():
    try:
        time_range = request.args.get('timeRange', '24h')
        confidence_threshold = float(request.args.get('confidence', 0.0))
        selected_class = request.args.get('class', 'all')
        limit = int(request.args.get('limit', 1000))

        now = datetime.now(timezone.utc)
        time_map = {'1h': 1, '6h': 6, '24h': 24}
        time_limit = now - timedelta(hours=time_map.get(time_range, 24))

        query = db.session.query(Detection).filter(Detection.timestamp >= time_limit)
        if confidence_threshold > 0:
            query = query.filter(Detection.confidence >= confidence_threshold)
        if selected_class != 'all':
            query = query.filter(Detection.label == selected_class)

        detections = query.order_by(Detection.timestamp.desc()).all()
        result_list = [detection.to_dict() for detection in detections]
        return jsonify(result_list)
    except Exception as e:
        app.logger.error(f"Error in /api/detections (history): {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/detections/current', methods=['GET'])
def get_current_detections():
    try:
        time_window_seconds = int(request.args.get('time_window', 15))
        now = datetime.now(timezone.utc)
        time_limit = now - timedelta(seconds=time_window_seconds)

        subquery = db.session.query(
            Detection.object_id,
            db.func.max(Detection.timestamp).label('max_timestamp')
        ).filter(Detection.timestamp >= time_limit).group_by(Detection.object_id).subquery()

        query = db.session.query(Detection).join(
            subquery,
            db.and_(Detection.object_id == subquery.c.object_id, Detection.timestamp == subquery.c.max_timestamp)
        )

        detections = query.order_by(Detection.timestamp.desc()).all()
        result_list = [d.to_dict() for d in detections]
        
        response_data = {
            'detections': result_list,
            'metadata': { 'total_detections': len(result_list), 'query_timestamp': now.isoformat() }
        }
        return jsonify(response_data)

    except Exception as e:
        app.logger.error(f"Error in /api/detections/current: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/trajectories', methods=['GET'])
def get_trajectories():
    try:
        trajectories = Trajectory.query.all()
        result_object = {}
        for trajectory in trajectories:
            trajectory_data = trajectory.to_dict()
            points = TrajectoryPoint.query.filter_by(trajectory_id=trajectory.id).order_by(TrajectoryPoint.timestamp.asc()).all()
            trajectory_data['points'] = [point.to_dict() for point in points]
            
            if len(points) > 1:
                duration = (trajectory.last_seen - trajectory.start_time).total_seconds()
                def haversine(lat1, lon1, lat2, lon2):
                    from math import radians, sin, cos, sqrt, atan2
                    R = 6371000
                    dlat = radians(lat2 - lat1); dlon = radians(lon2 - lon1)
                    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
                    c = 2 * atan2(sqrt(a), sqrt(1-a))
                    return R * c
                
                total_distance = 0
                for i in range(1, len(points)):
                    p1, p2 = points[i-1], points[i]
                    if p1.latitude and p1.longitude and p2.latitude and p2.longitude:
                        total_distance += haversine(p1.latitude, p1.longitude, p2.latitude, p2.longitude)

                trajectory_data['duration'] = duration
                trajectory_data['totalDistance'] = total_distance
                trajectory_data['avgSpeed'] = total_distance / duration if duration > 0 else 0
                trajectory_data['pointCount'] = len(points)
            result_object[trajectory.object_id] = trajectory_data
        return jsonify(result_object)
    except Exception as e:
        app.logger.error(f"Error in /api/trajectories: {e}")
        return jsonify({'error': str(e)}), 500

# --- CORRECTION : Cette route renvoie maintenant la position dynamique ---
@app.route('/api/rover-location', methods=['GET'])
def get_rover_location():
    """Renvoie la position ACTUELLE et dynamique du rover depuis le manager."""
    if camera_location_manager.current_position:
        pos = camera_location_manager.current_position
        return jsonify({
            'latitude': pos.latitude,
            'longitude': pos.longitude
        })
    else:
        # Fournir une position par défaut si le manager n'a pas encore de données
        return jsonify({
            'latitude': 34.0,
            'longitude': 9.0
        })

# ... (Le reste des routes comme health, statistics, etc. n'a pas besoin de changer)
# --- Routes de statistiques, cleanup, export, health, yolo, etc. ---
@app.route('/api/statistics', methods=['GET'])
def get_statistics():
    """Retrieve global statistics."""
    try:
        now = datetime.now(timezone.utc)
        one_hour_ago = now - timedelta(hours=1)
        six_hours_ago = now - timedelta(hours=6)
        one_day_ago = now - timedelta(hours=24)
        
        # Count detections by period
        hourly_count = Detection.query.filter(Detection.timestamp >= one_hour_ago).count()
        six_hour_count = Detection.query.filter(Detection.timestamp >= six_hours_ago).count()
        daily_count = Detection.query.filter(Detection.timestamp >= one_day_ago).count()
        total_count = Detection.query.count()
        
        # Unique objects
        unique_objects = db.session.query(Detection.object_id).distinct().count()
        
        # Average confidence
        avg_confidence = db.session.query(db.func.avg(Detection.confidence)).scalar() or 0
        
        # Active trajectories
        active_trajectories = Trajectory.query.filter_by(is_active=True).count()
        
        return jsonify({
            'hourlyCount': hourly_count,
            'sixHourCount': six_hour_count,
            'dailyCount': daily_count,
            'totalDetections': total_count,
            'uniqueObjects': unique_objects,
            'avgConfidence': avg_confidence * 100,
            'activeTrajectories': active_trajectories
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 400
@app.route('/api/system-metrics', methods=['GET'])
def get_system_metrics():
    """Returns detailed, cross-platform system metrics using psutil."""
    try:
        # --- CORRECTION : Isoler l'appel à la batterie dans un try-except ---
        battery = None
        try:
            battery = psutil.sensors_battery()
        except Exception as e:
            app.logger.warning(f"Could not read battery sensor: {e}")

        cpu = psutil.cpu_percent(interval=0.1)
        ram = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        net = psutil.net_io_counters()

        data = {
            'cpu_percent': cpu,
            'ram_percent': ram.percent,
            'ram_used_MB': ram.used // 1024**2,
            'ram_total_MB': ram.total // 1024**2,
            'disk_percent': disk.percent,
            'disk_used_GB': round(disk.used / 1024**3, 2),
            'disk_total_GB': round(disk.total / 1024**3, 2),
            'net_sent_MB': round(net.bytes_sent / 1024**2, 2),
            'net_recv_MB': round(net.bytes_recv / 1024**2, 2),
            'running_processes': len(psutil.pids()),
            'battery_percent': battery.percent if battery else None,
            'battery_plugged': battery.power_plugged if battery else None,
            'battery_secsleft': battery.secsleft if battery else None,
        }
        return jsonify(data)
    except Exception as e:
        app.logger.error(f"Error in get_system_metrics: {e}")
        return jsonify({"error": str(e)}), 500
@app.route('/api/cleanup', methods=['POST'])
def cleanup_old_data():
    """Clean up old data (more than 24 hours)."""
    try:
        cutoff_date = datetime.now(timezone.utc) - timedelta(hours=24)
        
        # Delete old detections
        deleted_detections = Detection.query.filter(Detection.timestamp < cutoff_date).delete()
        
        # Mark inactive trajectories
        inactive_trajectories = Trajectory.query.filter(Trajectory.last_seen < cutoff_date).update({'is_active': False})
        
        db.session.commit()
        
        return jsonify({
            'message': 'Cleanup completed',
            'deleted_detections': deleted_detections,
            'inactive_trajectories': inactive_trajectories
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/cleanup/auto', methods=['POST'])
def auto_cleanup():
    """
    Intelligent auto-cleanup of data.
    Deletes old data and optimizes the database.
    """
    try:
        now = datetime.now(timezone.utc)
        
        # 1. Clean up very old detections (more than 7 days)
        week_ago = now - timedelta(days=7)
        old_detections_deleted = Detection.query.filter(Detection.timestamp < week_ago).delete()
        
        # 2. Clean up old low-confidence detections (more than 24 hours)
        day_ago = now - timedelta(hours=24)
        low_confidence_deleted = Detection.query.filter(
            Detection.timestamp < day_ago,
            Detection.confidence < 0.3
        ).delete()
        
        # 3. Mark inactive trajectories (no detection for 1 hour)
        hour_ago = now - timedelta(hours=1)
        inactive_trajectories = Trajectory.query.filter(
            Trajectory.last_seen < hour_ago,
            Trajectory.is_active == True
        ).update({'is_active': False})
        
        # 4. Clean up very old trajectory points (more than 3 days)
        three_days_ago = now - timedelta(days=3)
        old_trajectory_points = TrajectoryPoint.query.filter(
            TrajectoryPoint.timestamp < three_days_ago
        ).delete()
        
        db.session.commit()
        
        # 5. Calculate statistics after cleanup
        total_detections = Detection.query.count()
        total_trajectories = Trajectory.query.count()
        active_trajectories = Trajectory.query.filter_by(is_active=True).count()
        
        return jsonify({
            'message': 'Auto cleanup completed successfully',
            'cleanup_results': {
                'old_detections_deleted': old_detections_deleted,
                'low_confidence_deleted': low_confidence_deleted,
                'trajectories_marked_inactive': inactive_trajectories,
                'old_trajectory_points_deleted': old_trajectory_points
            },
            'current_stats': {
                'total_detections': total_detections,
                'total_trajectories': total_trajectories,
                'active_trajectories': active_trajectories
            },
            'cleanup_timestamp': now.isoformat()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@app.route('/api/export', methods=['POST'])
def export_data():
    """Export all data."""
    try:
        data = request.json
        export_date = datetime.now(timezone.utc)
        
        # Retrieve all data
        detections = Detection.query.all()
        trajectories = Trajectory.query.all()
        
        export_data = {
            'exportDate': export_date.isoformat(),
            'detectionHistory': [detection.to_dict() for detection in detections],
            'trajectoryHistory': {},
            'currentDetections': data.get('currentDetections', []),
            'filters': data.get('filters', {})
        }
        
        # Add trajectories with their points
        for trajectory in trajectories:
            points = TrajectoryPoint.query.filter_by(trajectory_id=trajectory.id).all()
            export_data['trajectoryHistory'][trajectory.object_id] = {
                'id': trajectory.object_id,
                'label': trajectory.label,
                'startTime': trajectory.start_time.isoformat(),
                'lastSeen': trajectory.last_seen.isoformat(),
                'points': [point.to_dict() for point in points]
            }
        
        # Save to a file
        filename = f"export_{export_date.strftime('%Y%m%d_%H%M%S')}.json"
        filepath = os.path.join('exports', filename)
        
        # Create exports directory if it doesn't exist
        os.makedirs('exports', exist_ok=True)
        
        with open(filepath, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        return jsonify({
            'message': 'Export completed',
            'filename': filename,
            'detectionCount': len(detections),
            'trajectoryCount': len(trajectories)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 400
    
@app.route('/api/export/daily', methods=['POST'])
def export_daily_data():
    """
    Exporte automatiquement les données des dernières 24 heures.
    """
    try:
        now = datetime.now(timezone.utc)
        start_time = now - timedelta(hours=24)
        
        # Récupérer les données des dernières 24 heures
        detections = Detection.query.filter(Detection.timestamp >= start_time).all()
        # On pourrait aussi filtrer les trajectoires, mais on les garde pour le contexte
        trajectories = Trajectory.query.all() 
        
        if not detections:
            return jsonify({'message': 'No new detections in the last 24 hours to export.'}), 200

        export_data_content = {
            'exportDate': now.isoformat(),
            'timeRange': {'start': start_time.isoformat(), 'end': now.isoformat()},
            'detectionHistory': [d.to_dict() for d in detections],
            'trajectoryHistory': {}
        }

        for trajectory in trajectories:
            points = TrajectoryPoint.query.filter(
                TrajectoryPoint.trajectory_id == trajectory.id,
                TrajectoryPoint.timestamp >= start_time
            ).all()
            if points: # N'inclure que les trajectoires avec des points récents
                t_data = trajectory.to_dict()
                t_data['points'] = [p.to_dict() for p in points]
                export_data_content['trajectoryHistory'][trajectory.object_id] = t_data

        filename = f"daily_export_{now.strftime('%Y%m%d')}.json"
        filepath = os.path.join('exports', filename)
        os.makedirs('exports', exist_ok=True)
        
        with open(filepath, 'w') as f:
            json.dump(export_data_content, f, indent=2)
        
        return jsonify({
            'message': f'Daily export completed successfully to {filename}',
            'detectionCount': len(detections)
        }), 200
        
    except Exception as e:
        app.logger.error(f"Error during daily export: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Check server health."""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'database': 'connected',
        'yolo_available': YOLO_AVAILABLE
    })

# YOLO and Video Routes
@app.route('/api/yolo/model', methods=['GET'])
def get_model_info():
    """Get YOLO model information."""
    if not YOLO_AVAILABLE:
        return jsonify({'error': 'YOLO not available'}), 400
    
    return jsonify(detector.get_model_info())

@app.route('/api/yolo/model', methods=['POST'])
def load_model():
    """Load a new YOLO model."""
    if not YOLO_AVAILABLE:
        return jsonify({'error': 'YOLO not available'}), 400
    
    try:
        data = request.json
        model_path = data.get('model_path', 'models/best.onnx')
        confidence = data.get('confidence', 0.5)
        
        detector.model_path = model_path
        detector.confidence_threshold = confidence
        detector.load_model()
        
        return jsonify({
            'message': 'Model loaded successfully',
            'model_path': model_path,
            'confidence': confidence
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/yolo/videos', methods=['GET'])
def get_available_videos():
    """Get list of available videos."""
    if not YOLO_AVAILABLE:
        return jsonify({'error': 'YOLO not available'}), 400
    
    videos = detector.get_available_videos()
    return jsonify({
        'videos': videos,
        'count': len(videos)
    })

@app.route('/api/yolo/process', methods=['POST'])
def process_video():
    """Process a video with YOLO."""
    if not YOLO_AVAILABLE:
        return jsonify({'error': 'YOLO not available'}), 400
    
    try:
        data = request.json
        video_path = data.get('video_path')
        save_results = data.get('save_results', True)
        
        if not video_path:
            return jsonify({'error': 'Video path required'}), 400
        
        # Process video in a separate thread
        import threading
        thread = threading.Thread(
            target=detector.process_video,
            args=(video_path, save_results)
        )
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'message': 'Video processing started',
            'video_path': video_path,
            'save_results': save_results
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/yolo/stream/start', methods=['POST'])
def start_streaming():
    """Start streaming from a video file or a network URL."""
    if not YOLO_AVAILABLE:
        return jsonify({'error': 'YOLO not available'}), 400
    
    try:
        data = request.json
        stream_source = data.get('video_path') or data.get('network_url')

        if not stream_source:
            return jsonify({'error': 'Source (video_path or network_url) is required'}), 400

        thread = detector.start_streaming(stream_source)

        if thread is None:
            last_logs = "Could not read server logs."
            try:
                with open('server.log', 'r', encoding='utf-8') as f:
                    # Lire toutes les lignes et garder les 10 dernières
                    last_logs = "".join(f.readlines()[-20:])
            except Exception as log_error:
                last_logs = f"Error reading logs: {log_error}"
            
            # Message d'erreur détaillé
            error_message = "Failed to start the stream. Please check that the URL is correct and accessible."
            
            return jsonify({
                'error': error_message,
                'is_running': False,
                'stream_source': stream_source,
                'last_logs': last_logs 
            }), 500
        
        return jsonify({
            'message': 'Streaming started',
            'stream_source': stream_source,
            'is_running': detector.is_running
        })
    except Exception as e:
        app.logger.error(f"Error in start_streaming: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/yolo/detect_frame', methods=['POST'])
def detect_frame():
    """Process a single frame for detection."""
    if not YOLO_AVAILABLE:
        return jsonify({'error': 'YOLO not available'}), 400

    if 'frame' not in request.files:
        return jsonify({'error': 'No frame provided in the request'}), 400

    try:
        frame_file = request.files['frame']
        
        # Read the image file
        image_bytes = frame_file.read()
        image = Image.open(io.BytesIO(image_bytes))
        
        # Convert to numpy array (OpenCV format)
        frame_np = np.array(image)
        
        # Process the frame using the detector
        detections = detector.process_frame(frame_np)

        return jsonify({'detections': detections})

    except Exception as e:
        if ENABLE_LOGS:
            print(f"Error processing frame: {e}")
        return jsonify({'error': 'Failed to process frame'}), 500


@app.route('/api/yolo/stream/stop', methods=['POST'])
def stop_streaming():
    """Stop streaming."""
    if not YOLO_AVAILABLE:
        return jsonify({'error': 'YOLO not available'}), 400
    
    try:
        detector.stop_streaming()
        return jsonify({
            'message': 'Streaming stopped',
            'is_running': detector.is_running
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/yolo/stream/status', methods=['GET'])
def get_streaming_status():
    """Get streaming status."""
    if not YOLO_AVAILABLE:
        return jsonify({'error': 'YOLO not available'}), 400
    
    return jsonify({
        'is_running': detector.is_running,
        'current_video': detector.current_video
    })

@app.route('/api/yolo/upload-video', methods=['POST'])
def upload_video():
    """Upload a video."""
    if not YOLO_AVAILABLE:
        return jsonify({'error': 'YOLO not available'}), 400
    
    try:
        if 'video' not in request.files:
            return jsonify({'error': 'No video file provided'}), 400
        
        file = request.files['video']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Check file extension
        allowed_extensions = {'mp4', 'avi', 'mov', 'mkv'}
        if not file.filename.lower().endswith(tuple(allowed_extensions)):
            return jsonify({'error': 'Unsupported file format'}), 400
        
        # Save the file
        filename = file.filename
        filepath = os.path.join('videos', filename)
        file.save(filepath)
        
        return jsonify({
            'message': 'Video uploaded successfully',
            'filename': filename,
            'filepath': filepath
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/yolo/upload-model', methods=['POST'])
def upload_model():
    """Upload a YOLO model."""
    if not YOLO_AVAILABLE:
        return jsonify({'error': 'YOLO not available'}), 400
    
    try:
        if 'model' not in request.files:
            return jsonify({'error': 'No model file provided'}), 400
        
        file = request.files['model']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Check file extension
        if not file.filename.lower().endswith('.pt'):
            return jsonify({'error': 'Unsupported file format (.pt required)'}), 400
        
        # Save the file
        filename = file.filename
        filepath = os.path.join('models', filename)
        file.save(filepath)
        
        return jsonify({
            'message': 'Model uploaded successfully',
            'filename': filename,
            'filepath': filepath
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400

# Route to serve static videos
@app.route('/videos/<path:filename>')
def serve_video(filename):
    # Optional: force correct mimetype for mp4
    if filename.lower().endswith('.mp4'):
        return send_from_directory('videos', filename, mimetype='video/mp4')
    return send_from_directory('videos', filename)

@app.route('/video_feed')
def video_feed():
    # Check if streaming is active
    if not YOLO_AVAILABLE or not detector.is_running:
        # If not running, generate a placeholder image dynamically
        img = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.putText(img, 'Stream Offline', (200, 240), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        _, jpeg = cv2.imencode('.jpg', img)
        return Response(jpeg.tobytes(), mimetype='image/jpeg')

    return Response(
        detector.generate_stream_frames(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )

@app.route('/api/logs', methods=['GET'])
def get_logs():
    try:
        # Check if the log file exists before trying to open it
        if not os.path.exists('server.log'):
            return jsonify({'logs': ['Log file not yet created.']})

        with open('server.log', 'r', encoding='utf-8') as f:
            lines = f.readlines()[-100:]
        return jsonify({'logs': lines})
    except Exception as e:
        # Log the error for debugging purposes
        app.logger.error(f"Error reading log file: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/performance', methods=['GET'])
def get_performance():
    """
    Returns real-time performance data from the YOLO detector.
    """
    if not YOLO_AVAILABLE :
        return jsonify({
            "fps": 0,
            "inferenceTime": 0,
            "objectCount": 0
        })

    # Get metrics from the detector
    perf_metrics = detector.get_performance_metrics() if hasattr(detector, 'get_performance_metrics') else {}

    print(f"DEBUG - Sending performance metrics: {perf_metrics}")


    # Get object count from the database (last 2 seconds for a more "current" feel)
    now = datetime.now(timezone.utc)
    two_seconds_ago = now - timedelta(seconds=2)
    object_count = db.session.query(Detection.object_id).filter(Detection.timestamp >= two_seconds_ago).distinct().count()

    try:
        with app.app_context():
            tracks = db.session.query(Trajectory).all()
            lifetimes = []
            all_points = []
            for t in tracks:
                points = db.session.query(TrajectoryPoint).filter_by(trajectory_id=t.id).all()
                lifetimes.append(len(points))
                all_points.append(points)
            
            # Calculs avec NumPy
            np_avg_track_lifetime = np.mean(lifetimes) if lifetimes else 0.0
            np_median_track_lifetime = np.median(lifetimes) if lifetimes else 0.0

            motp_list = []
            for points in all_points:
                if len(points) > 1:
                    dists = [((points[i].x - points[i-1].x)**2 + (points[i].y - points[i-1].y)**2)**0.5 for i in range(1, len(points))]
                    motp_list.extend(dists)
            np_motp = np.mean(motp_list) if motp_list else 0.0

            # Ajout au dictionnaire en convertissant explicitement avec float()
            perf_metrics['avgTrackLifetime'] = float(np_avg_track_lifetime)
            perf_metrics['medianTrackLifetime'] = float(np_median_track_lifetime)
            perf_metrics['MOTP'] = float(np_motp)
            
            # Les autres métriques qui n'utilisent pas NumPy peuvent être ajoutées directement
            short_tracks = sum(1 for l in lifetimes if l < 10)
            long_tracks = sum(1 for l in lifetimes if l > 60)
            perf_metrics['fragmentationRate'] = short_tracks / len(lifetimes) if lifetimes else 0
            perf_metrics['persistenceScore'] = long_tracks / len(lifetimes) if lifetimes else 0
            

    except Exception as e:
        print(f"❌ Error during database metric calculation: {e}")

    print(f"DEBUG - FINAL metrics sent to frontend: {perf_metrics}")

    return jsonify(perf_metrics)

@app.route('/api/statistics/realtime', methods=['GET'])
def get_realtime_statistics():
    """
    Returns real-time statistics for the dashboard.
    Dynamic with real-time calculations.
    """
    try:
        now = datetime.now(timezone.utc)
        
        # Time windows for statistics
        windows = {
            'last_second': now - timedelta(seconds=1),
            'last_minute': now - timedelta(minutes=1),
            'last_5_minutes': now - timedelta(minutes=5),
            'last_hour': now - timedelta(hours=1),
            'last_24h': now - timedelta(hours=24)
        }
        
        # Calculate statistics for each window
        stats = {}
        for window_name, time_limit in windows.items():
            detections = Detection.query.filter(Detection.timestamp >= time_limit).all()
            
            if detections:
                # Basic statistics
                count = len(detections)
                avg_confidence = sum(d.confidence for d in detections) / count
                
                # Unique objects
                unique_objects = len(set(d.object_id for d in detections))
                
                # Detected classes
                classes = {}
                for d in detections:
                    classes[d.label] = classes.get(d.label, 0) + 1
                
                # Average speed (if available)
                speeds = [d.speed for d in detections if d.speed is not None]
                avg_speed = sum(speeds) / len(speeds) if speeds else 0
                
                stats[window_name] = {
                    'detection_count': count,
                    'unique_objects': unique_objects,
                    'avg_confidence': avg_confidence,
                    'avg_speed': avg_speed,
                    'classes': classes,
                    'most_common_class': max(classes.items(), key=lambda x: x[1])[0] if classes else None
                }
            else:
                stats[window_name] = {
                    'detection_count': 0,
                    'unique_objects': 0,
                    'avg_confidence': 0,
                    'avg_speed': 0,
                    'classes': {},
                    'most_common_class': None
                }
        
        # Global statistics
        total_detections = Detection.query.count()
        total_trajectories = Trajectory.query.count()
        active_trajectories = Trajectory.query.filter_by(is_active=True).count()
        
        # Recent trajectories (created in the last hour)
        recent_trajectories = Trajectory.query.filter(
            Trajectory.start_time >= now - timedelta(hours=1)
        ).count()
        
        response_data = {
            'windows': stats,
            'global': {
                'total_detections': total_detections,
                'total_trajectories': total_trajectories,
                'active_trajectories': active_trajectories,
                'recent_trajectories': recent_trajectories
            },
            'metadata': {
                'query_timestamp': now.isoformat(),
                'is_dynamic': True,
                'system_status': 'running' if YOLO_AVAILABLE and detector.is_running else 'stopped'
            }
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 400
    
@app.route('/api/update_rover_location', methods=['POST'])
def update_rover_location():
    """
    Endpoint pour que le téléphone/rover mette à jour sa position GPS.
    """
    try:
        data = request.get_json() 
        if not data or 'latitude' not in data or 'longitude' not in data:
            return jsonify({'error': "Invalid or missing JSON payload."}), 400
        
        lat = float(data['latitude'])
        lon = float(data['longitude'])
        camera_location_manager.update_position(lat=lat, lon=lon)
        
        if ENABLE_LOGS:
            app.logger.info(f"🛰️ Rover position updated via API: ({lat}, {lon})")
        return jsonify({'message': 'Location updated successfully.'}), 200
        
    except (json.JSONDecodeError, ValueError, TypeError):
        return jsonify({'error': 'Invalid data format. Ensure latitude and longitude are numbers.'}), 400
    except Exception as e:
        app.logger.error(f"Error updating rover location: {e}")
        return jsonify({'error': 'An internal error occurred.'}), 500

@app.route('/api/alerts', methods=['GET'])
def get_alerts():
    """Génère des alertes basées sur les détections récentes et les zones OSM."""
    try:
        if not camera_location_manager.current_position:
            return jsonify({'alerts': [], 'message': 'Rover position not yet available.'})

        rover_pos = camera_location_manager.current_position
        load_osm_zones(rover_pos.latitude, rover_pos.longitude)

        time_limit = datetime.now(timezone.utc) - timedelta(minutes=2)
        recent_detections = Detection.query.filter(Detection.timestamp >= time_limit).all()

        alerts = []
        for d in recent_detections:
            if not (d.latitude and d.longitude):
                continue
            
            is_weapon = any(w in d.label.lower() for w in ['weapon', 'gun', 'rifle'])
            
            if is_weapon:
                in_mil = point_in_military_zone(d.latitude, d.longitude)
                if not in_mil:
                    alerts.append({
                        'type': 'danger',
                        'message': f"Weapon detected in non-military area (ID {d.object_id})",
                        'lat': d.latitude, 'lon': d.longitude, 'color': 'red'
                    })
                else:
                     alerts.append({
                        'type': 'secure',
                        'message': f"Weapon detected in military zone (ID {d.object_id})",
                        'lat': d.latitude, 'lon': d.longitude, 'color': 'green'
                    })
        return jsonify({'alerts': alerts})
    except Exception as e:
        app.logger.error(f"Error in /api/alerts: {e}")
        return jsonify({'error': str(e)}), 500

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)