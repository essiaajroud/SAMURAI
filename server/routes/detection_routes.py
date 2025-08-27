# Fichier : server/routes/detection_routes.py

from flask import Blueprint, request, jsonify, current_app
from ..models import Detection, Trajectory, TrajectoryPoint # Notez le '..' pour remonter d'un dossier
from ..extensions import db
from datetime import datetime, timezone, timedelta

# 1. Créer le Blueprint
detection_bp = Blueprint('detection', __name__)

# 2. Remplacer @app.route par @detection_bp.route

@detection_bp.route('/api/detections', methods=['GET'])
def get_detections_history():
    try:
        
        time_range = request.args.get('timeRange', '24h')
        confidence_threshold = float(request.args.get('confidence', 0.0))
        selected_class = request.args.get('class', 'all')
        
        now = datetime.now(timezone.utc)
        time_map = {'1h': 1, '6h': 6, '24h': 24}
        time_limit = now - timedelta(hours=time_map.get(time_range, 24))

        query = db.session.query(Detection).filter(Detection.timestamp >= time_limit)
        if confidence_threshold > 0:
            query = query.filter(Detection.confidence >= confidence_threshold)
        if selected_class != 'all':
            query = query.filter(Detection.label == selected_class)

        detections = query.order_by(Detection.timestamp.desc()).all()
        return jsonify([d.to_dict() for d in detections])
    except Exception as e:
        
        current_app.logger.error(f"Error in /api/detections: {e}")
        return jsonify({'error': str(e)}), 500

@detection_bp.route('/api/detections/current', methods=['GET'])
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
        current_app.logger.error(f"Error in /api/detections/current: {e}")
        return jsonify({'error': str(e)}), 500

@detection_bp.route('/api/trajectories', methods=['GET'])
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
        current_app.logger.error(f"Error in /api/trajectories: {e}")
        return jsonify({'error': str(e)}), 500

