# SAMURAI

SAMURAI est un projet de machine learning/MLOps pour la gestion et le déploiement de modèles.

## Installation

1. **Cloner le dépôt :**

   ```bash
   git clone https://github.com/essiaajroud/SAMURAI.git
   cd SAMURAI
   ```

2. **Installer les dépendances Python :**

   ```bash
   pip install --upgrade pip
   pip install -r server/requirements-ci.txt
   ```

3. **Installer les dépendances système (Linux) :**
   ```bash
   sudo apt-get update && sudo apt-get install -y libgl1 libglib2.0-0 git
   ```

## Démarrage du serveur

- **Windows :**
  Double-cliquez sur `start_backend.bat` ou lancez :

  ```bat
  start_backend.bat
  ```

- **Linux/Mac :**
  Lancez le script PowerShell :
  ```bash
  pwsh scripts/start_flask_server.ps1
  ```

## Utilisation

- Pour entraîner un modèle :

  ```bash
  python mlops/scripts/train.py --epochs 2 --batch 2 --data dataset/samurai/data.yaml --model server/models/best.pt --device cpu
  ```

- Pour comparer les modèles :
  ```bash
  python mlops/scripts/compare_models.py --run_id <MLflow_Run_ID>
  ```

## Gestion des données

- Les données sont gérées via DVC. Pour récupérer les données :
  ```bash
  dvc pull -r myremote
  ```

## Documentation

- Consultez les guides spécifiques dans le dossier `docs/` ou les fichiers d'aide inclus dans le projet.

## Support

Pour toute question, ouvrez une issue sur le dépôt GitHub.

# 🎯 Military Detection System Dashboard

Système de détection militaire avec historisation complète des détections et trajectoires d'objets.

## 🚀 Fonctionnalités

### Frontend (React)

- **Détection en temps réel** : Affichage live des objets détectés
- **Suivi de trajectoires** : Visualisation des mouvements d'objets
- **Historique complet** : Stockage et consultation des détections passées
- **Analytics avancés** : Statistiques et métriques de performance
- **Alertes intelligentes IA/OSM** : Affichage dynamique d'alertes (danger, anomalie, sécurisé) issues du croisement entre détection IA et cartographie OSM, visibles dans les logs et sur la carte (marqueurs colorés, popups, contrôle de visibilité)
- **Interface moderne** : Dashboard professionnel avec thème militaire

### Backend (Flask)

- **API RESTful** : Endpoints pour la gestion des données
- **Base de données SQLite** : Stockage persistant des détections
- **Gestion des trajectoires** : Suivi complet des mouvements d'objets
- **Alertes dynamiques** : Génération d'alertes en temps réel via IA et croisement cartographique OSM (zones militaires/civiles)
- **Nettoyage automatique** : Suppression des données anciennes
- **Export de données** : Sauvegarde des historiques

## 🛡️ Alertes intelligentes (IA + OSM)

Le système génère des alertes en temps réel selon la logique suivante :

- **Arme détectée en zone non-militaire** : alerte danger (rouge)
- **Arme détectée en zone militaire** : alerte sécurisé (vert)
- **Personne avec vitesse anormale** : alerte anomalie (orange)

Les alertes sont affichées :

- Dans les logs (onglet logs du dashboard)
- Sur la carte (marqueurs colorés, popups, contrôle de visibilité)

**API :**

- `/api/alerts` : retourne la liste des alertes en temps réel (voir `server/README.md` pour détails)

**Techniques :**

- Croisement IA (YOLO, tracking) et cartographie OSMnx (zones militaires)
- Backend : Python Flask, OSMnx, Shapely
- Frontend : React, Leaflet, intégration dynamique

## 📁 Structure du Projet

```
samurai_dashboard/
├── client/                 # Frontend React
│   ├── src/
│   │   ├── components/     # Composants React
│   │   └── App.js         # Application principale
│   └── package.json
├── server/                 # Backend Flask
│   ├── app.py             # Serveur Flask principal
│   ├── requirements.txt   # Dépendances Python
│   ├── start_server.py    # Script de démarrage Python
│   ├── start_server.bat   # Script de démarrage Windows
│   └── README.md          # Documentation backend
└── README.md              # Ce fichier
```

## 🛠️ Installation et Démarrage

### Prérequis

- **Node.js** (v14 ou supérieur)
- **Python** (v3.7 ou supérieur)
- **npm** ou **yarn**

### 1. Frontend (React)

```bash
# Naviguer vers le dossier client
cd client

# Installer les dépendances
npm install

# Démarrer l'application React
npm start
```

L'application sera accessible sur `http://localhost:3000`

