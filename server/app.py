from flask import Flask, request, jsonify, send_from_directory, Response
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime, timedelta
import json
import os
import time
from datetime import datetime, timezone

import uuid



# Import du détecteur YOLO
try:
    from yolo_detector import detector
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False
    print("⚠️ Module YOLO non disponible")

app = Flask(__name__)

# Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///detection_history.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your-secret-key-here'

# Initialiser les extensions
db = SQLAlchemy(app)
CORS(app)

# Remove logging configuration and log statements

# Modèles de base de données
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

# Fonction de callback pour les détections YOLO
def save_yolo_detection(detection_data):
    """Sauvegarde une détection YOLO dans la base de données"""
    try:
        with app.app_context():
            detection = Detection(
                object_id=detection_data['id'],
                label=detection_data['label'],
                confidence=detection_data['confidence'],
                x=detection_data['x'],
                y=detection_data['y'],
                history_id=f"yolo_{uuid.uuid4()}"  # Utilisation d'un UUID unique
            )
            db.session.add(detection)
            db.session.commit()
    except Exception as e:
        print(f"❌ Erreur lors de la sauvegarde de la détection: {e}")

# Configurer le callback si YOLO est disponible
if YOLO_AVAILABLE:
    detector.set_detection_callback(save_yolo_detection)

# Routes API
@app.route('/api/detections', methods=['POST'])
def save_detection():
    """Sauvegarder une nouvelle détection"""
    try:
        data = request.json

        # Générer un history_id unique si non fourni
        history_id = data.get('historyId') or f"api_{uuid.uuid4()}"

        # Sauvegarder la détection
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
        
        # Mettre à jour ou créer la trajectoire
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
        
        # Ajouter le point de trajectoire
        trajectory_point = TrajectoryPoint(
            trajectory_id=trajectory.id,
            x=data['x'],
            y=data['y'],
            speed=data.get('speed'),
            distance=data.get('distance')
        )
        db.session.add(trajectory_point)
        
        db.session.commit()
        
        # Retourner la détection complète pour affichage immédiat
        return jsonify({'message': 'Detection saved successfully', 'detection': detection.to_dict()}), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@app.route('/api/detections', methods=['GET'])
