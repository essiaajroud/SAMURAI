from flask import Blueprint, jsonify, current_app
from werkzeug.exceptions import RequestTimeout
import time
import logging

stream_bp = Blueprint('stream', __name__)
logger = logging.getLogger(__name__)

@stream_bp.route('/api/yolo/stream/status', methods=['GET'])
def get_stream_status():
    return jsonify({
        'active': current_app.stream_monitor.is_stream_active,
        'last_heartbeat': current_app.stream_monitor.last_heartbeat.isoformat() if current_app.stream_monitor.last_heartbeat else None
    })

@stream_bp.route('/api/yolo/stream/heartbeat', methods=['POST'])
def update_stream_heartbeat():
    try:
        current_app.stream_monitor.update_heartbeat()
        return jsonify({'status': 'success'})
    except RequestTimeout:
        current_app.stream_monitor.handle_disconnect()
        return jsonify({'status': 'timeout'}), 408
    except Exception as e:
        logger.error(f"Error updating stream heartbeat: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500
