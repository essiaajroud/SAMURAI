import psutil
import torch
import time
import threading
import onnxruntime as ort

class SystemMonitor:
    def __init__(self):
        self.gpu_available = torch.cuda.is_available()
        self._metrics = {
            'cpu_usage': 0,
            'gpu_usage': 0,
            'gpu_memory_used': 0,
            'memory_usage': 0
        }
        self._running = False
        self._setup_onnx_providers()
        self._start_monitoring()

    def _setup_onnx_providers(self):
        """Setup ONNX Runtime providers"""
        self.onnx_providers = []
        if self.gpu_available:
            # Configure CUDA provider options
            cuda_provider_options = {
                "device_id": 0,
                "arena_extend_strategy": "kNextPowerOfTwo",
                "gpu_mem_limit": 2 * 1024 * 1024 * 1024,  # 2GB
                "cudnn_conv_algo_search": "EXHAUSTIVE",
                "do_copy_in_default_stream": True,
            }
            self.onnx_providers.append(('CUDAExecutionProvider', cuda_provider_options))
        self.onnx_providers.append('CPUExecutionProvider')
        
        # Initialize ONNX Runtime session for monitoring
        try:
            self.ort_session = ort.InferenceSession("models/best.onnx", 
                                                  providers=self.onnx_providers)
            print(f"✅ ONNX Runtime initialized with providers: {self.ort_session.get_providers()}")
        except Exception as e:
            print(f"⚠️ ONNX Runtime initialization error: {e}")

    def _start_monitoring(self):
        """Start background monitoring thread"""
        self._running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()

    def _monitor_loop(self):
        """Monitor system metrics"""
        while self._running:
            # CPU & Memory
            self._metrics['cpu_usage'] = psutil.cpu_percent(interval=0.1)
            self._metrics['memory_usage'] = psutil.virtual_memory().percent

            # GPU Metrics
            if self.gpu_available:
                try:
                    # GPU Memory from PyTorch
                    allocated = torch.cuda.memory_allocated()
                    reserved = torch.cuda.memory_reserved()
                    total = torch.cuda.get_device_properties(0).total_memory
                    
                    self._metrics['gpu_memory_used'] = (allocated / total) * 100
                    
                    # GPU Usage from CUDA Events
                    current_stream = torch.cuda.current_stream()
                    start_event = torch.cuda.Event(enable_timing=True)
                    end_event = torch.cuda.Event(enable_timing=True)
                    
                    start_event.record()
                    torch.cuda.synchronize()
                    end_event.record()
                    end_event.synchronize()
                    
                    # Calculate GPU utilization
                    gpu_active_time = start_event.elapsed_time(end_event)
                    self._metrics['gpu_usage'] = min(100.0, (gpu_active_time / 10.0) * 100)
                except Exception as e:
                    print(f"Error updating GPU metrics: {e}")

            time.sleep(0.5)

    def get_metrics(self):
        """Get current metrics"""
        return self._metrics.copy()

    def __del__(self):
        self._running = False

# Global instance
system_monitor = SystemMonitor()
