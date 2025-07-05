# Detection History Backend Server

Serveur Flask pour stocker et gérer l'historique des détections et trajectoires.

## Installation

1. **Créer un environnement virtuel** :
```bash
python -m venv venv
```

2. **Activer l'environnement virtuel** :
```bash
# Windows
venv\Scripts\activate
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process
.\venv\Scripts\Activate.ps1


# Linux/Mac
source venv/bin/activate
```

3. **Installer les dépendances** :
```bash
pip install -r requirements.txt
```

## Démarrage du serveur

```bash
python app.py
```

Le serveur sera accessible sur `http://localhost:5000`

## API Endpoints

### Détections
- `POST /api/detections` - Sauvegarder une nouvelle détection
- `GET /api/detections` - Récupérer les détections avec filtres

### Trajectoires
- `GET /api/trajectories` - Récupérer toutes les trajectoires

### Statistiques
- `GET /api/statistics` - Statistiques globales

### Maintenance
- `POST /api/cleanup` - Nettoyer les données anciennes
- `POST /api/export` - Exporter toutes les données
- `GET /api/health` - Vérification de l'état du serveur

## Base de données

La base de données SQLite est automatiquement créée dans `detection_history.db`

### Tables
- `detection` - Historique des détections
- `trajectory` - Informations sur les trajectoires
- `trajectory_point` - Points individuels des trajectoires

## Configuration

Modifier `app.py` pour changer :
- Port du serveur
- Type de base de données
- Clé secrète
- Paramètres de nettoyage 