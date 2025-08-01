@echo off
chcp 65001 >nul
echo ============================================================
echo 🎯 GPU-Optimized SAMURAI AI Server Startup
echo    Optimized for NVIDIA RTX 3060 Laptop GPU
echo ============================================================
echo.

REM Check if virtual environment exists
if not exist "venv\Scripts\activate.bat" (
    echo ❌ Virtual environment not found. Creating one...
    python -m venv venv
    if errorlevel 1 (
        echo ❌ Failed to create virtual environment
        pause
        exit /b 1
    )
)

REM Activate virtual environment
echo 🔧 Activating virtual environment...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo ❌ Failed to activate virtual environment
    pause
    exit /b 1
)

REM Install/upgrade dependencies
echo 📦 Installing/upgrading dependencies...
pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 (
    echo ❌ Failed to install dependencies
    pause
    exit /b 1
)

REM Check GPU availability
echo 🔍 Checking GPU availability...
python -c "import torch; print('✅ CUDA available:', torch.cuda.is_available()); print('GPU:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'None')"
if errorlevel 1 (
    echo ⚠️ GPU check failed, continuing anyway...
)

REM Set environment variables for GPU optimization
echo ⚙️ Setting GPU optimization environment variables...
set CUDA_LAUNCH_BLOCKING=0
set CUDA_CACHE_DISABLE=0
set TORCH_CUDNN_V8_API_ENABLED=1
set PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:128
set OMP_NUM_THREADS=%NUMBER_OF_PROCESSORS%
set MKL_NUM_THREADS=%NUMBER_OF_PROCESSORS%
set FLASK_ENV=production
set FLASK_DEBUG=0

echo.
echo 🚀 Starting GPU-optimized server...
echo    Server will be available at: http://localhost:5000
echo    GPU acceleration: ENABLED
echo    Press Ctrl+C to stop
echo.

REM Start the server
python start_gpu_server.py

echo.
echo 🛑 Server stopped
pause 