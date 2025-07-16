import cv2
import torch
from ultralytics import YOLO
import os
import time
from datetime import datetime
import threading
import queue

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
        self.detection_queue = queue.Queue()
        self.detection_callback = None
        # Load the model
        self.load_model()

    def load_model(self):
        """Load the YOLO model (ONNX or PyTorch)."""
        if not os.path.exists(self.model_path):
            print(f"❌ Model not found: {self.model_path}")
            self.model = None
            return
        try:
            self.model = YOLO(self.model_path, task="detect")
            print(f"✅ Model loaded: {self.model_path}")
        except Exception as e:
            print(f"❌ Error loading model: {e}")
            self.model = None

    def set_detection_callback(self, callback):
        """Set the callback function for detections."""
        self.detection_callback = callback

    def process_video(self, video_path, save_results=True):
        """
        Process a video with the YOLO model.
        Args:
            video_path (str): Path to the video
            save_results (bool): Whether to save results
        """
        print(f"[YOLO] Processing video or stream: {video_path}")  # Ajout du log
        if not os.path.exists(video_path):
            print(f"❌ Video not found: {video_path}")
            return
        if self.model is None:
            print("❌ Model not loaded")
            return
        try:
            # Open the video
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                print(f"❌ Unable to open video: {video_path}")
                return
            # Get video properties
            fps = int(cap.get(cv2.CAP_PROP_FPS))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            print(f"📹 Processing video: {video_path}")
            print(f"📊 FPS: {fps}, Resolution: {width}x{height}, Frames: {total_frames}")
            # Prepare to save results
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
                # Detect objects
                results = self.model(frame, conf=self.confidence_threshold, verbose=False)
                # Process detections
                detections = []
                for result in results:
                    boxes = result.boxes
                    if boxes is not None:
                        for box in boxes:
                            # Bounding box coordinates
                            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                            x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
                            # Class and confidence
                            cls = int(box.cls[0].cpu().numpy())
                            conf = float(box.conf[0].cpu().numpy())
                            # Class name
                            class_name = result.names[cls]
                            # Calculate center
                            center_x = (x1 + x2) / 2
                            center_y = (y1 + y2) / 2
                            # Create detection object
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
                            # Draw bounding box
                            if save_results:
                                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                                cv2.putText(frame, f'{class_name} {conf:.2f}', 
                                          (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                # Send detections via callback
                if self.detection_callback and detections:
                    for detection in detections:
                        self.detection_callback(detection)
                # Save the frame
                if save_results:
                    out.write(frame)
                frame_count += 1
                # Show progress
                if frame_count % 30 == 0:
                    elapsed = time.time() - start_time
                    fps_processed = frame_count / elapsed
                    progress = (frame_count / total_frames) * 100
                    print(f"📈 Progress: {progress:.1f}% ({frame_count}/{total_frames}) - FPS: {fps_processed:.1f}")
            # Cleanup
            cap.release()
            if save_results:
                out.release()
                print(f"✅ Processed video saved: {output_path}")
            total_time = time.time() - start_time
            print(f"✅ Processing finished in {total_time:.2f} seconds")
        except Exception as e:
            print(f"❌ Error during processing: {e}")

    def process_video_stream(self, video_path):
        """
        Process a video in streaming mode (for web interface).
        Args:
            video_path (str): Path to the video
        """
        print(f"[YOLO] Streaming started for: {video_path}")  # Ajout du log
        if not os.path.exists(video_path):
            print(f"❌ Video not found: {video_path}")
            return
        if self.model is None:
            print("❌ Model not loaded")
            return
        try:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                print(f"❌ Unable to open video: {video_path}")
                return
            self.is_running = True
            self.current_video = video_path
            print(f"🎬 Streaming started for: {video_path}")
            while self.is_running:
                ret, frame = cap.read()
                if not ret:
                    # Loop back to start of video
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    continue
                # Detect objects
                results = self.model(frame, conf=self.confidence_threshold, verbose=False)
                # Process detections
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
                
                # Send detections
                if self.detection_callback and detections:
                    for detection in detections:
                        self.detection_callback(detection)
                
                # Control processing speed
                time.sleep(0.033)  # ~30 FPS
            
            cap.release()
            
        except Exception as e:
            print(f"❌ Error during streaming: {e}")
        finally:
            self.is_running = False
            self.current_video = None
            print("🛑 Streaming finished")
    
    def start_streaming(self, video_path):
        """Starts streaming a video in a separate thread."""
        if self.is_running:
            print("🔄 Stopping previous streaming...")
            self.stop_streaming()
        
        print(f"▶️ Starting YOLO streaming with video: {video_path}")
        thread = threading.Thread(target=self.process_video_stream, args=(video_path,))
        thread.daemon = True
        thread.start()
        return thread
    
    def stop_streaming(self):
        """Stops the streaming."""
        print("🛑 Stopping YOLO streaming...")
        self.is_running = False
        self.current_video = None
        print("✅ YOLO streaming stopped")
    
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

    def generate_stream_frames(self, video_path):
        import cv2
        import os
        from datetime import datetime
        import uuid
        
        if not os.path.exists(video_path):
            print(f"❌ Video not found: {video_path}")
            return
        if self.model is None:
            print("❌ Model not loaded")
            return

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            print(f"❌ Unable to open video: {video_path}")
            return

        frame_count = 0
        while self.is_running:  # Check streaming status
            ret, frame = cap.read()
            if not ret:
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                frame_count = 0
                continue

            # Only detect if streaming is active
            if not self.is_running:
                break
                
            results = self.model(frame, conf=self.confidence_threshold, verbose=False)
            detections_in_frame = []
            
            for result in results:
                boxes = result.boxes
                if boxes is not None:
                    for box in boxes:
                        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                        cls = int(box.cls[0].cpu().numpy())
                        conf = float(box.conf[0].cpu().numpy())
                        class_name = result.names[cls]
                        
                        # Draw on the frame
                        cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0,255,0), 2)
                        cv2.putText(frame, f"{class_name} {conf:.2f}", (int(x1), int(y1)-10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,0), 2)
                        
                        # Prepare detection data for saving
                        center_x = (x1 + x2) / 2
                        center_y = (y1 + y2) / 2
                        
                        detection_data = {
                            'id': frame_count * 1000 + len(detections_in_frame),  # Unique ID based on frame
                            'label': class_name,
                            'confidence': conf,
                            'x': center_x,
                            'y': center_y,
                            'bbox': [int(x1), int(y1), int(x2), int(y2)],
                            'timestamp': datetime.now().isoformat(),
                            'frame_number': frame_count
                        }
                        
                        detections_in_frame.append(detection_data)
            
            # Save detections in real-time via callback only if streaming is active
            if self.is_running and self.detection_callback and detections_in_frame:
                for detection in detections_in_frame:
                    try:
                        self.detection_callback(detection)
                    except Exception as e:
                        print(f"❌ Error saving detection: {e}")

            # JPEG encoding
            ret2, jpeg = cv2.imencode('.jpg', frame)
            if not ret2:
                continue
                
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n')
            
            frame_count += 1
            
        cap.release()

# Global detector instance
detector = YOLODetector()