#!/usr/bin/env python3
"""
Script pour démarrer automatiquement le streaming avec la vidéo de test
"""

import requests
import json
import time
import sys
import os

def start_streaming_auto():
    """Démarre automatiquement le streaming avec la vidéo de test"""
    
    # URL du serveur
    base_url = "http://localhost:5000"
    
    # Vérifier que le serveur est en cours d'exécution
    try:
        health_response = requests.get(f"{base_url}/api/health", timeout=5)
        if health_response.status_code != 200:
            print("❌ Serveur non accessible")
            return False
        print("✅ Serveur accessible")
    except requests.exceptions.RequestException as e:
        print(f"❌ Impossible de se connecter au serveur: {e}")
        return False
    
    # Vérifier le statut du streaming
    try:
        status_response = requests.get(f"{base_url}/api/yolo/stream/status")
        if status_response.status_code == 200:
            status_data = status_response.json()
            if status_data.get('is_running', False):
                print("✅ Streaming déjà en cours")
                return True
    except Exception as e:
        print(f"⚠️ Erreur lors de la vérification du statut: {e}")
    
    # Vérifier les vidéos disponibles
    try:
        videos_response = requests.get(f"{base_url}/api/yolo/videos")
        if videos_response.status_code == 200:
            videos_data = videos_response.json()
            available_videos = videos_data.get('videos', [])
            print(f"📹 Vidéos disponibles: {available_videos}")
            
            if not available_videos:
                print("❌ Aucune vidéo disponible")
                return False
            
            # Utiliser la première vidéo disponible
            video_path = available_videos[0]
            print(f"🎬 Démarrage du streaming avec: {video_path}")
            
        else:
            print("❌ Impossible de récupérer la liste des vidéos")
            return False
    except Exception as e:
        print(f"❌ Erreur lors de la récupération des vidéos: {e}")
        return False
    
    # Démarrer le streaming
    try:
        start_data = {
            "video_path": video_path
        }
        
        start_response = requests.post(
            f"{base_url}/api/yolo/stream/start",
            json=start_data,
            timeout=10
        )
        
        if start_response.status_code == 200:
            result = start_response.json()
            print(f"✅ Streaming démarré: {result.get('message', '')}")
            print(f"   Source: {result.get('stream_source', '')}")
            print(f"   Statut: {'En cours' if result.get('is_running', False) else 'Arrêté'}")
            return True
        else:
            error_data = start_response.json()
            print(f"❌ Erreur lors du démarrage: {error_data.get('error', 'Erreur inconnue')}")
            return False
            
    except requests.exceptions.Timeout:
        print("❌ Timeout lors du démarrage du streaming")
        return False
    except Exception as e:
        print(f"❌ Erreur lors du démarrage: {e}")
        return False

def main():
    """Fonction principale"""
    print("🚀 Démarrage automatique du streaming...")
    print("=" * 50)
    
    # Attendre un peu que le serveur soit prêt
    print("⏳ Attente du serveur...")
    time.sleep(2)
    
    # Démarrer le streaming
    success = start_streaming_auto()
    
    if success:
        print("\n✅ Streaming démarré avec succès!")
        print("🌐 Accédez à l'interface web: http://localhost:3000")
        print("📹 Flux vidéo: http://localhost:5000/video_feed")
    else:
        print("\n❌ Échec du démarrage du streaming")
        print("🔧 Vérifiez que:")
        print("   - Le serveur Flask est en cours d'exécution")
        print("   - YOLO est correctement configuré")
        print("   - Des vidéos sont disponibles dans le dossier videos/")
        sys.exit(1)

if __name__ == "__main__":
    main() 