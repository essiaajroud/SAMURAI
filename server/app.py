# app.py - Main Flask application for the military detection server
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
import io
from PIL import Image
import numpy as np
import psutil
import random


# --- YOLO Detector Initialization ---
try:
    from yolo_detector import detector
    YOLO_AVAILABLE = detector.model is not None
    if YOLO_AVAILABLE:
        print("✅ YOLO detector loaded successfully.")
    else:
        print("⚠️ YOLO detector failed to load a model. YOLO features will be disabled.")
except ImportError as e:
    print(f"⚠️ YOLO detector could not be imported: {e}")
    print("   YOLO features will be disabled.")
    YOLO_AVAILABLE = False
    detector = None
except Exception as e:
    print(f"❌ An unexpected error occurred while loading the YOLO detector: {e}")
    YOLO_AVAILABLE = False
    detector = None
# --- Flask App Initialization ---
app = Flask(__name__)

# --- App Configuration ---
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///detection_history.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your-secret-key-here'

# --- Extensions Initialization ---
db = SQLAlchemy(app)
CORS(app)

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

    def to_dict(self):
        return {
            'id': self.object_id,
            'label': self.label,
            'confidence': self.confidence,
            'x': self.x,
            'y': self.y,
            'speed': self.speed,
            'distance': self.distance,
            'timestamp': self.timestamp.isoformat(),
            'historyId': self.history_id
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
            'id': self.object_id,
            'label': self.label,
            'startTime': self.start_time.isoformat(),
            'lastSeen': self.last_seen.isoformat(),
            'isActive': self.is_active
        }

class TrajectoryPoint(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    trajectory_id = db.Column(db.Integer, db.ForeignKey('trajectory.id'), nullable=False)
    x = db.Column(db.Float, nullable=False)
    y = db.Column(db.Float, nullable=False)
    speed = db.Column(db.Float)
    distance = db.Column(db.Float)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            'x': self.x,
            'y': self.y,
            'speed': self.speed,
            'distance': self.distance,
            'timestamp': self.timestamp.isoformat()
        }

# --- YOLO Detection Callback ---
def save_yolo_detection(detection_data):
    """Save a YOLO detection to the database dynamically."""
    try:
        with app.app_context():
            # Compute speed and distance if available
            speed = detection_data.get('speed')
            distance = detection_data.get('distance')
            # Create detection
            detection = Detection(
                object_id=detection_data['id'],
                label=detection_data['label'],
                confidence=detection_data['confidence'],
                x=detection_data['x'],
                y=detection_data['y'],
                speed=speed,
                distance=distance,
                history_id=f"yolo_{uuid.uuid4()}_{detection_data.get('frame_number', 0)}"
            )
            db.session.add(detection)
            # Update or create trajectory dynamically
            trajectory = Trajectory.query.filter_by(object_id=detection_data['id']).first()
            if trajectory:
                # Update existing trajectory
                trajectory.last_seen = datetime.now(timezone.utc)
                trajectory.is_active = True
            else:
                # Create new trajectory
                trajectory = Trajectory(
                    object_id=detection_data['id'],
                    label=detection_data['label']
                )
                db.session.add(trajectory)
                db.session.flush()  # To get trajectory ID
            # Add trajectory point
            trajectory_point = TrajectoryPoint(
                trajectory_id=trajectory.id,
                x=detection_data['x'],
                y=detection_data['y'],
                speed=speed,
                distance=distance
            )
            db.session.add(trajectory_point)
            db.session.commit()
            # Debug log
            print(f"✅ Detection saved: {detection_data['label']} (conf: {detection_data['confidence']:.2f}) at ({detection_data['x']:.1f}, {detection_data['y']:.1f})")
    except Exception as e:
        print(f"❌ Error saving detection: {e}")
        db.session.rollback()

# --- Set YOLO Callback if Available ---
if YOLO_AVAILABLE:
    detector.set_detection_callback(save_yolo_detection)

# --- API Routes (see rest of file for endpoints) ---
@app.route('/api/detections', methods=['POST'])
def save_detection():
    """Save a new detection."""
    try:
        data = request.json

        # Generate a unique history_id if not provided
        history_id = data.get('historyId') or f"api_{uuid.uuid4()}"

        # Save the detection
        detection = Detection(
            object_id=data['id'],
            label=data['label'],
            confidence=data['confidence'],
            x=data['x'],
            y=data['y'],
            speed=data.get('speed'),
            distance=data.get('distance'),
            history_id=history_id
        )
        db.session.add(detection)
        
        # Update or create trajectory
        trajectory = Trajectory.query.filter_by(object_id=data['id']).first()
        if trajectory:
            trajectory.last_seen = datetime.now(timezone.utc)
            trajectory.is_active = True
        else:
            trajectory = Trajectory(
                object_id=data['id'],
                label=data['label']
            )
            db.session.add(trajectory)
            db.session.flush()
        
        # Add trajectory point
        trajectory_point = TrajectoryPoint(
            trajectory_id=trajectory.id,
            x=data['x'],
            y=data['y'],
            speed=data.get('speed'),
            distance=data.get('distance')
        )
        db.session.add(trajectory_point)
        
        db.session.commit()
        
        # Return the complete detection for immediate display
        return jsonify({'message': 'Detection saved successfully', 'detection': detection.to_dict()}), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@app.route('/api/detections', methods=['GET'])
