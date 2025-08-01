#!/usr/bin/env python3
"""
GPU-Optimized Server Startup Script for NVIDIA RTX 3060
Ensures optimal GPU configuration for AI models and streaming
"""

import os
import sys
import subprocess
import time
import torch
from pathlib import Path

def check_cuda_installation():
    """Check if CUDA is properly installed and accessible."""
    print("🔍 Checking CUDA installation...")
    
    try:
        # Check PyTorch CUDA availability
        if torch.cuda.is_available():
            print(f"✅ PyTorch CUDA available: {torch.version.cuda}")
            print(f"   GPU Device: {torch.cuda.get_device_name(0)}")
            print(f"   GPU Memory: {torch.cuda.get_device_properties(0).total_memory / (1024**3):.1f} GB")
            return True
        else:
            print("❌ PyTorch CUDA not available")
            return False
    except Exception as e:
        print(f"❌ CUDA check failed: {e}")
        return False

def check_nvidia_driver():
    """Check NVIDIA driver installation."""
    print("🔍 Checking NVIDIA driver...")
    
    try:
        result = subprocess.run(['nvidia-smi'], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("✅ NVIDIA driver found")
            return True
        else:
            print("❌ NVIDIA driver not found")
            return False
    except (subprocess.TimeoutExpired, FileNotFoundError):
        print("❌ NVIDIA driver not found or nvidia-smi not available")
        return False

def set_environment_variables():
    """Set optimal environment variables for GPU performance."""
    print("⚙️ Setting environment variables for GPU optimization...")
    
    # CUDA optimization settings
    os.environ['CUDA_LAUNCH_BLOCKING'] = '0'  # Non-blocking CUDA operations
    os.environ['CUDA_CACHE_DISABLE'] = '0'    # Enable CUDA cache
    os.environ['TORCH_CUDNN_V8_API_ENABLED'] = '1'  # Enable cuDNN v8 API
    
    # Memory optimization
    os.environ['PYTORCH_CUDA_ALLOC_CONF'] = 'max_split_size_mb:128'
    
    # Performance optimization
    os.environ['OMP_NUM_THREADS'] = str(os.cpu_count())
    os.environ['MKL_NUM_THREADS'] = str(os.cpu_count())
    
    print("✅ Environment variables set")

def optimize_gpu_settings():
    """Apply GPU-specific optimizations."""
    print("🚀 Applying GPU optimizations...")
    
    try:
        import torch
        
        if torch.cuda.is_available():
            # Set optimal CUDA settings for RTX 3060
            torch.backends.cudnn.benchmark = True
            torch.backends.cudnn.deterministic = False
            torch.backends.cudnn.enabled = True
            
            # Clear GPU cache
            torch.cuda.empty_cache()
            
            # Set memory fraction to avoid OOM (80% of available memory)
            torch.cuda.set_per_process_memory_fraction(0.8)
            
            print("✅ GPU optimizations applied")
            return True
        else:
            print("⚠️ CUDA not available, skipping GPU optimizations")
            return False
            
    except Exception as e:
        print(f"⚠️ GPU optimization failed: {e}")
        return False

def check_dependencies():
    """Check if all required dependencies are installed."""
    print("🔍 Checking dependencies...")
    
    required_packages = [
        'torch',
        'torchvision', 
        'ultralytics',
        'opencv-python',
        'flask',
        'numpy'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package} - MISSING")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n⚠️ Missing packages: {', '.join(missing_packages)}")
        print("Please install missing packages with: pip install -r requirements.txt")
        return False
    
    print("✅ All dependencies found")
    return True

def start_server():
    """Start the Flask server with GPU optimizations."""
    print("\n🚀 Starting GPU-optimized server...")
    
    # Set Flask environment
    os.environ['FLASK_ENV'] = 'production'
    os.environ['FLASK_DEBUG'] = '0'
    
    # Import and start the app
    try:
        from app import app
        
        print("✅ Server starting on http://localhost:5000")
        print("   GPU acceleration: ENABLED")
        print("   Press Ctrl+C to stop")
        
        app.run(
            host='0.0.0.0',
            port=5000,
            debug=False,
            threaded=True,
            use_reloader=False
        )
        
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as e:
        print(f"❌ Server startup failed: {e}")
        sys.exit(1)

def main():
    """Main startup function."""
    print("=" * 60)
    print("🎯 GPU-Optimized SAMURAI AI Server Startup")
    print("   Optimized for NVIDIA RTX 3060 Laptop GPU")
    print("=" * 60)
    
    # Check if we're in the right directory
    if not Path("app.py").exists():
        print("❌ app.py not found. Please run this script from the server directory.")
        sys.exit(1)
    
    # Run checks
    print("\n📋 Running startup checks...")
    
    if not check_dependencies():
        print("❌ Dependency check failed")
        sys.exit(1)
    
    if not check_nvidia_driver():
        print("⚠️ NVIDIA driver not found - GPU acceleration may not work")
    
    if not check_cuda_installation():
        print("⚠️ CUDA not available - will use CPU mode")
    
    # Apply optimizations
    print("\n⚙️ Applying optimizations...")
    set_environment_variables()
    optimize_gpu_settings()
    
    # Start server
    print("\n" + "=" * 60)
    start_server()

if __name__ == "__main__":
    main() 