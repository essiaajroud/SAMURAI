from flask import Blueprint, jsonify, request, current_app
from ..extensions import db, METRICS
from ..models import Detection, Trajectory, TrajectoryPoint
from ..utils.geo_helpers import load_osm_zones, point_in_military_zone
from ..utils.statistics import calculate_detection_stats, calculate_tracking_stats
from datetime import datetime, timezone, timedelta
import psutil
import os
import json
import numpy as np


system_bp = Blueprint('system', __name__)

@system_bp.route('/api/health', methods=['GET'])
def health_check():
    yolo_available = current_app.yolo_available
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'database': 'connected',
        'yolo_available': yolo_available
    })

@system_bp.route('/api/system-metrics', methods=['GET'])
def get_system_metrics():
    try:
        battery = None
        try:
            battery = psutil.sensors_battery()
        except Exception as e:
            current_app.logger.warning(f"Could not read battery sensor: {e}")
        ram = psutil.virtual_memory()
        cpu = psutil.cpu_percent(interval=0.1)
        disk = psutil.disk_usage('/')
        net = psutil.net_io_counters()
        METRICS['system_cpu_percent'].set(cpu)
        METRICS['system_ram_percent'].set(ram.percent)
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
        current_app.logger.error(f"Error in get_system_metrics: {e}")

        return jsonify({"error": str(e)}), 500

@system_bp.route('/api/logs', methods=['GET'])
def get_logs():
    try:
        log_file = 'server.log' # Assurez-vous que ce chemin est correct
        if not os.path.exists(log_file):
            return jsonify({'logs': ['Log file not found.']})
        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()[-100:]
        return jsonify({'logs': lines})
    except Exception as e:
        current_app.logger.error(f"Error reading log file: {e}")
        return jsonify({'error': str(e)}), 500

@system_bp.route('/api/rover-location', methods=['GET'])
def get_rover_location():
    camera_location_manager = current_app.camera_location_manager
    if camera_location_manager and camera_location_manager.current_position:
        pos = camera_location_manager.current_position
        return jsonify({'latitude': pos.latitude, 'longitude': pos.longitude})
    return jsonify({'latitude': 34.0, 'longitude': 9.0})

@system_bp.route('/api/alerts', methods=['GET'])
def get_alerts():
    try:
        # 1. Récupérer les composants nécessaires depuis l'application Flask
        camera_location_manager = current_app.camera_location_manager
        zone_polygons = current_app.zone_polygons

        # 2. Vérifier si la position du rover est disponible
        if not (camera_location_manager and camera_location_manager.current_position and camera_location_manager.is_real_position):
            return jsonify({'alerts': [], 'message': 'Real-time rover GPS position not yet available.'})

        rover_pos = camera_location_manager.current_position
        
        # 3. Charger les zones militaires autour de la position actuelle du rover
        # La fonction modifie le dictionnaire 'zone_polygons' en place
        load_osm_zones(zone_polygons, rover_pos.latitude, rover_pos.longitude)

        # 4. Récupérer les détections récentes qui ont des coordonnées GPS
        time_limit = datetime.now(timezone.utc) - timedelta(minutes=2)
        recent_detections_with_gps = Detection.query.filter(
            Detection.timestamp >= time_limit,
            Detection.latitude.isnot(None),
            Detection.longitude.isnot(None)
        ).all()

        alerts = []
        for d in recent_detections_with_gps:
            # 5. Définir les conditions de menace (ici, une arme)
            is_weapon = 'weapon' in d.label.lower()
            
            if is_weapon:
                # 6. Vérifier si l'arme se trouve dans une zone militaire connue
                in_military_zone = point_in_military_zone(zone_polygons, d.latitude, d.longitude)
                
                if not in_military_zone:
                    # Si ce n'est PAS dans une zone militaire, c'est une alerte de danger
                    alerts.append({
                        'type': 'danger',
                        'message': f"Weapon detected in NON-MILITARY area (ID {d.object_id})",
                        'lat': d.latitude, 
                        'lon': d.longitude, 
                        'color': 'red',
                        'timestamp': d.timestamp.isoformat()
                    })
                else:
                    # Si c'est DANS une zone militaire, c'est une information sécurisée
                     alerts.append({
                        'type': 'secure',
                        'message': f"Weapon detected within a military zone (ID {d.object_id})",
                        'lat': d.latitude, 
                        'lon': d.longitude, 
                        'color': 'green',
                        'timestamp': d.timestamp.isoformat()
                    })

        return jsonify({'alerts': alerts})

    except Exception as e:
        # Logger l'erreur complète pour le débogage
        current_app.logger.error(f"❌ Error in /api/alerts: {e}", exc_info=True)
        # Renvoyer une réponse d'erreur générique au client
        return jsonify({'error': 'An internal server error occurred while generating alerts.'}), 500
    
