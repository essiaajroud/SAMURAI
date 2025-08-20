#!/usr/bin/env python3
"""
maintenance.py - Automatic maintenance script for the detection server.
Handles scheduled data cleanup, database optimization, health checks, and backups.
"""

import schedule
import time
import requests
import logging
import sqlite3
import os

# --- Configuration ---
SERVER_URL = "http://localhost:5000"
DB_PATH = "instance/detection_history.db"

# --- Logging Configuration (Compatible Windows) ---
# Ajout de 'encoding="utf-8"' pour les gestionnaires de fichiers pour une meilleure compatibilité
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("maintenance.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)

def check_server_connection():
    """Vérifie si le serveur principal est accessible avant de continuer."""
    try:
        response = requests.get(f"{SERVER_URL}/api/health", timeout=5)
        if response.status_code == 200:
            logging.info("[SUCCESS] Main server is running. Maintenance script can proceed.")
            return True
        else:
            logging.error(f"[ERROR] Main server responded with status {response.status_code}. Maintenance tasks might fail.")
            return False
    except requests.exceptions.ConnectionError:
        logging.error(f"[FATAL] Could not connect to the main server at {SERVER_URL}.")
        logging.error("   Please ensure the main 'app.py' server is running before starting this maintenance script.")
        return False
    except Exception as e:
        logging.error(f"[ERROR] An unexpected error occurred while checking server connection: {e}")
        return False

def cleanup_old_data():
    """Clean up old data via the API."""
    logging.info("[JOB START] Running Auto Cleanup...")
    try:
        response = requests.post(f"{SERVER_URL}/api/cleanup/auto", timeout=30)
        response.raise_for_status()
        result = response.json()
        logging.info(f"[SUCCESS] Auto Cleanup finished: {result.get('message')}")
    except requests.exceptions.RequestException as e:
        logging.error(f"[ERROR] API call failed during cleanup: {e}")
    except Exception as e:
        logging.error(f"[ERROR] An unexpected error occurred during cleanup: {e}")

def optimize_database():
    """Optimize the SQLite database (VACUUM, ANALYZE)."""
    logging.info("[JOB START] Running Database Optimization...")
    if not os.path.exists(DB_PATH):
        logging.warning(f"[WARNING] Database not found at {DB_PATH}. Skipping optimization.")
        return
        
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        logging.info("   Executing VACUUM...")
        cursor.execute("VACUUM")
        logging.info("   Executing ANALYZE...")
        cursor.execute("ANALYZE")
        conn.close()
        logging.info("[SUCCESS] Database optimized.")
    except Exception as e:
        logging.error(f"[ERROR] Database optimization failed: {e}")

def export_daily_report():
    """Déclenche l'exportation quotidienne des données via l'API."""
    logging.info("[JOB START] Running Daily Data Export...")
    try:
        response = requests.post(f"{SERVER_URL}/api/export/daily", timeout=60)
        response.raise_for_status()
        result = response.json()
        logging.info(f"[SUCCESS] Daily export finished: {result.get('message')}")
    except requests.exceptions.RequestException as e:
        logging.error(f"[ERROR] API call failed during daily export: {e}")
    except Exception as e:
        logging.error(f"[ERROR] An unexpected error occurred during daily export: {e}")

def main():
    """Main function for automatic maintenance."""
    logging.info("--- Starting Automatic Maintenance System ---")
    
    if not check_server_connection():
        logging.info("--- Halting maintenance script due to server connection issues. ---")
        return

    logging.info("--- Scheduling maintenance tasks ---")
    schedule.every(30).minutes.do(cleanup_old_data)
    schedule.every(2).hours.do(optimize_database)
    schedule.every().day.at("01:00").do(export_daily_report)
    logging.info("- Auto cleanup scheduled every 30 minutes.")
    logging.info("- Database optimization scheduled every 2 hours.")
    logging.info("- Daily export scheduled at 01:00 AM.")
    
    logging.info("--- Maintenance script is now running. Press CTRL+C to stop. ---")

    # Boucle principale
    while True:
        try:
            schedule.run_pending()
            time.sleep(1)
        except KeyboardInterrupt:
            logging.info("\n--- Stopping maintenance system. ---")
            break
        except Exception as e:
            logging.error(f"[FATAL] An unexpected error occurred in the main loop: {e}")
            time.sleep(30)

if __name__ == "__main__":
    main()