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
        """Load the YOLO model (ONNX or PyTorch)."""
        if not os.path.exists(self.model_path):
            if ENABLE_LOGS:
                print(f"❌ Model not found: {self.model_path}")
            self.model = None
            return
        try:
            self.model = YOLO(self.model_path, task="detect")
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
        """
        if self.model is None:
            return frame, []

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
            
                    # Create detection object
                    detection_data = {
                        'label': class_name,
                        'confidence': conf,
                        'x': (x1 + x2) / 2,
                        'y': (y1 + y2) / 2,
                        'width': x2 - x1,
                        'height': y2 - y1,
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
            cap = cv2.VideoCapture(stream_source)
            if not cap.isOpened():
                if ENABLE_LOGS:
                    print(f"❌ Unable to open stream source: {stream_source}")
                started_event.set()  # Signal completion to unblock the caller
                return

            self.is_running = True
            self.current_video = stream_source
            started_event.set()  # Signal successful start
            if ENABLE_LOGS:
                print(f"🎬 Streaming started for: {stream_source}")

            while self.is_running:
                ret, frame = cap.read()
                if not ret:
                    if is_file: # If it's a file, loop it
                        if ENABLE_LOGS:
                            print("Looping video file...")
                        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        continue
                    else: # If it's a network stream and it ends, stop.
                        if ENABLE_LOGS:
                            print("Network stream ended.")
                        break
                
                # Execute detection
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
            error_message = str(e)
            if ENABLE_LOGS:
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
            self.is_running = False
            self.current_video = None
            # Clear the queue
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
            print("🛑 Stopping YOLO stream...")
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
        return {
            "fps": self.fps,
            "inferenceTime": self.inference_time_ms,
        }

    def get_objects_by_class(self):
        """Returns a dictionary with the count of detected objects per class."""
        return self.objects_by_class

# Global detector instance
detector = YOLODetector()