from flask import Blueprint, request, jsonify, Response, current_app
import numpy as np
import cv2
import os
from PIL import Image
import io
from ..extensions import db

yolo_bp = Blueprint('yolo', __name__)

@yolo_bp.route('/api/yolo/stream/start', methods=['POST'])
def start_streaming():
    
    detector = current_app.detector
    yolo_available = current_app.yolo_available
    #metrics = current_app.metrics

    if not yolo_available:
        return jsonify({'error': 'YOLO not available'}), 503
    
    try:
        data = request.json
        stream_source = data.get('network_url')
        if not stream_source:
            return jsonify({'error': 'Source (network_url) is required'}), 400   
        

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

        # if 'fps_gauge' in metrics:
        #     metrics['fps_gauge'].set(0)
        # if 'inference_gauge' in metrics:
        #     metrics['inference_gauge'].set(0)

        return jsonify({
            'message': 'Streaming started',
            'stream_source': stream_source,
            'is_running': detector.is_running
        })
    except Exception as e:
        current_app.logger.error(f"Error in start_streaming: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@yolo_bp.route('/api/yolo/stream/stop', methods=['POST'])
def stop_streaming():
    if not current_app.yolo_available:
        return jsonify({'error': 'YOLO not available'}), 400
    
    try:
        current_app.detector.stop_streaming()
        return jsonify({
            'message': 'Streaming stopped',
            'is_running': current_app.detector.is_running
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@yolo_bp.route('/api/yolo/stream/status', methods=['GET'])
def get_streaming_status():
    yolo_available = current_app.yolo_available
    if not yolo_available:
        return jsonify({'is_running': False, 'current_video': None})
    return jsonify({'is_running': current_app.detector.is_running, 'current_video': current_app.detector.current_video})

@yolo_bp.route('/video_feed')
def video_feed():
    detector = current_app.detector
    yolo_available = current_app.yolo_available
    if not yolo_available or not detector.is_running:
        img = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.putText(img, 'Stream Offline', (200, 240), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        _, jpeg = cv2.imencode('.jpg', img)
        return Response(jpeg.tobytes(), mimetype='image/jpeg')

    return Response(detector.generate_stream_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@yolo_bp.route('/api/yolo/model', methods=['GET']) 
def get_model_info():
    detector = current_app.detector
    yolo_available = current_app.yolo_available
    """Get YOLO model information."""
    if not yolo_available:
        return jsonify({'error': 'YOLO not available'}), 400
    
    return jsonify(detector.get_model_info())

@yolo_bp.route('/api/yolo/model', methods=['POST'])
def load_model():
    """Load a new YOLO model."""
    detector = current_app.detector
    yolo_available = current_app.yolo_available
    if not yolo_available:
        return jsonify({'error': 'YOLO not available'}), 400
    
    try:
        data = request.json
        model_path = data.get('model_path', 'models/best2.onnx')
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
    
@yolo_bp.route('/api/yolo/upload-model', methods=['POST'])
def upload_model():
    """Upload a YOLO model."""
    yolo_available = current_app.yolo_available
    if not yolo_available:
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
    
@yolo_bp.route('/api/yolo/process', methods=['POST'])
def process_video():
    """Process a video with YOLO."""
    detector = current_app.detector
    yolo_available = current_app.yolo_available
    if not yolo_available:
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
    
@yolo_bp.route('/api/yolo/detect_frame', methods=['POST'])
def detect_frame():
    """Process a single frame for detection."""
    yolo_available = current_app.yolo_available
    detector = current_app.detector
    if not yolo_available:
        current_app.logger.warning("Appel à 'detect_frame' alors que YOLO n'est pas disponible.")
        return jsonify({'error': 'YOLO detector is not available'}),

    if 'frame' not in request.files:
        current_app.logger.error("Requête invalide à 'detect_frame' : 'frame' manquant.")
        return jsonify({'error': 'No frame provided in the request'}), 400

    try:
        frame_file = request.files['frame']
        
        # Read the image file
        image_bytes = frame_file.read()
        image = Image.open(io.BytesIO(image_bytes))
        
        # Convert to numpy array (OpenCV format)
        frame_np = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        
        # Process the frame using the detector
        detections = detector.process_frame(frame_np)

        return jsonify({'detections': detections})

    except Exception as e:
        current_app.logger.error(f"Erreur lors du traitement d'une trame dans 'detect_frame'", exc_info=True)
        
        # Renvoyer une réponse d'erreur générique et sûre au client
        return jsonify({'error': 'Une erreur interne est survenue lors du traitement de l´image.'}), 500
    
