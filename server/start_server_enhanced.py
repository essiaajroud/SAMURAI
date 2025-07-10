#!/usr/bin/env python3
"""
Script de démarrage amélioré pour le serveur de détection militaire.
Démarre tous les services dynamiques et la maintenance automatique.
"""

import os
import sys
import time
import threading
import subprocess
import signal
import logging
from datetime import datetime

# Ajouter le répertoire courant au path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import get_config

# Configuration
config = get_config()

# Configuration du logging
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(config.LOG_FILE),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class ServerManager:
    """Gestionnaire du serveur avec tous les services dynamiques"""
    
    def __init__(self):
        self.processes = {}
        self.running = False
        
    def start_maintenance_service(self):
        """Démarrer le service de maintenance automatique"""
        try:
            logger.info("🔧 Démarrage du service de maintenance automatique...")
            
            # Démarrer le script de maintenance en arrière-plan
            maintenance_script = os.path.join(os.path.dirname(__file__), 'maintenance.py')
            if os.path.exists(maintenance_script):
                process = subprocess.Popen([
                    sys.executable, maintenance_script
                ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                
                self.processes['maintenance'] = process
                logger.info("✅ Service de maintenance démarré")
            else:
                logger.warning("⚠️ Script de maintenance non trouvé")
                
        except Exception as e:
            logger.error(f"❌ Erreur lors du démarrage du service de maintenance: {e}")
    
    def start_flask_server(self):
        """Démarrer le serveur Flask principal"""
        try:
            logger.info("🚀 Démarrage du serveur Flask principal...")
            
            # Vérifier que le modèle YOLO est disponible
            if not os.path.exists(config.YOLO_MODEL_PATH):
                logger.warning(f"⚠️ Modèle YOLO non trouvé: {config.YOLO_MODEL_PATH}")
                logger.info("📥 Veuillez placer un modèle YOLO dans le dossier 'models/'")
            
            # Vérifier le dossier des vidéos
            if not os.path.exists(config.YOLO_VIDEOS_DIR):
                os.makedirs(config.YOLO_VIDEOS_DIR, exist_ok=True)
                logger.info(f"📁 Dossier vidéos créé: {config.YOLO_VIDEOS_DIR}")
            
            # Démarrer le serveur Flask
            from app import app
            app.run(
                host=config.HOST,
                port=config.PORT,
                debug=config.DEBUG,
                use_reloader=False  # Éviter les conflits avec le gestionnaire
            )
            
        except Exception as e:
            logger.error(f"❌ Erreur lors du démarrage du serveur Flask: {e}")
    
    def check_dependencies(self):
        """Vérifier les dépendances requises"""
        logger.info("🔍 Vérification des dépendances...")
        
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
            logger.error(f"❌ Packages manquants: {', '.join(missing_packages)}")
            logger.info("💡 Installez-les avec: pip install " + " ".join(missing_packages))
            return False
        
        logger.info("✅ Toutes les dépendances sont installées")
        return True
    
    def initialize_database(self):
        """Initialiser la base de données"""
        try:
            logger.info("🗄️ Initialisation de la base de données...")
            
            # Créer le dossier instance s'il n'existe pas
            os.makedirs('instance', exist_ok=True)
            
            # Importer et initialiser la base de données
            from app import db
            with app.app_context():
                db.create_all()
            
            logger.info("✅ Base de données initialisée")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erreur lors de l'initialisation de la base: {e}")
            return False
    
    def start(self):
        """Démarrer tous les services"""
        logger.info("🎯 Démarrage du système de détection militaire")
        logger.info(f"📋 Configuration: {config.__name__}")
        logger.info(f"🌐 Serveur: http://{config.HOST}:{config.PORT}")
        
        # Vérifier les dépendances
        if not self.check_dependencies():
            logger.error("❌ Arrêt du démarrage - dépendances manquantes")
            return False
        
        # Initialiser la base de données
        if not self.initialize_database():
            logger.error("❌ Arrêt du démarrage - erreur de base de données")
            return False
        
        self.running = True
        
        # Démarrer le service de maintenance dans un thread séparé
        maintenance_thread = threading.Thread(target=self.start_maintenance_service)
        maintenance_thread.daemon = True
        maintenance_thread.start()
        
        # Attendre un peu que la maintenance démarre
        time.sleep(2)
        
        # Démarrer le serveur Flask principal
        try:
            self.start_flask_server()
        except KeyboardInterrupt:
            logger.info("🛑 Arrêt demandé par l'utilisateur")
        except Exception as e:
            logger.error(f"❌ Erreur fatale: {e}")
        finally:
            self.stop()
    
    def stop(self):
        """Arrêter tous les services"""
        logger.info("🛑 Arrêt de tous les services...")
        self.running = False
        
        # Arrêter tous les processus
        for name, process in self.processes.items():
            try:
                logger.info(f"🛑 Arrêt du service: {name}")
                process.terminate()
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.warning(f"⚠️ Force arrêt du service: {name}")
                process.kill()
            except Exception as e:
                logger.error(f"❌ Erreur lors de l'arrêt de {name}: {e}")
        
        logger.info("✅ Tous les services arrêtés")

def signal_handler(signum, frame):
    """Gestionnaire de signaux pour un arrêt propre"""
    logger.info(f"📡 Signal reçu: {signum}")
    if hasattr(signal_handler, 'server_manager'):
        signal_handler.server_manager.stop()
    sys.exit(0)

def main():
    """Fonction principale"""
    # Enregistrer les gestionnaires de signaux
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Créer et démarrer le gestionnaire de serveur
    server_manager = ServerManager()
    signal_handler.server_manager = server_manager
    
    try:
        server_manager.start()
    except Exception as e:
        logger.error(f"❌ Erreur fatale lors du démarrage: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 