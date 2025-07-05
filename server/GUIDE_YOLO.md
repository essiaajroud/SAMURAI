# 🎯 Guide d'utilisation - Intégration YOLO

## 📁 Structure des dossiers

```
server/
├── models/          # Vos modèles YOLO (.pt)
│   ├── best.pt     # Modèle entraîné
│   └── last.pt     # Dernier checkpoint
├── videos/          # Vos vidéos
│   ├── test.mp4    # Vidéo de test
│   └── ...
├── yolo_detector.py # Module de détection YOLO
├── app.py          # Serveur Flask avec API YOLO
└── test_yolo.py    # Script de test
```

## 🚀 Installation des dépendances

Le serveur va automatiquement installer les dépendances YOLO au démarrage :

```bash
cd server
python start_server.py
```

## 📋 API Endpoints YOLO

### 1. **Informations du modèle**
```bash
GET /api/yolo/model
```

### 2. **Charger un modèle**
```bash
POST /api/yolo/model
{
  "model_path": "models/best.pt",
  "confidence": 0.5
}
```

### 3. **Liste des vidéos**
```bash
GET /api/yolo/videos
```

### 4. **Traiter une vidéo**
```bash
POST /api/yolo/process
{
  "video_path": "videos/test.mp4",
  "save_results": true
}
```

### 5. **Démarrer le streaming**
```bash
POST /api/yolo/stream/start
{
  "video_path": "videos/test.mp4"
}
```

### 6. **Arrêter le streaming**
```bash
POST /api/yolo/stream/stop
```

### 7. **Statut du streaming**
```bash
GET /api/yolo/stream/status
```

### 8. **Upload vidéo**
```bash
POST /api/yolo/upload-video
# Avec fichier multipart
```

### 9. **Upload modèle**
```bash
POST /api/yolo/upload-model
# Avec fichier multipart
```

## 🎬 Utilisation étape par étape

### Étape 1: Placer vos fichiers
1. **Modèle YOLO** : Placez votre fichier `.pt` dans `server/models/`
2. **Vidéo** : Placez votre vidéo dans `server/videos/`

### Étape 2: Démarrer le serveur
```bash
cd server
python start_server.py
```

### Étape 3: Tester l'intégration
```bash
python test_yolo.py
```

### Étape 4: Utiliser via l'interface web
1. Ouvrez votre navigateur sur `http://localhost:3000`
2. Allez dans l'onglet "Camera View"
3. Sélectionnez votre vidéo
4. Cliquez sur "Start Detection"

## 🔧 Configuration

### Modifier le seuil de confiance
```python
# Dans yolo_detector.py
detector = YOLODetector(confidence_threshold=0.7)
```

### Changer le modèle par défaut
```python
# Dans yolo_detector.py
detector = YOLODetector(model_path="models/votre_modele.pt")
```

## 📊 Détections automatiques

Les détections YOLO sont automatiquement :
- ✅ Sauvegardées dans la base de données
- ✅ Affichées en temps réel dans l'interface
- ✅ Incluses dans les statistiques
- ✅ Exportées avec les données

## 🐛 Dépannage

### Problème : "YOLO non disponible"
```bash
# Vérifier l'installation
pip install ultralytics opencv-python torch
```

### Problème : Modèle non trouvé
```bash
# Vérifier le chemin du modèle
ls server/models/
```

### Problème : Vidéo non trouvée
```bash
# Vérifier le chemin de la vidéo
ls server/videos/
```

## 📈 Performance

- **FPS** : ~30 FPS en streaming
- **Mémoire** : ~2-4 GB RAM recommandés
- **GPU** : Support CUDA si disponible
- **CPU** : Multi-core recommandé

## 🔄 Intégration avec l'interface

Le système est entièrement intégré avec :
- ✅ **DetectionPanel** : Affichage des détections en temps réel
- ✅ **PerformancePanel** : Statistiques de performance
- ✅ **CameraView** : Contrôle vidéo et détection
- ✅ **Base de données** : Historique complet

## 📝 Exemple d'utilisation complète

```python
import requests

# 1. Vérifier la santé du serveur
response = requests.get('http://localhost:5000/api/health')
print(response.json())

# 2. Charger un modèle
response = requests.post('http://localhost:5000/api/yolo/model', json={
    'model_path': 'models/best.pt',
    'confidence': 0.6
})
print(response.json())

# 3. Démarrer le streaming
response = requests.post('http://localhost:5000/api/yolo/stream/start', json={
    'video_path': 'videos/test.mp4'
})
print(response.json())

# 4. Vérifier les détections
response = requests.get('http://localhost:5000/api/detections')
print(response.json())
```

## 🎉 Félicitations !

Votre système YOLO est maintenant intégré et prêt à détecter des objets en temps réel ! 🚀 

from flask import send_from_directory

@app.route('/videos/<path:filename>')
def serve_video(filename):
    return send_from_directory('videos', filename) 