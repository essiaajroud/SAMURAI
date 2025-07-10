# 🚀 Système de Détection Militaire - Version Dynamique

## 📋 Vue d'ensemble

Ce système de détection militaire est entièrement **dynamique** et **en temps réel**. Toutes les données sont sauvegardées automatiquement, les statistiques sont calculées en temps réel, et le système s'auto-optimise.

## 🔄 Fonctionnalités Dynamiques

### ✅ **Sauvegarde Automatique des Détections**
- **Temps réel** : Chaque détection YOLO est sauvegardée instantanément
- **Base de données** : SQLite avec SQLAlchemy pour la persistance
- **Trajectoires** : Suivi automatique des objets détectés
- **Métadonnées** : Timestamp, confiance, position, vitesse

### ✅ **Historisation 24h Automatique**
- **Fenêtres temporelles** : 1h, 6h, 24h configurable
- **Filtrage dynamique** : Par confiance, classe d'objet, période
- **Tri chronologique** : Plus récentes en premier
- **Export complet** : Toutes les données exportables

### ✅ **Statistiques en Temps Réel**
- **Calculs dynamiques** : FPS, nombre d'objets, confiance moyenne
- **Fenêtres multiples** : 1s, 1min, 5min, 1h, 24h
- **Métriques avancées** : Vitesse, distance, trajectoires
- **API temps réel** : `/api/statistics/realtime`

### ✅ **Maintenance Automatique**
- **Nettoyage intelligent** : Suppression des données anciennes
- **Optimisation DB** : VACUUM et ANALYZE automatiques
- **Sauvegardes** : Quotidiennes avec rotation
- **Monitoring** : Vérification de santé continue

## 🛠️ Architecture Dynamique

### **Backend (Flask)**
```
server/
├── app.py                 # Serveur principal avec API dynamique
├── yolo_detector.py       # Détecteur YOLO avec callback temps réel
├── config.py              # Configuration centralisée
├── maintenance.py         # Service de maintenance automatique
├── start_server_enhanced.py # Démarrage avec tous les services
└── README_DYNAMIC.md      # Cette documentation
```

### **Frontend (React)**
```
client/src/components/
├── DetectionPanel.js      # Affichage dynamique des détections
├── CameraView.js          # Streaming vidéo en temps réel
├── PerformancePanel.js    # Statistiques dynamiques
└── Header.js              # Contrôles système
```

## 🚀 Démarrage Rapide

### **1. Installation des dépendances**
```bash
cd server
pip install -r requirements.txt
```

### **2. Configuration**
```bash
# Copier le modèle YOLO
cp your_model.onnx models/best.onnx

# Ajouter des vidéos
cp your_videos.mp4 videos/
```

### **3. Démarrage du serveur**
```bash
# Démarrage simple
python app.py

# Démarrage avec maintenance automatique
python start_server_enhanced.py
```

### **4. Démarrage du client**
```bash
cd client
npm start
```

## 📊 API Dynamique

### **Détections en Temps Réel**
```http
GET /api/detections/current?time_window=5&confidence=0.5&limit=10
```

### **Statistiques Dynamiques**
```http
GET /api/statistics/realtime
```

### **Historique avec Filtres**
```http
GET /api/detections?timeRange=24h&confidence=0.7&class=person
```

### **Export Complet**
```http
POST /api/export
```

## 🔧 Configuration Dynamique

### **Fichier `config.py`**
```python
class Config:
    # Détections
    DETECTION_CLEANUP_HOURS = 24
    DETECTION_LOW_CONFIDENCE_THRESHOLD = 0.3
    
    # Trajectoires
    TRAJECTORY_INACTIVE_HOURS = 1
    TRAJECTORY_POINT_CLEANUP_DAYS = 3
    
    # Maintenance
    MAINTENANCE_CLEANUP_INTERVAL_MINUTES = 30
    MAINTENANCE_BACKUP_TIME = "02:00"
```

## 📈 Monitoring et Maintenance

### **Logs Automatiques**
- **Détections** : Chaque détection est loggée
- **Erreurs** : Gestion automatique des erreurs
- **Performance** : Métriques système en temps réel
- **Maintenance** : Actions de nettoyage documentées

### **Sauvegardes Automatiques**
- **Quotidiennes** : À 2h du matin
- **Rotation** : Garde 7 jours de sauvegardes
- **Intégrité** : Vérification automatique

### **Nettoyage Intelligent**
- **Détections anciennes** : Suppression après 24h
- **Faible confiance** : Nettoyage des détections < 30%
- **Trajectoires inactives** : Marquage après 1h
- **Points anciens** : Suppression après 3 jours

## 🎯 Utilisation Dynamique

### **1. Démarrer la Détection**
- Cliquer sur "Start Detection" dans CameraView
- Le système démarre automatiquement le streaming
- Les détections sont sauvegardées en temps réel

### **2. Consulter l'Historique**
- Onglet "History" dans DetectionPanel
- Filtres dynamiques : temps, confiance, classe
- Export complet avec métadonnées

### **3. Monitorer les Performances**
- PerformancePanel affiche les métriques en temps réel
- FPS, temps d'inférence, nombre d'objets
- Graphiques dynamiques

### **4. Maintenance Automatique**
- Le système s'auto-optimise
- Nettoyage automatique des données
- Sauvegardes quotidiennes

## 🔍 Dépannage

### **Problème : Vidéo ne s'affiche pas**
```bash
# Vérifier OpenCV
pip install opencv-python

# Vérifier le modèle YOLO
ls models/best.onnx
```

### **Problème : Détections non sauvegardées**
```bash
# Vérifier la base de données
ls instance/detection_history.db

# Vérifier les logs
tail -f server.log
```

### **Problème : Performance lente**
```bash
# Nettoyer manuellement
curl -X POST http://localhost:5000/api/cleanup/auto

# Vérifier les statistiques
curl http://localhost:5000/api/statistics/realtime
```

## 📝 Notes Importantes

### **✅ Système Entièrement Dynamique**
- **Pas de données statiques** : Tout est calculé en temps réel
- **Sauvegarde automatique** : Chaque détection est persistée
- **Optimisation continue** : Maintenance automatique
- **Monitoring intégré** : Santé système en temps réel

### **🎯 Performance Optimisée**
- **Base de données** : Index automatiques sur les timestamps
- **Requêtes optimisées** : Filtrage au niveau SQL
- **Cache intelligent** : Mise en cache des statistiques
- **Nettoyage automatique** : Évite l'accumulation de données

### **🔒 Sécurité et Fiabilité**
- **Gestion d'erreurs** : Try-catch sur toutes les opérations
- **Rollback automatique** : En cas d'erreur de base de données
- **Logs complets** : Traçabilité de toutes les opérations
- **Sauvegardes** : Protection contre la perte de données

---

**🎉 Le système est maintenant entièrement dynamique et prêt pour la production !** 