def get_detections():
    """Retrieve detections with filters."""
    try:
        # Filter parameters
        time_range = request.args.get('timeRange', '24h')
        confidence_threshold = float(request.args.get('confidence', 0.0))
        selected_class = request.args.get('class', 'all')
        limit = int(request.args.get('limit', 100))
        
        # Calculate time limit
        now = datetime.now(timezone.utc)
        if time_range == '1h':
            time_limit = now - timedelta(hours=1)
        elif time_range == '6h':
            time_limit = now - timedelta(hours=6)
        else:  # 24h by default
            time_limit = now - timedelta(hours=24)
        
        # Build query
        query = Detection.query.filter(Detection.timestamp >= time_limit)
        
        if confidence_threshold > 0:
            query = query.filter(Detection.confidence >= confidence_threshold)
        
        if selected_class != 'all':
            query = query.filter(Detection.label == selected_class)
        
        # Get detections
        detections = query.order_by(Detection.timestamp.desc()).limit(limit).all()
        
        return jsonify([detection.to_dict() for detection in detections])
        
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/trajectories', methods=['GET'])
def get_trajectories():
    """Retrieve trajectories with their points."""
    try:
        trajectories = Trajectory.query.all()
        result = []
        
        for trajectory in trajectories:
            trajectory_data = trajectory.to_dict()
            
            # Get trajectory points
            points = TrajectoryPoint.query.filter_by(trajectory_id=trajectory.id).all()
            trajectory_data['points'] = [point.to_dict() for point in points]
            
            # Calculate metrics
            if points:
                duration = (trajectory.last_seen - trajectory.start_time).total_seconds()
                total_distance = 0
                for i in range(1, len(points)):
                    dx = points[i].x - points[i-1].x
                    dy = points[i].y - points[i-1].y
                    total_distance += (dx**2 + dy**2)**0.5
                
                trajectory_data['duration'] = duration
                trajectory_data['totalDistance'] = total_distance
                trajectory_data['avgSpeed'] = total_distance / duration if duration > 0 else 0
                trajectory_data['pointCount'] = len(points)
            
            result.append(trajectory_data)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 400

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
        video_path = data.get('video_path')
        network_url = data.get('network_url')

        if not video_path and not network_url:
            return jsonify({'error': 'Either video_path or network_url is required'}), 400

        # The source is either the local path or the network URL
        stream_source = video_path if video_path else network_url
        
        thread = detector.start_streaming(stream_source)

        if thread is None:
            return jsonify({
                'error': 'Failed to start stream. Check server logs for details.',
                'is_running': False
            }), 500
        
        return jsonify({
            'message': 'Streaming started',
            'stream_source': stream_source,
            'is_running': detector.is_running
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400

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

        # The detector callback `save_yolo_detection` will be triggered inside `process_frame`
        # if detections are found. We just return the detections for immediate display.
        
        return jsonify({'detections': detections})

    except Exception as e:
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
    # This route now primarily serves streams started by `start_streaming`.
    # It might not be directly hit for network URLs if they are passed to a different player,
    # but it's essential for server-processed video files.
    
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

# Create tables on startup
with app.app_context():
    db.create_all()

@app.route('/api/logs', methods=['GET'])
def get_logs():
    try:
        with open('server.log', 'r') as f:
            lines = f.readlines()[-100:]
        return jsonify({'logs': lines})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/performance', methods=['GET'])
def get_performance():
    """
    Returns real-time performance data from the YOLO detector.
    """
    if not YOLO_AVAILABLE or not detector.is_running:
        return jsonify({
            "fps": 0,
            "inferenceTime": 0,
            "objectCount": 0
        })

    # Get metrics from the detector
    perf_metrics = detector.get_performance_metrics()

    # Get object count from the database (last 2 seconds for a more "current" feel)
    now = datetime.now(timezone.utc)
    two_seconds_ago = now - timedelta(seconds=2)
    object_count = db.session.query(Detection.object_id).filter(Detection.timestamp >= two_seconds_ago).distinct().count()

    # Add simulated metrics for now
    perf_metrics['detectionRate'] = 98.5 + random.uniform(-1.5, 1.5)
    perf_metrics['precision'] = 95.2 + random.uniform(-2.0, 2.0)
    perf_metrics['recall'] = 97.0 + random.uniform(-1.0, 1.0)
    perf_metrics['f1Score'] = 2 * (perf_metrics['precision'] * perf_metrics['recall']) / (perf_metrics['precision'] + perf_metrics['recall']) if (perf_metrics['precision'] + perf_metrics['recall']) > 0 else 0
    perf_metrics['idSwitchCount'] = random.randint(0, 5)
    perf_metrics['mota'] = 85.1 + random.uniform(-2.0, 2.0)
    perf_metrics['motp'] = 78.3 + random.uniform(-1.5, 1.5)
    perf_metrics['objectCount'] = object_count
    
    # Use hasattr for safety, as the error is mysterious
    if hasattr(detector, 'get_objects_by_class'):
        perf_metrics['objectsByClass'] = getattr(detector, 'get_objects_by_class')()
    else:
        perf_metrics['objectsByClass'] = {}

    return jsonify(perf_metrics)

@app.route('/api/system-metrics', methods=['GET'])
def get_system_metrics():
    """Returns system hardware metrics using psutil."""
    try:
        # Note: GPU metrics are complex and often require specific libraries (e.g., pynvml).
        # This is a simplified simulation.
        cpu_usage = psutil.cpu_percent(interval=0.1)
        ram_usage = psutil.virtual_memory().percent
        
        # Robust temperature check
        temps = psutil.sensors_temperatures()
        cpu_temp = random.uniform(50, 85) # Default fallback
        if temps and 'coretemp' in temps and temps['coretemp']:
            cpu_temp = temps['coretemp'][0].current
        
        return jsonify({
            "cpu": cpu_usage,
            "gpu": random.uniform(30, 70), # Simulated
            "ram": ram_usage,
            "tempCpu": cpu_temp,
            "tempGpu": random.uniform(60, 90), # Simulated
            "netIn": round(psutil.net_io_counters().bytes_recv / (1024*1024), 2), # MB received
            "netOut": round(psutil.net_io_counters().bytes_sent / (1024*1024), 2) # MB sent
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

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

@app.route('/api/detections/current', methods=['GET'])
def get_current_detections():
    """
    Returns the most recent detections for each object (by object_id).
    Dynamic with real-time filtering.
    """
    try:
        # Dynamic filtering parameters
        limit = int(request.args.get('limit', 10))
        confidence_threshold = float(request.args.get('confidence', 0.0))
        time_window = int(request.args.get('time_window', 5))  # X seconds of detections
        
        # Calculate time window
        now = datetime.now(timezone.utc)
        time_limit = now - timedelta(seconds=time_window)
        
        # For each object_id, take the most recent detection in the time window
        subquery = (
            db.session.query(
                Detection.object_id,
                db.func.max(Detection.timestamp).label('max_timestamp')
            )
            .filter(Detection.timestamp >= time_limit)
            .group_by(Detection.object_id)
            .subquery()
        )

        query = (
            db.session.query(Detection)
            .join(subquery, (Detection.object_id == subquery.c.object_id) & (Detection.timestamp == subquery.c.max_timestamp))
        )
        
        # Apply filters
        if confidence_threshold > 0:
            query = query.filter(Detection.confidence >= confidence_threshold)
        
        # Limit results
        detections = query.order_by(Detection.timestamp.desc()).limit(limit).all()

        # Adapt timestamp format for frontend (in ms since epoch)
        def detection_to_dict_with_epoch(d):
            dct = d.to_dict()
            try:
                dt = d.timestamp
                if isinstance(dt, str):
                    dt = datetime.fromisoformat(dt)
                dct['timestamp'] = int(dt.timestamp() * 1000)
                # Add dynamic metadata
                dct['age_seconds'] = (now - dt).total_seconds()
                dct['is_recent'] = dct['age_seconds'] <= 2  # Recent detection (< 2 seconds)
            except Exception:
                dct['timestamp'] = 0
                dct['age_seconds'] = 0
                dct['is_recent'] = False
            return dct

        result = [detection_to_dict_with_epoch(d) for d in detections]
        
        # Add metadata about the query
        response_data = {
            'detections': result,
            'metadata': {
                'total_detections': len(result),
                'time_window_seconds': time_window,
                'confidence_threshold': confidence_threshold,
                'query_timestamp': now.isoformat(),
                'is_dynamic': True
            }
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 400

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)