#!/usr/bin/env python3
"""
Script de maintenance automatique pour le serveur de détection.
Gère le nettoyage automatique des données et l'optimisation de la base de données.
"""

import schedule
import time
import requests
import logging
from datetime import datetime, timedelta
import sqlite3
import os

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('maintenance.log'),
        logging.StreamHandler()
    ]
)

# Configuration
SERVER_URL = "http://localhost:5000"
DB_PATH = "instance/detection_history.db"

def cleanup_old_data():
    """Nettoyer les données anciennes via l'API"""
    try:
        response = requests.post(f"{SERVER_URL}/api/cleanup/auto", timeout=30)
        if response.status_code == 200:
            result = response.json()
            logging.info(f"✅ Nettoyage automatique réussi: {result}")
        else:
            logging.error(f"❌ Erreur lors du nettoyage: {response.status_code}")
    except Exception as e:
        logging.error(f"❌ Erreur de connexion au serveur: {e}")

def optimize_database():
    """Optimiser la base de données SQLite"""
    try:
        if os.path.exists(DB_PATH):
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # VACUUM pour réorganiser la base de données
            cursor.execute("VACUUM")
            
            # ANALYZE pour mettre à jour les statistiques
            cursor.execute("ANALYZE")
            
            # Vérifier l'intégrité
            cursor.execute("PRAGMA integrity_check")
            integrity = cursor.fetchone()
            
            conn.close()
            
            if integrity[0] == 'ok':
                logging.info("✅ Base de données optimisée avec succès")
            else:
                logging.warning(f"⚠️ Problèmes d'intégrité détectés: {integrity}")
        else:
            logging.warning("⚠️ Base de données non trouvée")
            
    except Exception as e:
        logging.error(f"❌ Erreur lors de l'optimisation de la base: {e}")

def check_system_health():
    """Vérifier la santé du système"""
    try:
        # Vérifier la connexion au serveur
        response = requests.get(f"{SERVER_URL}/api/health", timeout=10)
        if response.status_code == 200:
            health = response.json()
            logging.info(f"✅ Système en bonne santé: {health}")
        else:
            logging.error(f"❌ Problème de santé du système: {response.status_code}")
            
        # Vérifier les statistiques
        response = requests.get(f"{SERVER_URL}/api/statistics/realtime", timeout=10)
        if response.status_code == 200:
            stats = response.json()
            logging.info(f"📊 Statistiques système: {stats['global']}")
        else:
            logging.error(f"❌ Impossible de récupérer les statistiques: {response.status_code}")
            
    except Exception as e:
        logging.error(f"❌ Erreur lors de la vérification de santé: {e}")

def backup_database():
    """Sauvegarder la base de données"""
    try:
        if os.path.exists(DB_PATH):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"backups/detection_history_{timestamp}.db"
            
            # Créer le dossier de sauvegarde s'il n'existe pas
            os.makedirs("backups", exist_ok=True)
            
            # Copier la base de données
            import shutil
            shutil.copy2(DB_PATH, backup_path)
            
            logging.info(f"✅ Sauvegarde créée: {backup_path}")
            
            # Nettoyer les anciennes sauvegardes (garder seulement les 7 derniers jours)
            cleanup_old_backups()
        else:
            logging.warning("⚠️ Base de données non trouvée pour la sauvegarde")
            
    except Exception as e:
        logging.error(f"❌ Erreur lors de la sauvegarde: {e}")

def cleanup_old_backups():
    """Nettoyer les anciennes sauvegardes"""
    try:
        if os.path.exists("backups"):
            cutoff_date = datetime.now() - timedelta(days=7)
            
            for filename in os.listdir("backups"):
                if filename.startswith("detection_history_") and filename.endswith(".db"):
                    file_path = os.path.join("backups", filename)
                    file_time = datetime.fromtimestamp(os.path.getctime(file_path))
                    
                    if file_time < cutoff_date:
                        os.remove(file_path)
                        logging.info(f"🗑️ Ancienne sauvegarde supprimée: {filename}")
                        
    except Exception as e:
        logging.error(f"❌ Erreur lors du nettoyage des sauvegardes: {e}")

def main():
    """Fonction principale de maintenance"""
    logging.info("🚀 Démarrage du système de maintenance automatique")
    
    # Planifier les tâches de maintenance
    schedule.every(30).minutes.do(cleanup_old_data)  # Nettoyage toutes les 30 minutes
    schedule.every(2).hours.do(optimize_database)    # Optimisation toutes les 2 heures
    schedule.every(15).minutes.do(check_system_health)  # Vérification de santé toutes les 15 minutes
    schedule.every().day.at("02:00").do(backup_database)  # Sauvegarde quotidienne à 2h du matin
    
    # Exécuter une première vérification
    check_system_health()
    
    # Boucle principale
    while True:
        try:
            schedule.run_pending()
            time.sleep(60)  # Vérifier toutes les minutes
        except KeyboardInterrupt:
            logging.info("🛑 Arrêt du système de maintenance")
            break
        except Exception as e:
            logging.error(f"❌ Erreur dans la boucle principale: {e}")
            time.sleep(60)

if __name__ == "__main__":
    main() 