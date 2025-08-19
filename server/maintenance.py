#!/usr/bin/env python3
"""
maintenance.py - Automatic maintenance script for the detection server.
Handles scheduled data cleanup, database optimization, health checks, and backups.
"""

import schedule
import time
import requests
import logging
from datetime import datetime, timedelta
import sqlite3
import os

# --- Logging Configuration ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('maintenance.log'),
        logging.StreamHandler()
    ]
)

# --- Main Configuration ---
SERVER_URL = "http://localhost:5000"
DB_PATH = "instance/detection_history.db"

# --- Cleanup Old Data via API ---
def cleanup_old_data():
    """Clean up old data via the API."""
    try:
        response = requests.post(f"{SERVER_URL}/api/cleanup/auto", timeout=30)
        if response.status_code == 200:
            result = response.json()
            logging.info(f"✅ Automatic cleanup successful: {result}")
        else:
            logging.error(f"❌ Error during cleanup: {response.status_code}")
    except Exception as e:
        logging.error(f"❌ Connection error to server: {e}")

# --- Optimize SQLite Database ---
def optimize_database():
    """Optimize the SQLite database (VACUUM, ANALYZE, integrity check)."""
    try:
        if os.path.exists(DB_PATH):
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            # VACUUM to reorganize the database
            cursor.execute("VACUUM")
            # ANALYZE to update statistics
            cursor.execute("ANALYZE")
            # Check integrity
            cursor.execute("PRAGMA integrity_check")
            integrity = cursor.fetchone()
            conn.close()
            if integrity[0] == 'ok':
                logging.info("✅ Database optimized successfully")
            else:
                logging.warning(f"⚠️ Integrity issues detected: {integrity}")
        else:
            logging.warning("⚠️ Database not found")
    except Exception as e:
        logging.error(f"❌ Error during database optimization: {e}")

# --- System Health Check ---
def check_system_health():
    """Check the health of the system via API endpoints."""
    try:
        # Check server connection
        response = requests.get(f"{SERVER_URL}/api/health", timeout=10)
        if response.status_code == 200:
            health = response.json()
            logging.info(f"✅ System healthy: {health}")
        else:
            logging.error(f"❌ System health problem: {response.status_code}")
        # Check statistics
        response = requests.get(f"{SERVER_URL}/api/statistics/realtime", timeout=10)
        if response.status_code == 200:
            stats = response.json()
            logging.info(f"📊 System statistics: {stats['global']}")
        else:
            logging.error(f"❌ Unable to retrieve statistics: {response.status_code}")
    except Exception as e:
        logging.error(f"❌ Error during health check: {e}")

# --- Backup the Database ---
def backup_database():
    """Backup the database to the backups directory."""
    try:
        if os.path.exists(DB_PATH):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"backups/detection_history_{timestamp}.db"
            # Create backup directory if it doesn't exist
            os.makedirs("backups", exist_ok=True)
            # Copy the database
            import shutil
            shutil.copy2(DB_PATH, backup_path)
            logging.info(f"✅ Backup created: {backup_path}")
            # Clean up old backups (keep only last 7 days)
            cleanup_old_backups()
        else:
            logging.warning("⚠️ Database not found for backup")
    except Exception as e:
        logging.error(f"❌ Error during backup: {e}")

# --- Cleanup Old Backups ---
def cleanup_old_backups():
    """Remove old backups older than 7 days."""
    try:
        if os.path.exists("backups"):
            cutoff_date = datetime.now() - timedelta(days=7)
            for filename in os.listdir("backups"):
                if filename.startswith("detection_history_") and filename.endswith(".db"):
                    file_path = os.path.join("backups", filename)
                    file_time = datetime.fromtimestamp(os.path.getctime(file_path))
                    if file_time < cutoff_date:
                        os.remove(file_path)
                        logging.info(f"🗑️ Old backup deleted: {filename}")
    except Exception as e:
        logging.error(f"❌ Error during backup cleanup: {e}")

def export_daily_report():
    """Déclenche l'exportation quotidienne des données via l'API."""
    try:
        logging.info("🚀 Triggering daily data export...")
        response = requests.post(f"{SERVER_URL}/api/export/daily", timeout=60)
        if response.status_code == 200:
            result = response.json()
            logging.info(f"✅ Daily export successful: {result.get('message')}")
        else:
            logging.error(f"❌ Error during daily export: {response.status_code} - {response.text}")
    except Exception as e:
        logging.error(f"❌ Connection error during daily export: {e}")


# --- Main Maintenance Loop ---
def main():
    """Main function for automatic maintenance."""
    logging.info("🚀 Starting automatic maintenance system")
    # Schedule maintenance tasks
    schedule.every(30).minutes.do(cleanup_old_data)  # Cleanup every 30 minutes
    schedule.every(2).hours.do(optimize_database)    # Optimize every 2 hours
    schedule.every(15).minutes.do(check_system_health)  # Health check every 15 minutes
    #schedule.every().day.at("02:00").do(backup_database)  # Daily backup at 2am
    schedule.every().day.at("01:00").do(export_daily_report)

    # Initial health check
    check_system_health()
    # Main loop
    while True:
        try:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
        except KeyboardInterrupt:
            logging.info("🛑 Stopping maintenance system")
            break
        except Exception as e:
            logging.error(f"❌ Error in main loop: {e}")
            time.sleep(60)

if __name__ == "__main__":
    main() 