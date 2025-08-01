"""
Stream Synchronizer for Real-Time Video Processing
Handles frame synchronization, buffering, and real-time streaming optimization
"""

import cv2
import time
import threading
import queue
import numpy as np
from collections import deque
from typing import Optional, Callable, Dict, Any
from dataclasses import dataclass
import logging

@dataclass
class FrameInfo:
    frame: np.ndarray
    timestamp: float
    frame_number: int
    processing_time: float = 0.0
    detection_results: Optional[Dict] = None

class StreamSynchronizer:
    def __init__(self, 
                 target_fps: int = 30,
                 buffer_size: int = 5,
                 max_latency_ms: int = 100,
                 enable_frame_dropping: bool = True):
        """
        Initialize stream synchronizer
        
        Args:
            target_fps: Target frames per second
            buffer_size: Number of frames to buffer
            max_latency_ms: Maximum allowed latency in milliseconds
            enable_frame_dropping: Whether to drop frames to maintain sync
        """
        self.target_fps = target_fps
        self.frame_interval = 1.0 / target_fps
        self.buffer_size = buffer_size
        self.max_latency_ms = max_latency_ms
        self.enable_frame_dropping = enable_frame_dropping
        
        # Frame buffers
        self.input_queue = queue.Queue(maxsize=buffer_size * 2)
        self.output_queue = queue.Queue(maxsize=buffer_size)
        self.frame_buffer = deque(maxlen=buffer_size)
        
        # Synchronization state
        self.is_running = False
        self.last_frame_time = 0
        self.frame_counter = 0
        self.dropped_frames = 0
        self.processed_frames = 0
        
        # Performance metrics
        self.avg_processing_time = 0.0
        self.avg_latency = 0.0
        self.fps_actual = 0.0
        
        # Threading
        self.sync_thread = None
        self.processing_thread = None
        self.lock = threading.Lock()
        
        # Callbacks
        self.frame_processor: Optional[Callable] = None
        self.on_frame_processed: Optional[Callable] = None
        
        # Logging
        self.logger = logging.getLogger(__name__)
    
    def set_frame_processor(self, processor: Callable[[np.ndarray], Dict]):
        """Set the frame processing function"""
        self.frame_processor = processor
    
    def set_frame_processed_callback(self, callback: Callable[[FrameInfo], None]):
        """Set callback for when frame is processed"""
        self.on_frame_processed = callback
    
    def start(self):
        """Start the synchronizer"""
        if self.is_running:
            return
        
        self.is_running = True
        self.frame_counter = 0
        self.dropped_frames = 0
        self.processed_frames = 0
        
        # Start synchronization thread
        self.sync_thread = threading.Thread(target=self._sync_loop, daemon=True)
        self.sync_thread.start()
        
        # Start processing thread
        self.processing_thread = threading.Thread(target=self._processing_loop, daemon=True)
        self.processing_thread.start()
        
        self.logger.info(f"🚀 Stream synchronizer started (target FPS: {self.target_fps})")
    
    def stop(self):
        """Stop the synchronizer"""
        self.is_running = False
        
        # Clear queues
        while not self.input_queue.empty():
            try:
                self.input_queue.get_nowait()
            except queue.Empty:
                break
        
        while not self.output_queue.empty():
            try:
                self.output_queue.get_nowait()
            except queue.Empty:
                break
        
        self.frame_buffer.clear()
        
        self.logger.info("🛑 Stream synchronizer stopped")
    
    def add_frame(self, frame: np.ndarray) -> bool:
        """
        Add a frame to the input queue
        
        Returns:
            bool: True if frame was added, False if dropped
        """
        if not self.is_running:
            return False
        
        current_time = time.time()
        frame_info = FrameInfo(
            frame=frame.copy(),
            timestamp=current_time,
            frame_number=self.frame_counter
        )
        
        try:
            # Check if we should drop this frame
            if self.enable_frame_dropping and self._should_drop_frame(current_time):
                self.dropped_frames += 1
                return False
            
            # Add to input queue with timeout
            self.input_queue.put(frame_info, timeout=0.1)
            self.frame_counter += 1
            return True
            
        except queue.Full:
            self.dropped_frames += 1
            return False
    
    def get_frame(self, timeout: float = 0.1) -> Optional[FrameInfo]:
        """Get the next processed frame"""
        try:
            return self.output_queue.get(timeout=timeout)
        except queue.Empty:
            return None
    
    def _should_drop_frame(self, current_time: float) -> bool:
        """Determine if frame should be dropped to maintain sync"""
        if self.last_frame_time == 0:
            return False
        
        time_since_last = current_time - self.last_frame_time
        
        # Drop if we're too far behind
        if time_since_last > self.frame_interval * 2:
            return True
        
        # Drop if buffer is full and we're behind schedule
        if (self.input_queue.qsize() >= self.buffer_size and 
            time_since_last < self.frame_interval * 0.5):
            return True
        
        return False
    
    def _sync_loop(self):
        """Main synchronization loop"""
        while self.is_running:
            try:
                # Get frame from input queue
                frame_info = self.input_queue.get(timeout=0.1)
                
                # Calculate target output time
                target_time = frame_info.timestamp + (self.max_latency_ms / 1000.0)
                current_time = time.time()
                
                # Wait if necessary to maintain timing
                if current_time < target_time:
                    time.sleep(target_time - current_time)
                
                # Add to frame buffer
                with self.lock:
                    self.frame_buffer.append(frame_info)
                
                # Update timing
                self.last_frame_time = time.time()
                
            except queue.Empty:
                continue
            except Exception as e:
                self.logger.error(f"Error in sync loop: {e}")
    
    def _processing_loop(self):
        """Frame processing loop"""
        while self.is_running:
            try:
                # Get frame from buffer
                frame_info = None
                with self.lock:
                    if self.frame_buffer:
                        frame_info = self.frame_buffer.popleft()
                
                if frame_info is None:
                    time.sleep(0.01)
                    continue
                
                # Process frame
                start_time = time.time()
                
                if self.frame_processor:
                    try:
                        detection_results = self.frame_processor(frame_info.frame)
                        frame_info.detection_results = detection_results
                    except Exception as e:
                        self.logger.error(f"Frame processing error: {e}")
                        frame_info.detection_results = None
                
                processing_time = (time.time() - start_time) * 1000  # Convert to ms
                frame_info.processing_time = processing_time
                
                # Update metrics
                self._update_metrics(processing_time, frame_info.timestamp)
                
                # Add to output queue
                try:
                    self.output_queue.put(frame_info, timeout=0.1)
                    self.processed_frames += 1
                except queue.Full:
                    self.dropped_frames += 1
                
                # Call callback if set
                if self.on_frame_processed:
                    try:
                        self.on_frame_processed(frame_info)
                    except Exception as e:
                        self.logger.error(f"Callback error: {e}")
                
            except Exception as e:
                self.logger.error(f"Error in processing loop: {e}")
    
    def _update_metrics(self, processing_time: float, frame_timestamp: float):
        """Update performance metrics"""
        current_time = time.time()
        latency = (current_time - frame_timestamp) * 1000  # Convert to ms
        
        # Update averages with exponential moving average
        alpha = 0.1
        self.avg_processing_time = (alpha * processing_time + 
                                   (1 - alpha) * self.avg_processing_time)
        self.avg_latency = (alpha * latency + 
                           (1 - alpha) * self.avg_latency)
        
        # Calculate actual FPS
        if self.processed_frames > 0:
            elapsed_time = current_time - self.last_frame_time
            if elapsed_time > 0:
                self.fps_actual = 1.0 / elapsed_time
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics"""
        return {
            'target_fps': self.target_fps,
            'actual_fps': self.fps_actual,
            'processed_frames': self.processed_frames,
            'dropped_frames': self.dropped_frames,
            'drop_rate': (self.dropped_frames / max(1, self.dropped_frames + self.processed_frames)) * 100,
            'avg_processing_time_ms': self.avg_processing_time,
            'avg_latency_ms': self.avg_latency,
            'buffer_usage': self.input_queue.qsize() / self.input_queue.maxsize * 100,
            'is_running': self.is_running
        }
    
    def reset_metrics(self):
        """Reset performance metrics"""
        self.frame_counter = 0
        self.dropped_frames = 0
        self.processed_frames = 0
        self.avg_processing_time = 0.0
        self.avg_latency = 0.0
        self.fps_actual = 0.0

class RealTimeStreamOptimizer:
    """Optimizer for real-time video streaming"""
    
    def __init__(self, target_fps: int = 30):
        self.target_fps = target_fps
        self.frame_interval = 1.0 / target_fps
        self.last_frame_time = 0
        self.frame_times = deque(maxlen=30)
        
    def should_process_frame(self) -> bool:
        """Determine if current frame should be processed"""
        current_time = time.time()
        
        # Always process first frame
        if self.last_frame_time == 0:
            self.last_frame_time = current_time
            self.frame_times.append(current_time)
            return True
        
        # Check if enough time has passed
        time_since_last = current_time - self.last_frame_time
        if time_since_last >= self.frame_interval:
            self.last_frame_time = current_time
            self.frame_times.append(current_time)
            return True
        
        return False
    
    def get_actual_fps(self) -> float:
        """Calculate actual FPS from recent frame times"""
        if len(self.frame_times) < 2:
            return 0.0
        
        # Calculate average time between frames
        intervals = []
        for i in range(1, len(self.frame_times)):
            intervals.append(self.frame_times[i] - self.frame_times[i-1])
        
        if not intervals:
            return 0.0
        
        avg_interval = sum(intervals) / len(intervals)
        return 1.0 / avg_interval if avg_interval > 0 else 0.0
    
    def optimize_frame_size(self, frame: np.ndarray, target_width: int = 640) -> np.ndarray:
        """Optimize frame size for streaming"""
        height, width = frame.shape[:2]
        
        if width <= target_width:
            return frame
        
        # Calculate new height maintaining aspect ratio
        aspect_ratio = width / height
        new_height = int(target_width / aspect_ratio)
        
        # Resize frame
        resized = cv2.resize(frame, (target_width, new_height), 
                           interpolation=cv2.INTER_AREA)
        
        return resized
    
    def optimize_encoding_params(self, quality: int = 80) -> list:
        """Get optimized encoding parameters"""
        return [
            int(cv2.IMWRITE_JPEG_QUALITY), quality,
            int(cv2.IMWRITE_JPEG_OPTIMIZE), 1,
            int(cv2.IMWRITE_JPEG_PROGRESSIVE), 1
        ] 