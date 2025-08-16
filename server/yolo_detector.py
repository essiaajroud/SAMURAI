# yolo_detector.py (VERSION FINALE ET CORRIGÉE)

import cv2
import torch
from ultralytics import YOLO
import os
import time
from datetime import datetime
import threading
import queue
import numpy as np

# Imports de configuration
from config import get_config
from gpu_config import gpu_config
from system_monitor import system_monitor
from bytetrack_tracker import ByteTracker

config = get_config()
ENABLE_LOGS = config.ENABLE_LOGS

class YOLODetector:
    def __init__(self, model_path="models/best.onnx", confidence_threshold=0.5):
        # Configuration Matérielle
        self.device = gpu_config.get_device()
        if ENABLE_LOGS:
            print(f"🔧 Initializing YOLO detector on {self.device}")
            if gpu_config.gpu_available:
                print(f"GPU: {gpu_config.gpu_name}")

        # Attributs du Modèle
        self.model_path = model_path
        self.confidence_threshold = confidence_threshold
        self.model = None
        self.detection_callback = None

        # État du Streaming
        self.is_running = False
        self.current_video = None
        self.frame_queue = queue.Queue(maxsize=30)

        # --- ÉTAT PERSISTANT POUR LES MÉTRIQUES ---
        # C'est la source de vérité pour l'API. Initialisé à zéro.
        self.fps = 0.0
        self.inference_time_ms = 0.0
        self.objects_by_class = {}
        self._frame_times = []  # Pour le calcul du FPS

        # Composants Externes
        self.tracker = ByteTracker(track_thresh=0.5, track_buffer=30, match_thresh=0.8)
        self.onnx_providers = system_monitor.onnx_providers
        self.load_model()

    def load_model(self):
        """Charge le modèle YOLO."""
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
        TRAITE UNE SEULE FRAME ET MET À JOUR TOUTES LES MÉTRIQUES.
        """
        if self.model is None:
            return frame, []

        try:
            # --- 1. MESURE DU TEMPS D'INFÉRENCE ---
            start_time = time.perf_counter()
            results = self.model.predict(
                source=frame,
                conf=self.confidence_threshold,
                device=self.device,
                verbose=False
            )
            # Synchronisation pour une mesure précise sur GPU
            if self.device.type == 'cuda':
                torch.cuda.synchronize()
            end_time = time.perf_counter()

            # --- 2. MISE À JOUR DES MÉTRIQUES DE PERFORMANCE ---
            self.inference_time_ms = (end_time - start_time) * 1000

            now = time.time()
            self._frame_times.append(now)
            self._frame_times = self._frame_times[-20:] # Garder les 20 derniers
            if len(self._frame_times) > 1:
                time_diff = self._frame_times[-1] - self._frame_times[0]
                self.fps = (len(self._frame_times) - 1) / time_diff if time_diff > 0 else 0.0

            # --- 3. TRAITEMENT DES DÉTECTIONS ET TRACKING ---
            detections = []
            dets_for_tracking = []
            # Réinitialiser le compteur pour CETTE frame
            self.objects_by_class = {} 

            for result in results:
                boxes = result.boxes
                if boxes is not None:
                    for box in boxes:
                        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)
                        conf = float(box.conf[0].cpu().numpy())
                        cls = int(box.cls[0].cpu().numpy())
                        class_name = result.names.get(cls, 'unknown')

                        self.objects_by_class[class_name] = self.objects_by_class.get(class_name, 0) + 1
                        
                        detections.append({
                            'label': class_name, 'confidence': conf, 'x': (x1 + x2) / 2, 'y': (y1 + y2) / 2,
                            'bbox': [x1, y1, x2, y2]
                        })
                        dets_for_tracking.append([x1, y1, x2, y2, conf, cls])

            tracks = self.tracker.update(dets_for_tracking)

            # Associer les IDs de tracking aux détections
            for det in detections:
                det_bbox = det['bbox']
                best_iou = 0
                best_track_id = -1
                for track in tracks:
                    iou = self._calculate_iou(det_bbox, track['bbox'])
                    if iou > best_iou:
                        best_iou = iou
                        best_track_id = track['track_id']
                det['id'] = best_track_id

            # Dessiner sur l'image
            for det in detections:
                x1, y1, x2, y2 = det['bbox']
                label = f"{det['label']} {det['confidence']:.2f} ID:{det['id']}"
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

            if self.detection_callback and detections:
                for det in detections:
                    self.detection_callback(det)

            return frame, detections
        except Exception as e:
            print(f"❌ Error during detection: {e}")
            # En cas d'erreur, on ne met pas à jour les métriques pour ne pas les fausser
            return frame, []

    def _process_stream(self, stream_source, started_event):
        """Boucle principale qui lit la vidéo et appelle _execute_detection."""
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
                    break # Sortir de la boucle

                # Toute la logique est maintenant dans _execute_detection
                drawn_frame, _ = self._execute_detection(frame)
                
                if not self.frame_queue.full():
                    self.frame_queue.put(drawn_frame)
        
        except Exception as e:
            if ENABLE_LOGS: print(f"❌ Stream error: {e}")
            started_event.set() # Signaler l'échec
        
        finally:
            self.is_running = False
            self.current_video = None
            if cap:
                cap.release()
            if ENABLE_LOGS: print("🛑 Streaming finished")

    def start_streaming(self, stream_source):
        """Démarre le thread de streaming."""
        if self.is_running:
            self.stop_streaming()
            time.sleep(1)

        # Réinitialiser les métriques avant de démarrer un nouveau flux
        self.fps = 0.0
        self.inference_time_ms = 0.0
        self.objects_by_class = {}
        self._frame_times = []
        self.tracker.reset()

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
        """Génère les frames pour le flux web."""
        while True: # Boucle infinie pour garder la connexion ouverte
            try:
                frame = self.frame_queue.get(timeout=1)
                _, jpeg = cv2.imencode('.jpg', frame)
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n')
            except queue.Empty:
                if not self.is_running:
                    # Si le stream est arrêté, on sort de la boucle pour fermer la connexion
                    if ENABLE_LOGS: print("Stream generation stopped.")
                    break
    
    def get_performance_metrics(self):
        """Lit et retourne le dernier état connu des métriques."""
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
                "totalTracks": self.tracker.next_id - 1,
                "active_trajectories": len(self.tracker.tracks),
            }
            return metrics
        except Exception as e:
            print(f"❌ CRITICAL ERROR in get_performance_metrics: {e}")
            return { "fps": 0, "inferenceTime": 0, "cpuUsage": 0, "gpuUsage": 0, "gpuMemoryUsage": 0, "memoryUsage": 0, "objectCount": 0, "objectsByClass": {}, "totalTracks": 0, "active_trajectories": 0 }

    def _calculate_iou(self, bbox1, bbox2):
        x1 = max(bbox1[0], bbox2[0])
        y1 = max(bbox1[1], bbox2[1])
        x2 = min(bbox1[2], bbox2[2])
        y2 = min(bbox1[3], bbox2[3])
        intersection = max(0, x2 - x1) * max(0, y2 - y1)
        area1 = (bbox1[2] - bbox1[0]) * (bbox1[3] - bbox1[1])
        area2 = (bbox2[2] - bbox2[0]) * (bbox2[3] - bbox2[1])
        union = area1 + area2 - intersection
        return intersection / union if union > 0 else 0.0
    
    # ... autres méthodes utilitaires comme get_available_videos ...
    def get_available_videos(self):
        """Returns the list of available videos."""
        videos_dir = "videos"
        if not os.path.exists(videos_dir): return []
        video_extensions = ['.mp4', '.avi', '.mov', '.mkv']
        return [os.path.join(videos_dir, f) for f in os.listdir(videos_dir) if any(f.lower().endswith(ext) for ext in video_extensions)]

# Instance globale
detector = YOLODetector()