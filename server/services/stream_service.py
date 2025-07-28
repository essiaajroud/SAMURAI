import cv2
from config.stream_config import STREAM_CONFIG, TCP_CONFIG
import time

class StreamService:
    def __init__(self):
        self.last_frame_time = 0
        self.frame_interval = 1.0 / STREAM_CONFIG['target_fps']
        
    def process_frame(self, frame):
        current_time = time.time()
        if current_time - self.last_frame_time < self.frame_interval:
            return None  # Skip frame to maintain target FPS
            
        # Compress frame with optimized parameters
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 
                       STREAM_CONFIG['jpeg_quality']]
        _, encoded_frame = cv2.imencode('.jpg', frame, encode_param)
        
        self.last_frame_time = current_time
        return encoded_frame

    def start_stream(self):
        retry_count = 0
        while retry_count < STREAM_CONFIG['tcp_retry_attempts']:
            try:
                # Stream implementation
                # ...existing code...
                pass
            except ConnectionError:
                retry_count += 1
                time.sleep(TCP_CONFIG['reconnect_delay'])