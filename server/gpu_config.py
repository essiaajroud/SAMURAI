import torch
import os
from typing import Optional, Dict, Any

class GPUConfig:
    def __init__(self):
        self.gpu_available = torch.cuda.is_available()
        self.gpu_name = None
        self.gpu_memory = None
        self.device = None
        self.optimization_level = 'balanced'
        self.initialize()

    def initialize(self):
        """Initialize GPU configuration"""
        if self.gpu_available:
            try:
                self.device = torch.device('cuda:0')
                self.gpu_name = torch.cuda.get_device_name(0)
                props = torch.cuda.get_device_properties(0)
                self.gpu_memory = props.total_memory / (1024**3)  # Convert to GB
                
                # Configure CUDA settings
                torch.backends.cudnn.benchmark = True
                torch.backends.cudnn.deterministic = False
                torch.cuda.empty_cache()
                
                print(f"✅ GPU initialized: {self.gpu_name}")
                print(f"   Memory: {self.gpu_memory:.1f} GB")
            except Exception as e:
                print(f"⚠️ GPU initialization error: {e}")
                self.gpu_available = False
                self.device = torch.device('cpu')
        else:
            self.device = torch.device('cpu')
            print("⚠️ No GPU available, using CPU")

    def get_device(self):
        """Get current device (GPU or CPU)"""
        return self.device

    def get_optimization_settings(self):
        """Get current optimization settings"""
        return {
            'device': 'cuda' if self.gpu_available else 'cpu',
            'precision': 'fp16' if self.gpu_available else 'fp32',
            'cudnn_benchmark': True if self.gpu_available else False
        }

    def clear_cache(self):
        """Clear GPU memory cache"""
        if self.gpu_available:
            torch.cuda.empty_cache()

# Create global instance
gpu_config = GPUConfig()

# Ensure the instance is available for import
__all__ = ['gpu_config']
