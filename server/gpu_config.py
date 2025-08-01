"""
GPU Configuration for NVIDIA RTX 3060 Laptop GPU
Optimized settings for AI models and streaming performance
"""

import torch
import psutil
import os
from typing import Optional, Dict, Any

class GPUConfig:
    def __init__(self):
        self.gpu_available = False
        self.gpu_name = None
        self.gpu_memory = None
        self.device = None
        self.optimization_level = "balanced"  # balanced, performance, quality
        self._initialize_gpu()
    
    def _initialize_gpu(self):
        """Initialize GPU configuration for RTX 3060"""
        try:
            # Check if CUDA is available
            if torch.cuda.is_available():
                self.gpu_available = True
                self.device = torch.device("cuda:0")
                
                # Get GPU information
                self.gpu_name = torch.cuda.get_device_name(0)
                self.gpu_memory = torch.cuda.get_device_properties(0).total_memory / (1024**3)  # GB
                
                # Set optimal CUDA settings for RTX 3060
                torch.backends.cudnn.benchmark = True
                torch.backends.cudnn.deterministic = False
                
                # Optimize memory allocation
                torch.cuda.empty_cache()
                
                # Set memory fraction to avoid OOM (80% of available memory)
                torch.cuda.set_per_process_memory_fraction(0.8)
                
                print(f"✅ GPU initialized: {self.gpu_name}")
                print(f"   Memory: {self.gpu_memory:.1f} GB")
                print(f"   CUDA Version: {torch.version.cuda}")
                
            else:
                self.device = torch.device("cpu")
                print("⚠️ CUDA not available, using CPU")
                
        except Exception as e:
            print(f"❌ GPU initialization error: {e}")
            self.device = torch.device("cpu")
    
    def get_device(self) -> torch.device:
        """Get the optimal device for tensor operations"""
        return self.device
    
    def get_optimization_settings(self) -> Dict[str, Any]:
        """Get optimization settings based on GPU capabilities"""
        if not self.gpu_available:
            return {
                "device": "cpu",
                "batch_size": 1,
                "precision": "fp32",
                "optimization": "none"
            }
        
        # RTX 3060 specific optimizations
        settings = {
            "device": "cuda",
            "batch_size": 4,  # Optimal for RTX 3060 6GB VRAM
            "precision": "fp16",  # Use half precision for better performance
            "optimization": "tensorrt",  # Enable TensorRT optimization
            "memory_pool": True,
            "cudnn_benchmark": True
        }
        
        # Adjust based on available memory
        if self.gpu_memory and self.gpu_memory < 8:
            settings["batch_size"] = 2
            settings["precision"] = "fp32"  # Use full precision if limited memory
        
        return settings
    
    def optimize_model(self, model):
        """Apply optimizations to a PyTorch model"""
        if not self.gpu_available:
            return model
        
        try:
            # Move model to GPU
            model = model.to(self.device)
            
            # Enable half precision if supported
            if hasattr(model, 'half') and self.gpu_memory and self.gpu_memory >= 8:
                model = model.half()
            
            # Enable evaluation mode for inference
            model.eval()
            
            print(f"✅ Model optimized for GPU: {self.gpu_name}")
            return model
            
        except Exception as e:
            print(f"⚠️ Model optimization failed: {e}")
            return model
    
    def get_memory_info(self) -> Dict[str, float]:
        """Get current GPU memory usage"""
        if not self.gpu_available:
            return {"gpu_memory_used": 0, "gpu_memory_total": 0, "gpu_memory_free": 0}
        
        try:
            memory_allocated = torch.cuda.memory_allocated(0) / (1024**3)  # GB
            memory_reserved = torch.cuda.memory_reserved(0) / (1024**3)  # GB
            memory_free = self.gpu_memory - memory_allocated
            
            return {
                "gpu_memory_used": memory_allocated,
                "gpu_memory_reserved": memory_reserved,
                "gpu_memory_total": self.gpu_memory,
                "gpu_memory_free": memory_free
            }
        except Exception as e:
            print(f"⚠️ Error getting GPU memory info: {e}")
            return {"gpu_memory_used": 0, "gpu_memory_total": 0, "gpu_memory_free": 0}
    
    def clear_cache(self):
        """Clear GPU memory cache"""
        if self.gpu_available:
            torch.cuda.empty_cache()
    
    def set_optimization_level(self, level: str):
        """Set optimization level: balanced, performance, quality"""
        self.optimization_level = level
        
        if level == "performance":
            # Maximum performance settings
            torch.backends.cudnn.benchmark = True
            torch.backends.cudnn.deterministic = False
            os.environ['CUDA_LAUNCH_BLOCKING'] = '0'
        elif level == "quality":
            # Maximum quality settings
            torch.backends.cudnn.benchmark = False
            torch.backends.cudnn.deterministic = True
            os.environ['CUDA_LAUNCH_BLOCKING'] = '1'
        else:  # balanced
            # Balanced settings
            torch.backends.cudnn.benchmark = True
            torch.backends.cudnn.deterministic = False
            os.environ['CUDA_LAUNCH_BLOCKING'] = '0'

# Global GPU configuration instance
gpu_config = GPUConfig() 