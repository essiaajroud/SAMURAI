# yolo_detector.py (VERSION FINALE - Dessin manuel robuste et affichage personnalisé)

import cv2
import torch
from ultralytics import YOLO
import os
import time
from datetime import datetime
import threading
import queue
import numpy as np
import traceback

# Imports de configuration
from config import get_config
from gpu_config import gpu_config
from system_monitor import system_monitor

config = get_config()
ENABLE_LOGS = config.ENABLE_LOGS

class YOLODetector:
    def __init__(self, model_path="models/best.onnx", confidence_threshold=0.5, app=None, location_manager=None):
        self.app=app
        self.location_manager = location_manager
        self.device = gpu_config.get_device()
        if ENABLE_LOGS:
            print(f"🔧 Initializing YOLO detector on {self.device}")
            if gpu_config.gpu_available:
                print(f"GPU: {gpu_config.gpu_name}")

        self.model_path = model_path
        self.confidence_threshold = confidence_threshold
        self.model = None
        self.detection_callback = None
        self.is_running = False
        self.current_video = None
        self.frame_queue = queue.Queue(maxsize=30)

        # Métriques de performance
        self.fps = 0.0
        self.inference_time_ms = 0.0
        self.objects_by_class = {}
        self._frame_times = []
        self.seen_track_ids = set()
        self.active_trajectories = 0

        self.onnx_providers = system_monitor.onnx_providers
        self.load_model()

    def load_model(self):
        if not os.path.exists(self.model_path):
            if ENABLE_LOGS: print(f"❌ Model not found: {self.model_path}")
            return
        try:
            self.model = YOLO(self.model_path, task="detect")
            if ENABLE_LOGS: print(f"✅ Model loaded: {self.model_path}")
        except Exception as e:
            if ENABLE_LOGS: print(f"❌ Error loading model: {e}")
            self.model = None

    def set_detection_callback(self, callback):
        self.detection_callback = callback

    def _execute_detection(self, frame):
        """
        Traite une seule frame avec le tracker BoT-SORT et un dessin manuel pour un affichage propre.
        Solution finale pour empêcher les annotations parasites de la bibliothèque.
        """
        if self.model is None:
            return frame, []
        h, w, _ = frame.shape
        try:
            clean_frame_for_drawing = frame.copy()
            start_time = time.perf_counter()
            results = self.model.track(
                source=frame,
                persist=True,
                tracker="botsort.yaml",
                conf=self.confidence_threshold,
                device=self.device,
                verbose=False,
                plots=False
            )
            if self.device.type == 'cuda':
                torch.cuda.synchronize()
            end_time = time.perf_counter()
            
            self.inference_time_ms = (end_time - start_time) * 1000
            now = time.time()
            self._frame_times.append(now)
            self._frame_times = [t for t in self._frame_times if now - t < 2]
            if len(self._frame_times) > 1:
                time_diff = self._frame_times[-1] - self._frame_times[0]
                self.fps = (len(self._frame_times) - 1) / time_diff if time_diff > 0 else 0.0

            detections = []
            self.objects_by_class = {}
            active_tracks_in_frame = 0

            result = results[0]
            if result.boxes is not None and result.boxes.id is not None:
                active_tracks_in_frame = len(result.boxes.id)
                for i, track_id_tensor in enumerate(result.boxes.id):
                    track_id = int(track_id_tensor.item())
                    self.seen_track_ids.add(track_id)
                    box = result.boxes.xyxy[i].cpu().numpy().astype(int)
                    conf = float(result.boxes.conf[i].cpu().numpy())
                    cls = int(result.boxes.cls[i].cpu().numpy())
                    class_name = result.names.get(cls, 'unknown')
                    x1, y1, x2, y2 = box

                    detection_data = {
                        'id': track_id, 'label': class_name, 'confidence': conf,
                        'x': (x1 + x2) / 2, 'y': (y1 + y2) / 2, 'width': x2 - x1,
                        'height': y2 - y1, 'timestamp': datetime.now().isoformat(),
                        'frame_width': w
                    }
                    detections.append(detection_data)
                    self.objects_by_class[class_name] = self.objects_by_class.get(class_name, 0) + 1
                    
                    # --- 3. DESSINER UNIQUEMENT SUR NOTRE COPIE PROPRE ---
                    dark_green = (0, 100, 0)
                    text_color = (255, 255, 255)

                    label = f"{class_name.replace('_', ' ')} {conf:.1%} ID:{track_id}"
                    
                    cv2.rectangle(clean_frame_for_drawing, (x1, y1), (x2, y2), dark_green, 2)
                    (text_width, text_height), baseline = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
                    cv2.rectangle(clean_frame_for_drawing, (x1, y1 - text_height - baseline - 5), (x1 + text_width, y1), dark_green, cv2.FILLED)
                    cv2.putText(clean_frame_for_drawing, label, (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, text_color, 1)

            self.active_trajectories = active_tracks_in_frame

            if self.detection_callback and detections:
                for det in detections:
                    self.detection_callback(det)

            # 4. Retourner la copie propre sur laquelle nous avons dessiné.
            return clean_frame_for_drawing, detections
        except Exception as e:
            print(f"❌ Error during detection: {e}")
            traceback.print_exc()
            return frame, [] # En cas d'erreur, retourner l'image originale non modifiée.

    def _process_stream(self, stream_source, started_event):
        cap = None
        try:
            cap = cv2.VideoCapture(stream_source)
            if not cap.isOpened():
                raise ConnectionError(f"Failed to open video stream: {stream_source}")

            self.is_running = True
            self.current_video = stream_source
            started_event.set()
            if ENABLE_LOGS: print(f"✅ Stream connected: {stream_source}")

            while self.is_running:
                ret, frame = cap.read()
                if not ret:
                    if ENABLE_LOGS: print("End of video or stream interrupted. Stopping.")
                    break

                drawn_frame, _ = self._execute_detection(frame)
                
                if not self.frame_queue.full():
                    self.frame_queue.put(drawn_frame)
        
        except Exception as e:
            if ENABLE_LOGS: print(f"❌ Stream error: {e}")
            started_event.set()
        
        finally:
            self.is_running = False
            self.current_video = None
            if cap:
                cap.release()
            if ENABLE_LOGS: print("🛑 Streaming finished")

    def start_streaming(self, stream_source):
        if self.is_running:
            self.stop_streaming()
            time.sleep(1)

        self.fps = 0.0
        self.inference_time_ms = 0.0
        self.objects_by_class = {}
        self._frame_times = []
        self.seen_track_ids = set()
        self.active_trajectories = 0

        if ENABLE_LOGS: print(f"▶️ Starting YOLO stream with source: {stream_source}")
        
        started_event = threading.Event()
        thread = threading.Thread(target=self._process_stream, args=(stream_source, started_event))
        thread.daemon = True
        thread.start()

        if started_event.wait(timeout=10) and self.is_running:
            if ENABLE_LOGS: print("✅ Stream successfully initialized.")
            return thread
        else:
            if ENABLE_LOGS: print("❌ Stream failed to start. Check video path and logs.")
            self.is_running = False
            return None

    def stop_streaming(self):
        self.is_running = False

    def generate_stream_frames(self):
        TARGET_FPS = 15
        JPEG_QUALITY = 60
        frame_interval = 1.0 / TARGET_FPS
        while True:
            try:
                start_time = time.time()
                frame = self.frame_queue.get(timeout=1)
                encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY]
                _, jpeg = cv2.imencode('.jpg', frame, encode_param)
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n')
                elapsed_time = time.time() - start_time
                sleep_time = frame_interval - elapsed_time
                if sleep_time > 0:
                    time.sleep(sleep_time)
            except queue.Empty:
                if not self.is_running:
                    if ENABLE_LOGS: print("Stream generation stopped.")
                    break
    
    def get_performance_metrics(self):
        try:
            sys_metrics = system_monitor.get_metrics()
            object_count = sum(self.objects_by_class.values())
            
            metrics = {
                "fps": self.fps,
                "inferenceTime": self.inference_time_ms,
                "cpuUsage": sys_metrics.get('cpu_usage', 0.0),
                "gpuUsage": sys_metrics.get('gpu_usage', 0.0),
                "gpuMemoryUsage": sys_metrics.get('gpu_memory_used', 0.0),
                "memoryUsage": sys_metrics.get('memory_usage', 0.0),
                "objectCount": object_count,
                "objectsByClass": self.objects_by_class,
                "totalTracks": len(self.seen_track_ids),
                "active_trajectories": self.active_trajectories,
            }
            return metrics
        except Exception as e:
            print(f"❌ CRITICAL ERROR in get_performance_metrics: {e}")
            return { "fps": 0, "inferenceTime": 0, "cpuUsage": 0, "gpuUsage": 0, "gpuMemoryUsage": 0, "memoryUsage": 0, "objectCount": 0, "objectsByClass": {}, "totalTracks": 0, "active_trajectories": 0 }

    def get_available_videos(self):
        videos_dir = "videos"
        if not os.path.exists(videos_dir): return []
        video_extensions = ['.mp4', '.avi', '.mov', '.mkv']
        return [os.path.join(videos_dir, f) for f in os.listdir(videos_dir) if any(f.lower().endswith(ext) for ext in video_extensions)]

detector = YOLODetector()