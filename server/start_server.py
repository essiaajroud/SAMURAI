#!/usr/bin/env python3
"""
start_server.py - Startup script for the Flask detection history server.
Checks Python version, creates virtual environment, installs dependencies, and starts the server.
"""

import os
import sys
import subprocess
from pathlib import Path

# --- Check Python Version ---
def check_python_version():
    """Check that Python version is >= 3.7."""
    if sys.version_info < (3, 7):
        print("❌ Python 3.7 or higher is required.")
        sys.exit(1)
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} detected.")

# --- Create Virtual Environment ---
def create_virtual_env():
    """Create a virtual environment if it does not exist."""
    venv_path = Path("venv")
    if not venv_path.exists():
        print("📦 Creating virtual environment...")
        subprocess.run([sys.executable, "-m", "venv", "venv"], check=True)
        print("✅ Virtual environment created.")
    else:
        print("✅ Virtual environment already exists.")

# --- Install Dependencies ---
def install_dependencies():
    """Install dependencies from requirements.txt."""
    print("📦 Installing dependencies...")
    # Determine pip path based on OS
    if os.name == 'nt':  # Windows
        pip_path = "venv/Scripts/pip"
    else:  # Linux/Mac
        pip_path = "venv/bin/pip"
    try:
        subprocess.run([pip_path, "install", "-r", "requirements.txt"], check=True)
        print("✅ Dependencies installed.")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error during installation: {e}")
        sys.exit(1)

# --- Start Flask Server ---
def start_server():
    """Start the Flask server."""
    print("🚀 Starting Flask server...")
    print("📍 Server available at: http://localhost:5000")
    print("📊 API available at: http://localhost:5000/api")
    print("🔍 Health check: http://localhost:5000/api/health")
    print("\n⏹️  Press Ctrl+C to stop the server\n")
    # Determine python path based on OS
    if os.name == 'nt':  # Windows
        python_path = "venv/Scripts/python"
    else:  # Linux/Mac
        python_path = "venv/bin/python"
    try:
        subprocess.run([python_path, "app.py"])
    except KeyboardInterrupt:
        print("\n🛑 Server stopped.")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error during server startup: {e}")
        sys.exit(1)

# --- Main Entry Point ---
def main():
    """Main function."""
    print("🎯 Detection History Server")
    print("=" * 50)
    # Check that we are in the correct directory
    if not Path("app.py").exists():
        print("❌ app.py file not found. Run this script from the server/ directory.")
        sys.exit(1)
    check_python_version()
    create_virtual_env()
    install_dependencies()
    start_server()

if __name__ == "__main__":
    main() 