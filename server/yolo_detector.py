import cv2
import torch
from ultralytics import YOLO
import os
import time
from datetime import datetime
import threading
import queue
import numpy as np
import sys
import importlib.util
from bytetrack_tracker import ByteTracker
from gpu_config import gpu_config

# Importer la configuration des logs depuis app.py
try:
    # Vérifier si app est déjà importé
    if 'app' in sys.modules:
        from app import ENABLE_LOGS
    else:
        # Charger dynamiquement la variable ENABLE_LOGS depuis app.py
        spec = importlib.util.spec_from_file_location("app", "app.py")
        app_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(app_module)
        ENABLE_LOGS = getattr(app_module, "ENABLE_LOGS", False)
except ImportError:
    # Si l'import échoue, désactiver les logs par défaut
    ENABLE_LOGS = False

# yolo_detector.py - YOLO object detection logic for the server
# Handles model loading, video processing, streaming, and detection callbacks

class YOLODetector:
    def __init__(self, model_path="models/best.onnx", confidence_threshold=0.5):
        # Configure device based on GPU config
        self.device = gpu_config.get_device()
        if ENABLE_LOGS:
            print(f"🔧 Initializing YOLO detector on {self.device}")
            if gpu_config.gpu_available:
                print(f"GPU: {gpu_config.gpu_name}")
        
        # --- Tracking metrics state ---
        self._tracking_total_matches = 0
        self._tracking_misses = 0
        self._tracking_false_positives = 0
        self._tracking_id_switches = 0
        self._tracking_total_distance = 0.0
        self._tracking_total_detections = 0
        self._tracking_total_gt = 0
        self._tracking_last_ids = {}
        """
        Initialize the YOLO detector.
        Args:
            model_path (str): Path to YOLO model (.pt or .onnx)
            confidence_threshold (float): Confidence threshold for detections
        """
        self.model_path = model_path
        self.confidence_threshold = confidence_threshold
        self.model = None
        self.is_running = False
        self.current_video = None
        self.detection_callback = None
        self.frame_queue = queue.Queue(maxsize=10) # For streaming frames to the web
        
        # Performance metrics
        self.inference_time_ms = 0
        self.fps = 0
        self._frame_times = []
        self.objects_by_class = {}
        

        # --- ByteTrack tracker instance ---
        self.tracker = ByteTracker(track_thresh=0.5, track_buffer=30, match_thresh=0.8)

        # Initialize with GPU settings
        if torch.cuda.is_available():
            torch.backends.cudnn.benchmark = True
            if hasattr(cv2, 'cuda') and hasattr(cv2.cuda, 'setCudaDevice'):
                cv2.cuda.setCudaDevice(0)
        
        self.load_model()

    def load_model(self):
        """Load the YOLO model (ONNX or PyTorch)."""
        if not os.path.exists(self.model_path):
            if ENABLE_LOGS:
                print(f"❌ Model not found: {self.model_path}")
            self.model = None
            return
        try:
            self.model = YOLO(self.model_path, task="detect")
            # Don't call .to(device) for ONNX models
            if not self.model_path.endswith('.onnx') and torch.cuda.is_available():
                self.model.to(self.device)
            if ENABLE_LOGS:
                print(f"✅ Model loaded: {self.model_path}")
        except Exception as e:
            if ENABLE_LOGS:
                print(f"❌ Error loading model: {e}")
            self.model = None

    def set_detection_callback(self, callback):
        """Set the callback function for detections."""
        self.detection_callback = callback

    def _execute_detection(self, frame):
        """
        Executes YOLO detection on a single frame and returns drawn frame and detections.
        Ajoute le calcul de la distance réelle caméra-objet.
        """
        if self.model is None:
            return frame, []

        try:
            # For ONNX models, use predict() method with explicit device
            if self.model_path.endswith('.onnx'):
                results = self.model.predict(
                    source=frame,
                    conf=self.confidence_threshold,
                    device=0 if gpu_config.gpu_available else 'cpu',
                    verbose=False
                )
            else:
                # For PyTorch models, use direct inference
                if gpu_config.gpu_available:
                    frame_tensor = torch.from_numpy(frame).to(self.device)
                    results = self.model(frame_tensor, conf=self.confidence_threshold, verbose=False)
                else:
                    results = self.model(frame, conf=self.confidence_threshold, verbose=False)

            # Timing code
            start_time = time.time()
            if gpu_config.gpu_available:
                torch.cuda.synchronize()
            end_time = time.time()
            self.inference_time_ms = (end_time - start_time) * 1000

            # Move frame to GPU if available
            if torch.cuda.is_available():
                if isinstance(frame, np.ndarray):
                    frame_tensor = torch.from_numpy(frame).to(self.device)
                else:
                    frame_tensor = frame.to(self.device)
            
            # Paramètres caméra (à ajuster selon ton setup)
            FOCAL_LENGTH_PX = 800  # focale en pixels (exemple)
            # Tailles réelles moyennes (en mètres) pour chaque classe
            REAL_SIZES = {
                'person': 1.7,
                'soldier': 1.7,
                'weapon': 1.0,
                'military_vehicles': 3.0,
                'civilian_vehicles': 4.5,
                'military_aircraft': 15.0,
                'civilian_aircraft': 20.0
            }

            detections = []
            dets_for_tracking = []
            for result in results:
                boxes = result.boxes
                if boxes is not None:
                    for box in boxes:
                        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                        cls = int(box.cls[0].cpu().numpy())
                        conf = float(box.conf[0].cpu().numpy())
                        class_name = result.names[cls]

                        # Calcul de la distance réelle (si taille connue)
                        pixel_height = y2 - y1
                        real_height = REAL_SIZES.get(class_name, 1.7)  # défaut: 1.7m
                        distance = (real_height * FOCAL_LENGTH_PX) / (pixel_height + 1e-6)

                        detection_data = {
                            'label': class_name,
                            'confidence': conf,
                            'x': (x1 + x2) / 2,
                            'y': (y1 + y2) / 2,
                            'width': x2 - x1,
                            'height': pixel_height,
                            'distance': float(distance),
                            'timestamp': datetime.now().isoformat(),
                            'bbox': [x1, y1, x2, y2],
                            'class_id': cls
                        }
                        detections.append(detection_data)
                        dets_for_tracking.append([x1, y1, x2, y2, conf, cls])

                        # Update objects by class count
                        self.objects_by_class[class_name] = self.objects_by_class.get(class_name, 0) + 1

            # --- Tracking: assign IDs using ByteTracker ---
            tracks = self.tracker.update(dets_for_tracking, frame)
            # Map track_id to detection by IoU (simple association)
            for det in detections:
                det_bbox = det['bbox']
                best_iou = 0
                best_track_id = None
                for track in tracks:
                    iou = self.tracker._calculate_iou(det_bbox, track['bbox'])
                    if iou > best_iou and iou > self.tracker.match_thresh:
                        best_iou = iou
                        best_track_id = track['track_id']
                det['id'] = best_track_id if best_track_id is not None else -1

            # Draw on the frame
            for det in detections:
                x1, y1, x2, y2 = det['bbox']
                class_name = det['label']
                conf = det['confidence']
                track_id = det['id']
                cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
                cv2.putText(frame, f'{class_name} {conf:.2f} ID:{track_id}',
                            (int(x1), int(y1) - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

            # Trigger callback for database saving etc.
            if self.detection_callback and detections:
                for det in detections:
                    self.detection_callback(det)

            # Remove bbox/class_id from output for compatibility
            for det in detections:
                det.pop('bbox', None)
                det.pop('class_id', None)

            return frame, detections
        except Exception as e:
            if ENABLE_LOGS:
                print(f"❌ Error during detection: {e}")
            return frame, []

    def process_frame(self, frame_np):
        """
        Process a single frame received from an external source (e.g., frontend).
        Args:
            frame_np (np.array): The image as a numpy array.
        Returns:
            list: A list of detection dictionaries.
        """
        if self.model is None:
            if ENABLE_LOGS:
                print("❌ Model not loaded")
            return []
        
        # We don't need the drawn frame here, just the detections.
        _, detections = self._execute_detection(frame_np)

        return detections

    def _process_stream(self, stream_source, started_event):
        """Private method to process a video stream from a file or network URL."""
        if ENABLE_LOGS:
            print(f"[YOLO] Attempting to open stream: {stream_source}")
        
        max_retries = 3
        retry_delay = 2
        cap = None
        
        try:
            for attempt in range(max_retries):
                try:
                    # For network streams, validate connection first
                    if '://' in stream_source:
                        import socket
                        from urllib.parse import urlparse
                        parsed = urlparse(stream_source)
                        host = parsed.hostname
                        port = parsed.port or 8080
                        
                        # Test TCP connection
                        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        sock.settimeout(5)
                        result = sock.connect_ex((host, port))
                        sock.close()
                        
                        if result != 0:
                            raise ConnectionError(f"Cannot connect to {host}:{port}")

                    cap = cv2.VideoCapture(stream_source)
                    if not cap.isOpened():
                        raise ConnectionError("Failed to open video stream")

                    # Stream opened successfully
                    self.is_running = True
                    self.current_video = stream_source
                    started_event.set()
                    
                    if ENABLE_LOGS:
                        print(f"✅ Stream connected: {stream_source}")
                    break  # Success - exit retry loop
                    
                except Exception as e:
                    if attempt < max_retries - 1:
                        if ENABLE_LOGS:
                            print(f"⚠️ Attempt {attempt + 1}/{max_retries} failed: {str(e)}")
                            print(f"   Retrying in {retry_delay} seconds...")
                        time.sleep(retry_delay)
                    else:
                        raise  # Re-raise the last exception

            # Stream processing loop
            while self.is_running:
                ret, frame = cap.read()
                if not ret:
                    if '://' in stream_source:
                        if ENABLE_LOGS:
                            print("⚠️ Network stream interrupted - attempting reconnect")
                        cap.release()
                        cap = cv2.VideoCapture(stream_source)
                        continue
                    else:
                        if ENABLE_LOGS:
                            print("Looping video file...")
                        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        continue

                # Execute detection and process frame
                drawn_frame, detections = self._execute_detection(frame)
                
                # Debug log pour les détections
                if ENABLE_LOGS:
                    if detections:
                        print(f"✅ Détections trouvées: {len(detections)} objets")
                    else:
                        print("⚠️ Aucune détection trouvée dans cette frame")

                # Put the processed frame into the queue for the web feed
                if not self.frame_queue.full():
                    self.frame_queue.put(drawn_frame)
                
                # Update FPS calculation
                now = time.time()
                self._frame_times.append(now)
                # Keep the last 20 frame times
                self._frame_times = self._frame_times[-20:]
                if len(self._frame_times) > 1:
                    time_diff = self._frame_times[-1] - self._frame_times[0]
                    self.fps = (len(self._frame_times) - 1) / time_diff if time_diff > 0 else 0
            
        except Exception as e:
            if ENABLE_LOGS:
                print(f"❌ Stream error: {str(e)}")
            started_event.set()  # Signal failure
            
        finally:
            if cap is not None and cap.isOpened():
                cap.release()
            self.is_running = False
            self.current_video = None
            while not self.frame_queue.empty():
                self.frame_queue.get()
            if ENABLE_LOGS:
                print("🛑 Streaming finished")
    
    def start_streaming(self, stream_source):
        """Starts streaming in a separate thread and waits for initialization."""
        if self.is_running:
            if ENABLE_LOGS:
                print("🔄 Stopping previous stream...")
            self.stop_streaming()
            time.sleep(1)  # Give it a moment to fully stop
        
        # Reset metrics for new stream
        self.objects_by_class.clear()
        self._frame_times = []
        self.fps = 0
        # --- Tracking metrics update (simple, per frame) ---
        # This is a placeholder. In a real tracker, you would compare predicted IDs to ground truth.
        # Here, we simulate tracking metrics for demonstration.
        # You should replace this with your actual tracking logic.
        # For now, we count detections as matches, and simulate some misses and id switches.
        num_dets = 0
        self.inference_time_ms = 0

        if ENABLE_LOGS:
            print(f"▶️ Starting YOLO stream with source: {stream_source}")
        started_event = threading.Event()
        thread = threading.Thread(target=self._process_stream, args=(stream_source, started_event))
        thread.daemon = True
        thread.start()

        # Wait for the stream to be confirmed as running or failed
        event_set = started_event.wait(timeout=10)  # 10-second timeout

        if not event_set:
            if ENABLE_LOGS:
                print("❌ Timed out waiting for stream to initialize.")
            self.is_running = False # Ensure state is correct
            return None

        if not self.is_running:
            if ENABLE_LOGS:
                print("❌ Stream failed to start. Check video path and format.")
            return None

        if ENABLE_LOGS:
            print("✅ Stream successfully initialized.")
        return thread
    
    def stop_streaming(self):
        """Stops the stream."""
        self.is_running = False
        
    def generate_stream_frames(self):
        """Yields frames from the queue for the web feed."""
        while self.is_running:
            try:
                frame = self.frame_queue.get(timeout=1)
                
                # Réduire la taille de l'image pour améliorer les performances
                scale_percent = 70  # pourcentage de la taille originale
                width = int(frame.shape[1] * scale_percent / 100)
                height = int(frame.shape[0] * scale_percent / 100)
                dim = (width, height)
                resized_frame = cv2.resize(frame, dim, interpolation=cv2.INTER_AREA)
                
                # Réduire la qualité de l'image pour améliorer les performances
                encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 80]
                ret, jpeg = cv2.imencode('.jpg', resized_frame, encode_param)
                
                if not ret:
                    continue
                
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n')

            except queue.Empty:
                # If the queue is empty, it might mean processing has stopped
                # or is just slow. We check `is_running` to decide whether to continue.
                if not self.is_running:
                    if ENABLE_LOGS:
                        print("Stream generation stopped as processing is no longer running.")
                    break
    
    def get_available_videos(self):
        """Returns the list of available videos."""
        videos_dir = "videos"
        if not os.path.exists(videos_dir):
            return []
        
        video_extensions = ['.mp4', '.avi', '.mov', '.mkv']
        videos = []
        
        for file in os.listdir(videos_dir):
            if any(file.lower().endswith(ext) for ext in video_extensions):
                videos.append(os.path.join(videos_dir, file))
        
        return videos
    
    def get_model_info(self):
        """Returns model information."""
        if self.model is None:
            return {"status": "not_loaded", "message": "Model not loaded"}
        
        return {
            "status": "loaded",
            "model_path": self.model_path,
            "confidence_threshold": self.confidence_threshold,
            "is_running": self.is_running,
            "current_video": self.current_video
        }

    def get_performance_metrics(self):
        """Returns a dictionary with current performance metrics."""
        # Compute MOTA, MOTP, ID Switches from tracking state
        mota = 1.0
        motp = 0.0
        if self._tracking_total_gt > 0:
            mota = 1.0 - (self._tracking_misses + self._tracking_false_positives + self._tracking_id_switches) / self._tracking_total_gt
            mota = max(0.0, mota)
        if self._tracking_total_matches > 0:
            motp = self._tracking_total_distance / self._tracking_total_matches
        return {
            "fps": self.fps,
            "inferenceTime": self.inference_time_ms,
            "mota": mota,
            "motp": motp,
            "idSwitchCount": self._tracking_id_switches
        }

    def get_objects_by_class(self):
        """Returns a dictionary with the count of detected objects per class."""
        return self.objects_by_class

# Global detector instance
detector = YOLODetector()