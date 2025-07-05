import cv2
import torch
from ultralytics import YOLO
import os
import time
from datetime import datetime
import threading
import queue

class YOLODetector:
    def __init__(self, model_path="models/best.onnx", confidence_threshold=0.5):
        """
        Initialise le détecteur YOLO
        
        Args:
            model_path (str): Chemin vers le modèle YOLO (.pt ou .onnx)
            confidence_threshold (float): Seuil de confiance pour les détections
        """
        self.model_path = model_path
        self.confidence_threshold = confidence_threshold
        self.model = None
        self.is_running = False
        self.current_video = None
        self.detection_queue = queue.Queue()
        self.detection_callback = None
        
        # Charger le modèle
        self.load_model()
    
    def load_model(self):
        """Charge le modèle YOLO (ONNX ou PyTorch)."""
        if not os.path.exists(self.model_path):
            print(f"❌ Modèle non trouvé: {self.model_path}")
            self.model = None
            return
        try:
            self.model = YOLO(self.model_path, task="detect")
            print(f"✅ Modèle chargé: {self.model_path}")
        except Exception as e:
            print(f"❌ Erreur lors du chargement du modèle: {e}")
            self.model = None

    
    def set_detection_callback(self, callback):
        """Définit la fonction de callback pour les détections"""
        self.detection_callback = callback
    
    def process_video(self, video_path, save_results=True):
        """
        Traite une vidéo avec le modèle YOLO
        
        Args:
            video_path (str): Chemin vers la vidéo
            save_results (bool): Sauvegarder les résultats
        """
        if not os.path.exists(video_path):
            print(f"❌ Vidéo non trouvée: {video_path}")
            return
        
        if self.model is None:
            print("❌ Modèle non chargé")
            return
        
        try:
            # Ouvrir la vidéo
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                print(f"❌ Impossible d'ouvrir la vidéo: {video_path}")
                return
            
            # Obtenir les propriétés de la vidéo
            fps = int(cap.get(cv2.CAP_PROP_FPS))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            print(f"📹 Traitement de la vidéo: {video_path}")
            print(f"📊 FPS: {fps}, Résolution: {width}x{height}, Frames: {total_frames}")
            
            # Préparer la sauvegarde des résultats
            if save_results:
                output_path = video_path.replace('.mp4', '_detected.mp4')
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
            
            frame_count = 0
            start_time = time.time()
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # Détecter les objets
                results = self.model(frame, conf=self.confidence_threshold, verbose=False)
                
                # Traiter les détections
                detections = []
                for result in results:
                    boxes = result.boxes
                    if boxes is not None:
                        for box in boxes:
                            # Coordonnées du bounding box
                            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                            x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
                            
                            # Classe et confiance
                            cls = int(box.cls[0].cpu().numpy())
                            conf = float(box.conf[0].cpu().numpy())
                            
                            # Nom de la classe
                            class_name = result.names[cls]
                            
                            # Calculer le centre
                            center_x = (x1 + x2) / 2
                            center_y = (y1 + y2) / 2
                            
                            # Créer l'objet de détection
                            detection = {
                                'id': len(detections) + 1,
                                'label': class_name,
                                'confidence': conf,
                                'x': center_x,
                                'y': center_y,
                                'bbox': [x1, y1, x2, y2],
                                'timestamp': datetime.now().isoformat(),
                                'frame': frame_count
                            }
                            
                            detections.append(detection)
                            
                            # Dessiner le bounding box
                            if save_results:
                                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                                cv2.putText(frame, f'{class_name} {conf:.2f}', 
                                          (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                
                # Envoyer les détections via callback
                if self.detection_callback and detections:
                    for detection in detections:
                        self.detection_callback(detection)
                
                # Sauvegarder le frame
                if save_results:
                    out.write(frame)
                
                frame_count += 1
                
                # Afficher le progrès
                if frame_count % 30 == 0:
                    elapsed = time.time() - start_time
                    fps_processed = frame_count / elapsed
                    progress = (frame_count / total_frames) * 100
                    print(f"📈 Progrès: {progress:.1f}% ({frame_count}/{total_frames}) - FPS: {fps_processed:.1f}")
            
            # Nettoyer
            cap.release()
            if save_results:
                out.release()
                print(f"✅ Vidéo traitée sauvegardée: {output_path}")
            
            total_time = time.time() - start_time
            print(f"✅ Traitement terminé en {total_time:.2f} secondes")
            
        except Exception as e:
            print(f"❌ Erreur lors du traitement: {e}")
    
    def process_video_stream(self, video_path):
        """
        Traite une vidéo en streaming (pour l'interface web)
        
        Args:
            video_path (str): Chemin vers la vidéo
        """
        if not os.path.exists(video_path):
            print(f"❌ Vidéo non trouvée: {video_path}")
            return
        
        if self.model is None:
            print("❌ Modèle non chargé")
            return
        
        try:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                print(f"❌ Impossible d'ouvrir la vidéo: {video_path}")
                return
            
            self.is_running = True
            self.current_video = video_path
            
            while self.is_running:
                ret, frame = cap.read()
                if not ret:
                    # Revenir au début de la vidéo
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    continue
                
                # Détecter les objets
                results = self.model(frame, conf=self.confidence_threshold, verbose=False)
                
                # Traiter les détections
                detections = []
                for result in results:
                    boxes = result.boxes
                    if boxes is not None:
                        for box in boxes:
                            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                            cls = int(box.cls[0].cpu().numpy())
                            conf = float(box.conf[0].cpu().numpy())
                            class_name = result.names[cls]
                            
                            center_x = (x1 + x2) / 2
                            center_y = (y1 + y2) / 2
                            
                            detection = {
                                'id': len(detections) + 1,
                                'label': class_name,
                                'confidence': conf,
                                'x': center_x,
                                'y': center_y,
                                'bbox': [int(x1), int(y1), int(x2), int(y2)],
                                'timestamp': datetime.now().isoformat()
                            }
                            
                            detections.append(detection)
                
                # Envoyer les détections
                if self.detection_callback and detections:
                    for detection in detections:
                        self.detection_callback(detection)
                
                # Contrôler la vitesse de traitement
                time.sleep(0.033)  # ~30 FPS
            
            cap.release()
            
        except Exception as e:
            print(f"❌ Erreur lors du streaming: {e}")
        finally:
            self.is_running = False
            self.current_video = None
    
    def start_streaming(self, video_path):
        """Démarre le streaming d'une vidéo dans un thread séparé"""
        if self.is_running:
            self.stop_streaming()
        
        thread = threading.Thread(target=self.process_video_stream, args=(video_path,))
        thread.daemon = True
        thread.start()
        return thread
    
    def stop_streaming(self):
        """Arrête le streaming"""
        self.is_running = False
    
    def get_available_videos(self):
        """Retourne la liste des vidéos disponibles"""
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
        """Retourne les informations sur le modèle"""
        if self.model is None:
            return {"status": "not_loaded", "message": "Modèle non chargé"}
        
        return {
            "status": "loaded",
            "model_path": self.model_path,
            "confidence_threshold": self.confidence_threshold,
            "is_running": self.is_running,
            "current_video": self.current_video
        }

    def generate_stream_frames(self, video_path):
        import cv2
        import os
        if not os.path.exists(video_path):
            print(f"❌ Vidéo non trouvée: {video_path}")
            return
        if self.model is None:
            print("❌ Modèle non chargé")
            return

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            print(f"❌ Impossible d'ouvrir la vidéo: {video_path}")
            return

        while True:
            ret, frame = cap.read()
            if not ret:
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue

            # Détection
            results = self.model(frame, conf=self.confidence_threshold, verbose=False)
            for result in results:
                boxes = result.boxes
                if boxes is not None:
                    for box in boxes:
                        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                        cls = int(box.cls[0].cpu().numpy())
                        conf = float(box.conf[0].cpu().numpy())
                        class_name = result.names[cls]
                        cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0,255,0), 2)
                        cv2.putText(frame, f"{class_name} {conf:.2f}", (int(x1), int(y1)-10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,0), 2)

            # Encodage JPEG
            ret2, jpeg = cv2.imencode('.jpg', frame)
            if not ret2:
                continue
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n')
        cap.release()

# Instance globale du détecteur
detector = YOLODetector()