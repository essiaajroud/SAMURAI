import cv2
import torch
from ultralytics import YOLO
import os
import time
from datetime import datetime, timezone
import threading
import queue
import numpy as np
import sys
import importlib.util

# GPU Configuration
try:
    from gpu_config import gpu_config
    GPU_AVAILABLE = gpu_config.gpu_available
    if GPU_AVAILABLE:
        print(f"🚀 GPU acceleration enabled: {gpu_config.gpu_name}")
    else:
        print("⚠️ GPU acceleration not available, using CPU")
except ImportError:
    print("⚠️ GPU configuration not found, using CPU")
    GPU_AVAILABLE = False

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
        
        self.load_model()

    def load_model(self):
        """Load the YOLO model (ONNX or PyTorch) with GPU optimization."""
        if not os.path.exists(self.model_path):
            if ENABLE_LOGS:
                print(f"❌ Model not found: {self.model_path}")
            self.model = None
            return
        try:
            # Load model with GPU optimization
            if GPU_AVAILABLE:
                # Use GPU device for YOLO
                self.model = YOLO(self.model_path, task="detect")
                
                # Apply GPU optimizations
                if hasattr(self.model, 'model'):
                    self.model.model = gpu_config.optimize_model(self.model.model)
                
                # Set device for inference
                self.model.to(gpu_config.get_device())
                
                if ENABLE_LOGS:
                    print(f"✅ Model loaded with GPU acceleration: {self.model_path}")
                    print(f"   Device: {gpu_config.get_device()}")
                    print(f"   GPU Memory: {gpu_config.get_memory_info()['gpu_memory_used']:.2f} GB used")
            else:
                self.model = YOLO(self.model_path, task="detect")
                if ENABLE_LOGS:
                    print(f"✅ Model loaded (CPU): {self.model_path}")
                    
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
        Optimized for GPU acceleration with RTX 3060.
        """
        if self.model is None:
            return frame, []

        # GPU optimization for inference
        if GPU_AVAILABLE:
            # Convert frame to GPU tensor if needed
            if isinstance(frame, np.ndarray):
                frame_tensor = torch.from_numpy(frame).to(gpu_config.get_device())
                if gpu_config.get_optimization_settings()["precision"] == "fp16":
                    frame_tensor = frame_tensor.half()
            else:
                frame_tensor = frame

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

        start_time = time.time()
        results = self.model(frame, conf=self.confidence_threshold, verbose=False)
        end_time = time.time()
        self.inference_time_ms = (end_time - start_time) * 1000

        detections = []
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
                    distance = (real_height * FOCAL_LENGTH_PX) / (pixel_height + 1e-6)  # +1e-6 pour éviter div/0

                    detection_data = {
                        'label': class_name,
                        'confidence': conf,
                        'x': (x1 + x2) / 2,
                        'y': (y1 + y2) / 2,
                        'width': x2 - x1,
                        'height': pixel_height,
                        'distance': float(distance),
                        'timestamp': datetime.now().isoformat()
                    }
                    detections.append(detection_data)

                    # Update objects by class count
                    self.objects_by_class[class_name] = self.objects_by_class.get(class_name, 0) + 1

                    # Draw on the frame
                    cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
                    cv2.putText(frame, f'{class_name} {conf:.2f}',
                                (int(x1), int(y1) - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        # Trigger callback for database saving etc.
        if self.detection_callback and detections:
            # Assign a unique ID for each detection in the frame
            for i, det in enumerate(detections):
                det['id'] = int(time.time() * 1000) + i # pseudo-unique ID
                self.detection_callback(det)

        return frame, detections

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
        """
        Private method to process a video stream from a file or network URL.
        Args:
            stream_source (str): Path to the video or network URL.
            started_event (threading.Event): Event to signal when startup is complete.
        """
        if ENABLE_LOGS:
            print(f"[YOLO] Attempting to open stream: {stream_source}")
        
        # Check if it's a file path that exists, otherwise assume it's a URL
        is_file = os.path.exists(stream_source)
        
        try:
            if ENABLE_LOGS:
                print(f"🔍 Opening video capture for: {stream_source}")
            cap = cv2.VideoCapture(stream_source)
            if not cap.isOpened():
                if ENABLE_LOGS:
                    print(f"❌ Unable to open stream source: {stream_source}")
                started_event.set()  # Signal completion to unblock the caller
                return

            # Test reading first frame to ensure stream is working
            if ENABLE_LOGS:
                print(f"🔍 Testing first frame read...")
            ret, test_frame = cap.read()
            if not ret:
                if ENABLE_LOGS:
                    print(f"❌ Unable to read first frame from: {stream_source}")
                cap.release()
                started_event.set()
                return

            self.is_running = True
            self.current_video = stream_source
            started_event.set()  # Signal successful start
            if ENABLE_LOGS:
                print(f"🎬 Streaming started for: {stream_source}")

            # Initialize stream synchronizer if available
            stream_sync_available = False
            try:
                from stream_synchronizer import StreamSynchronizer, RealTimeStreamOptimizer
                stream_sync = StreamSynchronizer(target_fps=30, buffer_size=5, max_latency_ms=100)
                stream_optimizer = RealTimeStreamOptimizer(target_fps=30)
                stream_sync_available = True
                stream_sync.start()
                if ENABLE_LOGS:
                    print("🔄 Stream synchronization enabled")
            except ImportError:
                if ENABLE_LOGS:
                    print("⚠️ Stream synchronization not available")

            frame_count = 0
            last_fps_update = time.time()
            
            while self.is_running:
                # Check if we should process this frame (for synchronization)
                if stream_sync_available and not stream_optimizer.should_process_frame():
                    time.sleep(0.001)  # Small delay to prevent busy waiting
                    continue
                
                # Add a small delay to prevent excessive CPU usage
                time.sleep(0.001)
                
                # Debug: vérifier si le stream est toujours actif
                if ENABLE_LOGS and frame_count % 50 == 0:
                    print(f"🔄 Stream check: is_running={self.is_running}, frame_count={frame_count}")
                
                ret, frame = cap.read()
                if not ret:
                    if is_file: # If it's a file, loop it
                        if ENABLE_LOGS:
                            print("🔄 End of video file, looping...")
                        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        frame_count = 0  # Reset frame counter
                        continue
                    else: # If it's a network stream and it ends, stop.
                        if ENABLE_LOGS:
                            print("Network stream ended.")
                        break
                
                # Optimize frame size for better performance
                if stream_sync_available:
                    frame = stream_optimizer.optimize_frame_size(frame, target_width=640)
                
                # Execute detection with timing
                start_time = time.time()
                try:
                    drawn_frame, detections = self._execute_detection(frame)
                    inference_time = (time.time() - start_time) * 1000  # Convert to ms
                except Exception as e:
                    if ENABLE_LOGS:
                        print(f"❌ Error during detection: {e}")
                    inference_time = 0
                    drawn_frame = frame
                    detections = []
                
                # Update performance metrics
                self.inference_time_ms = inference_time
                
                # Add detection to metrics calculator if available
                try:
                    from metrics_calculator import add_detection_result, add_performance_data
                    for detection in detections:
                        add_detection_result({
                            'label': detection.get('label', 'unknown'),
                            'confidence': detection.get('confidence', 0.0),
                            'bbox': [detection.get('x', 0), detection.get('y', 0), 
                                   detection.get('width', 0), detection.get('height', 0)],
                            'timestamp': datetime.now(timezone.utc)
                        })
                    
                    # Add performance data
                    current_fps = stream_optimizer.get_actual_fps() if stream_sync_available else 0
                    add_performance_data(current_fps, inference_time)
                except ImportError:
                    pass  # Metrics calculator not available
                
                # Debug log pour les détections (reduced frequency)
                if ENABLE_LOGS and frame_count % 30 == 0:  # Log every 30 frames
                    if detections:
                        print(f"✅ Frame {frame_count}: {len(detections)} détections, {inference_time:.1f}ms")
                    else:
                        print(f"⚠️ Frame {frame_count}: Aucune détection, {inference_time:.1f}ms")
                
                # Log de debug pour identifier pourquoi le stream s'arrête
                if ENABLE_LOGS and frame_count % 10 == 0:  # Log every 10 frames
                    print(f"🔍 Frame {frame_count}: is_running={self.is_running}, queue_size={self.frame_queue.qsize()}")

                # Put the processed frame into the queue for the web feed
                if not self.frame_queue.full():
                    # Optimize encoding if stream sync is available
                    if stream_sync_available:
                        encode_params = stream_optimizer.optimize_encoding_params(quality=80)
                        _, encoded_frame = cv2.imencode('.jpg', drawn_frame, encode_params)
                        # Convert back to frame for queue
                        drawn_frame = cv2.imdecode(encoded_frame, cv2.IMREAD_COLOR)
                    
                    self.frame_queue.put(drawn_frame)
                else:
                    # If queue is full, remove oldest frame to make room
                    try:
                        self.frame_queue.get_nowait()
                        self.frame_queue.put(drawn_frame)
                    except queue.Empty:
                        pass
                
                # Update FPS calculation
                now = time.time()
                self._frame_times.append(now)
                # Keep the last 20 frame times
                self._frame_times = self._frame_times[-20:]
                if len(self._frame_times) > 1:
                    time_diff = self._frame_times[-1] - self._frame_times[0]
                    self.fps = (len(self._frame_times) - 1) / time_diff if time_diff > 0 else 0
                
                # Add detections to database using callback
                for detection in detections:
                    if self.detection_callback:
                        self.detection_callback(detection)
                
                # Update current detections for real-time display
                self.current_detections = detections
                
                frame_count += 1
                
                # Add a small delay to control frame rate for video files
                if is_file:
                    # Calculate target frame time (30 FPS = ~33ms per frame)
                    target_frame_time = 1.0 / 30.0
                    elapsed = time.time() - now
                    if elapsed < target_frame_time:
                        time.sleep(target_frame_time - elapsed)
                
                # Periodic performance logging
                if now - last_fps_update > 5.0:  # Every 5 seconds
                    if ENABLE_LOGS:
                        print(f"📊 Performance: FPS={self.fps:.1f}, Inference={inference_time:.1f}ms, Frame={frame_count}")
                    last_fps_update = now
            
        except Exception as e:
            error_message = str(e)
            if ENABLE_LOGS:
                print(f"❌ Exception in _process_stream: {e}")
                print(f"   Error type: {type(e).__name__}")
                print(f"   Frame count: {frame_count if 'frame_count' in locals() else 'N/A'}")
                if "Connection" in error_message and "timed out" in error_message:
                    print(f"❌ Erreur de connexion au flux: Timeout. Vérifiez que l'appareil est accessible et que l'URL est correcte.")
                    print(f"   URL tentée: {stream_source}")
                    print(f"   Pour IP Webcam, essayez les formats: http://IP:PORT/video ou http://IP:PORT/videofeed")
                elif "Connection" in error_message and "refused" in error_message:
                    print(f"❌ Connexion refusée. Vérifiez que le serveur est en cours d'exécution sur l'appareil cible.")
                    print(f"   URL tentée: {stream_source}")
                else:
                    print(f"❌ Error during streaming: {e}")
        finally:
            if 'cap' in locals() and cap.isOpened():
                cap.release()
            
            # Stop stream synchronizer
            if 'stream_sync_available' in locals() and stream_sync_available:
                try:
                    stream_sync.stop()
                except:
                    pass
            
            self.is_running = False
            self.current_video = None
            # Clear the queue
            while not self.frame_queue.empty():
                self.frame_queue.get()
            if ENABLE_LOGS:
                print("🛑 Streaming finished")
    
    def start_streaming(self, stream_source):
        """Starts streaming in a separate thread and waits for initialization."""
        # Check if model is loaded
        if self.model is None:
            if ENABLE_LOGS:
                print("❌ Model not loaded, attempting to load...")
            self.load_model()
            if self.model is None:
                if ENABLE_LOGS:
                    print("❌ Failed to load model, cannot start streaming")
                return None
        
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
        if ENABLE_LOGS:
            print(f"🛑 stop_streaming() called - is_running was: {self.is_running}")
        self.is_running = False
        
    def generate_stream_frames(self):
        """Yields frames from the queue for the web feed."""
        while self.is_running:
            try:
                frame = self.frame_queue.get(timeout=0.5)  # Reduced timeout for more responsive streaming
                
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
                # If the queue is empty, yield a placeholder frame or continue
                if not self.is_running:
                    if ENABLE_LOGS:
                        print("Stream generation stopped as processing is no longer running.")
                    break
                # Continue waiting for frames instead of breaking
                continue
    
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