@system_bp.route('/api/statistics/summary', methods=['GET'])
def get_statistics_summary():
    """
    Retourne un résumé statistique complet pour une période donnée.
    Exemple: /api/statistics/summary?hours=24
    """
    try:
        hours = int(request.args.get('hours', 24))
        time_limit = datetime.now(timezone.utc) - timedelta(hours=hours)

        # Récupérer les données pertinentes
        detections_in_period = Detection.query.filter(Detection.timestamp >= time_limit).all()
        trajectories_in_period = Trajectory.query.filter(Trajectory.start_time >= time_limit).all()

        # Calculer les statistiques en utilisant nos fonctions utilitaires
        detection_stats = calculate_detection_stats(detections_in_period)
        tracking_stats = calculate_tracking_stats(trajectories_in_period)

        # Agréger les résultats
        summary = {
            'time_window_hours': hours,
            'query_timestamp': datetime.now(timezone.utc).isoformat(),
            'detections': detection_stats,
            'tracking': tracking_stats
        }
        
        return jsonify(summary)

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
@system_bp.route('/api/performance', methods=['GET']) 
def get_performance():
    """
    Returns real-time performance data from the YOLO detector.
    """
    yolo_available = current_app.yolo_available
    detector = current_app.detector
    metrics = current_app.metrics
    if not yolo_available:
        return jsonify({
            "fps": 0,
            "inferenceTime": 0,
            "objectCount": 0
        })

    # Get metrics from the detector
    perf_metrics = detector.get_performance_metrics() if detector else {}

    print(f"DEBUG - Sending performance metrics: {perf_metrics}")

    METRICS['fps_gauge'].set(perf_metrics.get("fps", 0))
    METRICS['inference_gauge'].set(perf_metrics.get("inferenceTime", 0))
    METRICS['yolo_gpu_usage_percent'].set(perf_metrics.get("gpuUsage", 0))

    # Get object count from the database (last 2 seconds for a more "current" feel)
    now = datetime.now(timezone.utc)
    two_seconds_ago = now - timedelta(seconds=2)
    object_count = db.session.query(Detection.object_id).filter(Detection.timestamp >= two_seconds_ago).distinct().count()

    try:
        with current_app.app_context():
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

@system_bp.route('/api/statistics/realtime', methods=['GET'])
def get_realtime_statistics():
    """
    Returns real-time statistics for the dashboard.
    Dynamic with real-time calculations.
    """
    yolo_available = current_app.yolo_available
    detector = current_app.detector
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
                'system_status': 'running' if yolo_available and detector.is_running else 'stopped'
            }
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 400
     
@system_bp.route('/api/statistics', methods=['GET'])
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
    
@system_bp.route('/api/update_rover_location', methods=['POST'])
def update_rover_location():
    """
    Endpoint pour que le téléphone/rover mette à jour sa position GPS.
    """
    camera_location_manager = current_app.camera_location_manager
    try:
        data = request.get_json() 
        if not data or 'latitude' not in data or 'longitude' not in data:
            return jsonify({'error': "Invalid or missing JSON payload."}), 400
        
        lat = float(data['latitude'])
        lon = float(data['longitude'])
        camera_location_manager.update_position(lat=lat, lon=lon)
        
        current_app.logger.info(f"🛰️ Rover position updated via API: ({lat}, {lon})")
        return jsonify({'message': 'Location updated successfully.'}), 200
        
    except (json.JSONDecodeError, ValueError, TypeError):
        return jsonify({'error': 'Invalid data format. Ensure latitude and longitude are numbers.'}), 400
    except Exception as e:
        current_app.logger.error(f"Error updating rover location: {e}")
        return jsonify({'error': 'An internal error occurred.'}), 500
     
@system_bp.route('/api/cleanup', methods=['POST']) 
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
    
@system_bp.route('/api/cleanup/auto', methods=['POST']) 
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
    
@system_bp.route('/api/export', methods=['POST']) 
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
    
@system_bp.route('/api/export/daily', methods=['POST'])
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
        current_app.logger.error(f"Error during daily export: {e}")
        return jsonify({'error': str(e)}), 500