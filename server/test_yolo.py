#!/usr/bin/env python3
"""
Script de test pour l'intégration YOLO
"""

import os
import sys
import requests
import json
import time

def test_server_health():
    """Test de la santé du serveur"""
    try:
        response = requests.get('http://localhost:5000/api/health')
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Serveur en ligne: {data}")
            return data.get('yolo_available', False)
        else:
            print(f"❌ Serveur non accessible: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Erreur de connexion: {e}")
        return False

def test_yolo_model():
    """Test du modèle YOLO"""
    try:
        response = requests.get('http://localhost:5000/api/yolo/model')
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Modèle YOLO: {data}")
            return True
        else:
            print(f"❌ Erreur modèle YOLO: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Erreur test modèle: {e}")
        return False

def test_videos_list():
    """Test de la liste des vidéos"""
    try:
        response = requests.get('http://localhost:5000/api/yolo/videos')
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Vidéos disponibles: {data}")
            return data.get('videos', [])
        else:
            print(f"❌ Erreur liste vidéos: {response.status_code}")
            return []
    except Exception as e:
        print(f"❌ Erreur test vidéos: {e}")
        return []

def test_streaming_status():
    """Test du statut du streaming"""
    try:
        response = requests.get('http://localhost:5000/api/yolo/stream/status')
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Statut streaming: {data}")
            return data
        else:
            print(f"❌ Erreur statut streaming: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Erreur test streaming: {e}")
        return None

def main():
    """Fonction principale de test"""
    print("🧪 Test d'intégration YOLO")
    print("=" * 50)
    
    # Test 1: Santé du serveur
    print("\n1. Test de la santé du serveur...")
    yolo_available = test_server_health()
    
    if not yolo_available:
        print("⚠️ YOLO n'est pas disponible sur le serveur")
        return
    
    # Test 2: Modèle YOLO
    print("\n2. Test du modèle YOLO...")
    test_yolo_model()
    
    # Test 3: Liste des vidéos
    print("\n3. Test de la liste des vidéos...")
    videos = test_videos_list()
    
    if videos:
        print(f"📹 {len(videos)} vidéo(s) trouvée(s):")
        for video in videos:
            print(f"   - {video}")
    else:
        print("📹 Aucune vidéo trouvée")
    
    # Test 4: Statut du streaming
    print("\n4. Test du statut du streaming...")
    test_streaming_status()
    
    print("\n✅ Tests terminés")

if __name__ == "__main__":
    main() 