### 2. Backend (Flask)

#### Option A : Script automatique (Recommandé)

**Windows :**

```bash
cd server
start_server.bat
```

**Linux/Mac :**

```bash
cd server
python start_server.py
```

#### Option B : Installation manuelle

```bash
# Naviguer vers le dossier server
cd server

# Créer un environnement virtuel
python -m venv venv

# Activer l'environnement virtuel
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate

# Installer les dépendances
pip install -r requirements.txt

# Démarrer le serveur
python app.py
```

Le serveur sera accessible sur `http://localhost:5000`

## 🔧 Configuration

### Variables d'environnement

Créer un fichier `.env` dans le dossier `client/` :

```env
REACT_APP_API_URL=http://localhost:5000/api
```

### Configuration de la base de données

La base de données SQLite est automatiquement créée dans `server/detection_history.db`

## 📊 API Endpoints

### Détections

- `POST /api/detections` - Sauvegarder une détection
- `GET /api/detections` - Récupérer les détections avec filtres

### Trajectoires

- `GET /api/trajectories` - Récupérer toutes les trajectoires

### Statistiques

- `GET /api/statistics` - Statistiques globales

### Maintenance

- `POST /api/cleanup` - Nettoyer les données anciennes
- `POST /api/export` - Exporter toutes les données
- `GET /api/health` - Vérification de l'état du serveur

## 🎮 Utilisation

### 1. Démarrage du système

1. Démarrer le backend Flask
2. Démarrer le frontend React
3. Vérifier la connexion dans l'interface

### 2. Contrôles principaux

- **START/STOP** : Contrôle système complet
- **Play/Pause** : Contrôle vidéo uniquement
- **Filtres** : Par classe d'objet et confiance
- **Onglets** : Navigation entre vues

### 3. Historique et Analytics

- **Onglet History** : Consultation des détections passées
- **Onglet Trajectories** : Analyse des mouvements
- **Onglet Analytics** : Statistiques détaillées
- **Export** : Sauvegarde des données

## 🔍 Fonctionnalités Avancées

### Historisation Automatique

- Sauvegarde automatique de chaque détection
- Suivi des trajectoires en temps réel
- Nettoyage automatique après 24h
- Export des données en JSON

### Filtrage et Recherche

- Filtrage par type d'objet (Person, Vehicle, Drone)
- Filtrage par niveau de confiance
- Filtrage temporel (1h, 6h, 24h)
- Recherche dans l'historique

### Analytics en Temps Réel

- FPS et temps d'inférence
- Nombre d'objets détectés
- Statistiques de confiance
- Métriques de trajectoire

## 🛡️ Sécurité

- CORS configuré pour le développement
- Validation des données côté serveur
- Gestion des erreurs robuste
- Logs de sécurité

## 🔧 Développement

### Structure des données

```javascript
// Détection
{
  id: 1,
  label: "Person",
  confidence: 0.92,
  x: 215,
  y: 304,
  speed: 5.3,
  distance: 12.4,
  timestamp: 1640995200000
}

// Trajectoire
{
  id: 1,
  label: "Person",
  startTime: 1640995200000,
  lastSeen: 1640995260000,
  points: [
    { x: 215, y: 304, timestamp: 1640995200000 },
    { x: 220, y: 310, timestamp: 1640995210000 }
  ]
}
```

### Ajout de nouvelles fonctionnalités

1. **Backend** : Ajouter les endpoints dans `app.py`
2. **Frontend** : Créer les composants dans `client/src/components/`
3. **Base de données** : Modifier les modèles si nécessaire
4. **Tests** : Vérifier la compatibilité

## 🐛 Dépannage

### Problèmes courants

**Backend ne démarre pas :**

- Vérifier que Python 3.7+ est installé
- Vérifier que les dépendances sont installées
- Vérifier que le port 5000 est libre

**Frontend ne se connecte pas au backend :**

- Vérifier que le backend est démarré
- Vérifier l'URL dans la configuration
- Vérifier les logs de la console

**Données non sauvegardées :**

- Vérifier la connexion à la base de données
- Vérifier les permissions d'écriture
- Vérifier les logs du serveur

## 📈 Performance

### Optimisations recommandées

- Utiliser une base de données PostgreSQL pour la production
- Implémenter la pagination pour les grandes quantités de données
- Ajouter un cache Redis pour les requêtes fréquentes
- Optimiser les requêtes de base de données

## 🤝 Contribution

1. Fork le projet
2. Créer une branche pour votre fonctionnalité
3. Commiter vos changements
4. Pousser vers la branche
5. Ouvrir une Pull Request
