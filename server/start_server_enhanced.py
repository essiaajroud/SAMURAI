#!/usr/bin/env python3
"""
start_server_enhanced.py - Enhanced startup script for the military detection server.
Starts all dynamic services and automatic maintenance.
"""

import os
import sys
import time
import threading
import subprocess
import signal
import logging
from datetime import datetime

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import get_config

# --- Load Configuration ---
config = get_config()

# Variable pour contrôler l'affichage des logs dans le terminal
DISABLE_CONSOLE_LOGS = True

# --- Logging Configuration ---
handlers = [logging.FileHandler(config.LOG_FILE)]
if not DISABLE_CONSOLE_LOGS:
    handlers.append(logging.StreamHandler())

logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=handlers
)

logger = logging.getLogger(__name__)

class ServerManager:
    """Server manager for all dynamic services."""
    def __init__(self):
        self.processes = {}
        self.running = False

    def start_maintenance_service(self):
        """Start the automatic maintenance service."""
        try:
            logger.info("🔧 Starting automatic maintenance service...")
            # Start the maintenance script in the background
            maintenance_script = os.path.join(os.path.dirname(__file__), 'maintenance.py')
            if os.path.exists(maintenance_script):
                process = subprocess.Popen([
                    sys.executable, maintenance_script
                ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                self.processes['maintenance'] = process
                logger.info("✅ Maintenance service started.")
            else:
                logger.warning("⚠️ Maintenance script not found.")
        except Exception as e:
            logger.error(f"❌ Error starting maintenance service: {e}")

    def start_flask_server(self):
        """Start the main Flask server."""
        try:
            logger.info("🚀 Starting main Flask server...")
            # Check if YOLO model is available
            if not os.path.exists(config.YOLO_MODEL_PATH):
                logger.warning(f"⚠️ YOLO model not found: {config.YOLO_MODEL_PATH}")
                logger.info("📥 Please place a YOLO model in the 'models/' folder.")
            # Check videos directory
            if not os.path.exists(config.YOLO_VIDEOS_DIR):
                os.makedirs(config.YOLO_VIDEOS_DIR, exist_ok=True)
                logger.info(f"📁 Videos directory created: {config.YOLO_VIDEOS_DIR}")
            # Start Flask server
            from server import app
            app.run(
                host=config.HOST,
                port=config.PORT,
                debug=config.DEBUG,
                use_reloader=False  # Avoid conflicts with the manager
            )
        except Exception as e:
            logger.error(f"❌ Error starting Flask server: {e}")

    def check_dependencies(self):
        """Check for required dependencies."""
        logger.info("🔍 Checking dependencies...")
        required_packages = [
            'flask', 'flask_cors', 'flask_sqlalchemy',
            'opencv-python', 'torch', 'torchvision',
            'numpy', 'pillow'
        ]
        missing_packages = []
        for package in required_packages:
            try:
                __import__(package.replace('-', '_'))
            except ImportError:
                missing_packages.append(package)
        if missing_packages:
            logger.error(f"❌ Missing packages: {', '.join(missing_packages)}")
            logger.info("💡 Install them with: pip install " + " ".join(missing_packages))
            return False
        logger.info("✅ All dependencies are installed.")
        return True

    def initialize_database(self):
        """Initialize the database."""
        try:
            logger.info("🗄️ Initializing the database...")
            # Create instance folder if it doesn't exist
            os.makedirs('instance', exist_ok=True)
            # Import and initialize the database
            from server import db
            with app.app_context():
                db.create_all()
            logger.info("✅ Database initialized.")
            return True
        except Exception as e:
            logger.error(f"❌ Error initializing database: {e}")
            return False

    def start(self):
        """Start all services."""
        logger.info("🎯 Starting military detection system")
        logger.info(f"📋 Configuration: {config.__name__}")
        logger.info(f"🌐 Server: http://{config.HOST}:{config.PORT}")
        # Check dependencies
        if not self.check_dependencies():
            logger.error("❌ Startup aborted - missing dependencies.")
            return False
        # Initialize database
        if not self.initialize_database():
            logger.error("❌ Startup aborted - database error.")
            return False
        self.running = True
        # Start maintenance service in a separate thread
        maintenance_thread = threading.Thread(target=self.start_maintenance_service)
        maintenance_thread.daemon = True
        maintenance_thread.start()
        # Wait a bit for maintenance to start
        time.sleep(2)
        # Start the main Flask server
        try:
            self.start_flask_server()
        except KeyboardInterrupt:
            logger.info("🛑 Shutdown requested by user.")
        except Exception as e:
            logger.error(f"❌ Fatal error: {e}")
        finally:
            self.stop()

    def stop(self):
        """Stop all services."""
        logger.info("🛑 Stopping all services...")
        self.running = False
        # Stop all processes
        for name, process in self.processes.items():
            try:
                logger.info(f"🛑 Stopping service: {name}")
                process.terminate()
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.warning(f"⚠️ Force stopping service: {name}")
                process.kill()
            except Exception as e:
                logger.error(f"❌ Error stopping {name}: {e}")
        logger.info("✅ All services stopped.")

def signal_handler(signum, frame):
    """Signal handler for graceful shutdown."""
    logger.info(f"📣 Signal received: {signum}")
    if hasattr(signal_handler, 'server_manager'):
        signal_handler.server_manager.stop()
    sys.exit(0)

def main():
    """Main function."""
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    # Create and start the server manager
    server_manager = ServerManager()
    signal_handler.server_manager = server_manager
    try:
        server_manager.start()
    except Exception as e:
        logger.error(f"❌ Fatal error during startup: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 