def get_detections():
    """Récupérer les détections avec filtres"""
    try:
        # Paramètres de filtrage
        time_range = request.args.get('timeRange', '24h')
        confidence_threshold = float(request.args.get('confidence', 0.0))
        selected_class = request.args.get('class', 'all')
        limit = int(request.args.get('limit', 100))
        
        # Calculer la date limite
        now = datetime.now(timezone.utc)
        if time_range == '1h':
            time_limit = now - timedelta(hours=1)
        elif time_range == '6h':
            time_limit = now - timedelta(hours=6)
        else:  # 24h par défaut
            time_limit = now - timedelta(hours=24)
        
        # Construire la requête
        query = Detection.query.filter(Detection.timestamp >= time_limit)
        
        if confidence_threshold > 0:
            query = query.filter(Detection.confidence >= confidence_threshold)
        
        if selected_class != 'all':
            query = query.filter(Detection.label == selected_class)
        
        # Récupérer les détections
        detections = query.order_by(Detection.timestamp.desc()).limit(limit).all()
        
        return jsonify([detection.to_dict() for detection in detections])
        
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/trajectories', methods=['GET'])
def get_trajectories():
    """Récupérer les trajectoires avec leurs points"""
    try:
        trajectories = Trajectory.query.all()
        result = []
        
        for trajectory in trajectories:
            trajectory_data = trajectory.to_dict()
            
            # Récupérer les points de trajectoire
            points = TrajectoryPoint.query.filter_by(trajectory_id=trajectory.id).all()
            trajectory_data['points'] = [point.to_dict() for point in points]
            
            # Calculer les métriques
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
    """Récupérer les statistiques globales"""
    try:
        now = datetime.now(timezone.utc)
        one_hour_ago = now - timedelta(hours=1)
        six_hours_ago = now - timedelta(hours=6)
        one_day_ago = now - timedelta(hours=24)
        
        # Compter les détections par période
        hourly_count = Detection.query.filter(Detection.timestamp >= one_hour_ago).count()
        six_hour_count = Detection.query.filter(Detection.timestamp >= six_hours_ago).count()
        daily_count = Detection.query.filter(Detection.timestamp >= one_day_ago).count()
        total_count = Detection.query.count()
        
        # Objets uniques
        unique_objects = db.session.query(Detection.object_id).distinct().count()
        
        # Confiance moyenne
        avg_confidence = db.session.query(db.func.avg(Detection.confidence)).scalar() or 0
        
        # Trajectoires actives
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
    """Nettoyer les données anciennes (plus de 24h)"""
    try:
        cutoff_date = datetime.now(timezone.utc) - timedelta(hours=24)
        
        # Supprimer les détections anciennes
        deleted_detections = Detection.query.filter(Detection.timestamp < cutoff_date).delete()
        
        # Marquer les trajectoires inactives
        inactive_trajectories = Trajectory.query.filter(Trajectory.last_seen < cutoff_date).update({'is_active': False})
        
        db.session.commit()
        
        return jsonify({
            'message': 'Cleanup completed',
            'deletedDetections': deleted_detections,
            'inactiveTrajectories': inactive_trajectories
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@app.route('/api/export', methods=['POST'])
def export_data():
    """Exporter toutes les données"""
    try:
        data = request.json
        export_date = datetime.now(timezone.utc)
        
        # Récupérer toutes les données
        detections = Detection.query.all()
        trajectories = Trajectory.query.all()
        
        export_data = {
            'exportDate': export_date.isoformat(),
            'detectionHistory': [detection.to_dict() for detection in detections],
            'trajectoryHistory': {},
            'currentDetections': data.get('currentDetections', []),
            'filters': data.get('filters', {})
        }
        
        # Ajouter les trajectoires avec leurs points
        for trajectory in trajectories:
            points = TrajectoryPoint.query.filter_by(trajectory_id=trajectory.id).all()
            export_data['trajectoryHistory'][trajectory.object_id] = {
                'id': trajectory.object_id,
                'label': trajectory.label,
                'startTime': trajectory.start_time.isoformat(),
                'lastSeen': trajectory.last_seen.isoformat(),
                'points': [point.to_dict() for point in points]
            }
        
        # Sauvegarder dans un fichier
        filename = f"export_{export_date.strftime('%Y%m%d_%H%M%S')}.json"
        filepath = os.path.join('exports', filename)
        
        # Créer le dossier exports s'il n'existe pas
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
    """Vérification de l'état du serveur"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'database': 'connected',
        'yolo_available': YOLO_AVAILABLE
    })

# Routes YOLO et vidéo
@app.route('/api/yolo/model', methods=['GET'])
def get_model_info():
    """Obtenir les informations sur le modèle YOLO"""
    if not YOLO_AVAILABLE:
        return jsonify({'error': 'YOLO non disponible'}), 400
    
    return jsonify(detector.get_model_info())

@app.route('/api/yolo/model', methods=['POST'])
def load_model():
    """Charger un nouveau modèle YOLO"""
    if not YOLO_AVAILABLE:
        return jsonify({'error': 'YOLO non disponible'}), 400
    
    try:
        data = request.json
        model_path = data.get('model_path', 'models/best.onnx')
        confidence = data.get('confidence', 0.5)
        
        detector.model_path = model_path
        detector.confidence_threshold = confidence
        detector.load_model()
        
        return jsonify({
            'message': 'Modèle chargé avec succès',
            'model_path': model_path,
            'confidence': confidence
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/yolo/videos', methods=['GET'])
def get_available_videos():
    """Obtenir la liste des vidéos disponibles"""
    if not YOLO_AVAILABLE:
        return jsonify({'error': 'YOLO non disponible'}), 400
    
    videos = detector.get_available_videos()
    return jsonify({
        'videos': videos,
        'count': len(videos)
    })

@app.route('/api/yolo/process', methods=['POST'])
def process_video():
    """Traiter une vidéo avec YOLO"""
    if not YOLO_AVAILABLE:
        return jsonify({'error': 'YOLO non disponible'}), 400
    
    try:
        data = request.json
        video_path = data.get('video_path')
        save_results = data.get('save_results', True)
        
        if not video_path:
            return jsonify({'error': 'Chemin de vidéo requis'}), 400
        
        # Traiter la vidéo dans un thread séparé
        import threading
        thread = threading.Thread(
            target=detector.process_video,
            args=(video_path, save_results)
        )
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'message': 'Traitement de vidéo démarré',
            'video_path': video_path,
            'save_results': save_results
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/yolo/stream/start', methods=['POST'])
def start_streaming():
    """Démarrer le streaming d'une vidéo"""
    if not YOLO_AVAILABLE:
        return jsonify({'error': 'YOLO non disponible'}), 400
    
    try:
        data = request.json
        video_path = data.get('video_path')
        
        if not video_path:
            return jsonify({'error': 'Chemin de vidéo requis'}), 400
        
        thread = detector.start_streaming(video_path)
        
        return jsonify({
            'message': 'Streaming démarré',
            'video_path': video_path,
            'is_running': detector.is_running
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/yolo/stream/stop', methods=['POST'])
def stop_streaming():
    """Arrêter le streaming"""
    if not YOLO_AVAILABLE:
        return jsonify({'error': 'YOLO non disponible'}), 400
    
    try:
        detector.stop_streaming()
        return jsonify({
            'message': 'Streaming arrêté',
            'is_running': detector.is_running
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/yolo/stream/status', methods=['GET'])
def get_streaming_status():
    """Obtenir le statut du streaming"""
    if not YOLO_AVAILABLE:
        return jsonify({'error': 'YOLO non disponible'}), 400
    
    return jsonify({
        'is_running': detector.is_running,
        'current_video': detector.current_video
    })

@app.route('/api/yolo/upload-video', methods=['POST'])
def upload_video():
    """Uploader une vidéo"""
    if not YOLO_AVAILABLE:
        return jsonify({'error': 'YOLO non disponible'}), 400
    
    try:
        if 'video' not in request.files:
            return jsonify({'error': 'Aucun fichier vidéo fourni'}), 400
        
        file = request.files['video']
        if file.filename == '':
            return jsonify({'error': 'Aucun fichier sélectionné'}), 400
        
        # Vérifier l'extension
        allowed_extensions = {'mp4', 'avi', 'mov', 'mkv'}
        if not file.filename.lower().endswith(tuple(allowed_extensions)):
            return jsonify({'error': 'Format de fichier non supporté'}), 400
        
        # Sauvegarder le fichier
        filename = file.filename
        filepath = os.path.join('videos', filename)
        file.save(filepath)
        
        return jsonify({
            'message': 'Vidéo uploadée avec succès',
            'filename': filename,
            'filepath': filepath
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/yolo/upload-model', methods=['POST'])
def upload_model():
    """Uploader un modèle YOLO"""
    if not YOLO_AVAILABLE:
        return jsonify({'error': 'YOLO non disponible'}), 400
    
    try:
        if 'model' not in request.files:
            return jsonify({'error': 'Aucun fichier modèle fourni'}), 400
        
        file = request.files['model']
        if file.filename == '':
            return jsonify({'error': 'Aucun fichier sélectionné'}), 400
        
        # Vérifier l'extension
        if not file.filename.lower().endswith('.pt'):
            return jsonify({'error': 'Format de fichier non supporté (.pt requis)'}), 400
        
        # Sauvegarder le fichier
        filename = file.filename
        filepath = os.path.join('models', filename)
        file.save(filepath)
        
        return jsonify({
            'message': 'Modèle uploadé avec succès',
            'filename': filename,
            'filepath': filepath
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400

# Route pour servir les vidéos statiques
@app.route('/videos/<path:filename>')
def serve_video(filename):
    return send_from_directory('videos', filename)

@app.route('/video_feed')
def video_feed():
    video_path = request.args.get('video_path')
    if not video_path:
        return "No video_path provided", 400
    return Response(
        detector.generate_stream_frames(video_path),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )

# Créer les tables au démarrage
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
    Retourne des données de performance simulées ou calculées.
    À adapter selon vos métriques réelles si besoin.
    """
    # Exemple : calculer le FPS moyen sur la dernière minute
    now = datetime.now(timezone.utc)
    one_minute_ago = now - timedelta(minutes=1)
    recent_detections = Detection.query.filter(Detection.timestamp >= one_minute_ago).count()
    fps = recent_detections / 60 if recent_detections else 30  # fallback à 30 si aucune détection

    # Inference time simulé (à remplacer par une vraie métrique si dispo)
    inference_time = 33

    # Nombre d'objets détectés actuellement (dans la dernière seconde)
    one_second_ago = now - timedelta(seconds=1)
    object_count = Detection.query.filter(Detection.timestamp >= one_second_ago).count()

    return jsonify({
        "fps": fps,
        "inferenceTime": inference_time,
        "objectCount": object_count
    })

@app.route('/api/detections/current', methods=['GET'])
def get_current_detections():
    """
    Retourne les détections les plus récentes pour chaque objet (par object_id).
    """
    # Pour chaque object_id, on prend la détection la plus récente
    subquery = (
        db.session.query(
            Detection.object_id,
            db.func.max(Detection.timestamp).label('max_timestamp')
        )
        .group_by(Detection.object_id)
        .subquery()
    )

    detections = (
        db.session.query(Detection)
        .join(subquery, (Detection.object_id == subquery.c.object_id) & (Detection.timestamp == subquery.c.max_timestamp))
        .all()
    )

    # Adapter le format du timestamp pour le frontend (en ms depuis epoch)
    def detection_to_dict_with_epoch(d):
        dct = d.to_dict()
        try:
            dt = d.timestamp
            if isinstance(dt, str):
                dt = datetime.fromisoformat(dt)
            dct['timestamp'] = int(dt.timestamp() * 1000)
        except Exception:
            dct['timestamp'] = 0
        return dct

    return jsonify([detection_to_dict_with_epoch(d) for d in detections])

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)