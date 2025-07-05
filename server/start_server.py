#!/usr/bin/env python3
"""
Script de démarrage du serveur Flask pour l'historisation des détections
"""

import os
import sys
import subprocess
from pathlib import Path

def check_python_version():
    """Vérifier la version de Python"""
    if sys.version_info < (3, 7):
        print("❌ Python 3.7 ou supérieur est requis")
        sys.exit(1)
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} détecté")

def create_virtual_env():
    """Créer un environnement virtuel s'il n'existe pas"""
    venv_path = Path("venv")
    if not venv_path.exists():
        print("📦 Création de l'environnement virtuel...")
        subprocess.run([sys.executable, "-m", "venv", "venv"], check=True)
        print("✅ Environnement virtuel créé")
    else:
        print("✅ Environnement virtuel existant")

def install_dependencies():
    """Installer les dépendances"""
    print("📦 Installation des dépendances...")
    
    # Déterminer le chemin de pip selon l'OS
    if os.name == 'nt':  # Windows
        pip_path = "venv/Scripts/pip"
    else:  # Linux/Mac
        pip_path = "venv/bin/pip"
    
    try:
        subprocess.run([pip_path, "install", "-r", "requirements.txt"], check=True)
        print("✅ Dépendances installées")
    except subprocess.CalledProcessError as e:
        print(f"❌ Erreur lors de l'installation: {e}")
        sys.exit(1)

def start_server():
    """Démarrer le serveur Flask"""
    print("🚀 Démarrage du serveur Flask...")
    print("📍 Serveur accessible sur: http://localhost:5000")
    print("📊 API disponible sur: http://localhost:5000/api")
    print("🔍 Health check: http://localhost:5000/api/health")
    print("\n⏹️  Appuyez sur Ctrl+C pour arrêter le serveur\n")
    
    # Déterminer le chemin de python selon l'OS
    if os.name == 'nt':  # Windows
        python_path = "venv/Scripts/python"
    else:  # Linux/Mac
        python_path = "venv/bin/python"
    
    try:
        subprocess.run([python_path, "app.py"])
    except KeyboardInterrupt:
        print("\n🛑 Serveur arrêté")
    except subprocess.CalledProcessError as e:
        print(f"❌ Erreur lors du démarrage: {e}")
        sys.exit(1)

def main():
    """Fonction principale"""
    print("🎯 Serveur d'Historisation des Détections")
    print("=" * 50)
    
    # Vérifier que nous sommes dans le bon répertoire
    if not Path("app.py").exists():
        print("❌ Fichier app.py non trouvé. Exécutez ce script depuis le dossier server/")
        sys.exit(1)
    
    check_python_version()
    create_virtual_env()
    install_dependencies()
    start_server()

if __name__ == "__main__":
    main() 