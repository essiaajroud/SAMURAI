# Detection History Backend Server

Flask server to store and manage the history of detections and trajectories.

## Installation

1. **Create a virtual environment**:
```bash
python -m venv venv
```

2. **Activate the virtual environment**:
```bash
# Windows
venv\Scripts\activate
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process
.\venv\Scripts\Activate.ps1

# Linux/Mac
source venv/bin/activate
```

3. **Install dependencies**:
```bash
pip install -r requirements.txt
```

## Starting the Server

```bash
python app.py
```

The server will be accessible at `http://localhost:5000`


## API Endpoints

### Detections
- `POST /api/detections` - Save a new detection
- `GET /api/detections` - Retrieve detections with filters

### Trajectories
- `GET /api/trajectories` - Retrieve all trajectories

### Statistics
- `GET /api/statistics` - Global statistics

### Alertes intelligentes (IA + OSM)
- `GET /api/alerts` - Retourne la liste des alertes générées dynamiquement selon la logique IA et la cartographie OSM.
  - **Paramètres** : `lat`, `lon` (optionnels, pour centrer la zone OSM)
  - **Réponse** : liste d'alertes `{type, message, lat, lon, zone, timestamp, color}`
  - **Logique** :
    - Arme détectée hors zone militaire : danger (rouge)
    - Arme détectée en zone militaire : sécurisé (vert)
    - Personne avec vitesse anormale : anomalie (orange)

### Maintenance
- `POST /api/cleanup` - Clean up old data
- `POST /api/export` - Export all data
- `GET /api/health` - Server health check

## Database

The SQLite database is automatically created in `detection_history.db`

### Tables
- `detection` - Detection history
- `trajectory` - Trajectory information
- `trajectory_point` - Individual trajectory points

---

## 🛡️ Alertes dynamiques IA + OSM

Le backend croise les résultats de détection/tracking (YOLO) avec la cartographie OSMnx (zones militaires) :
- Utilisation de OSMnx et Shapely pour charger les polygones de zones militaires autour du rover
- Génération d'alertes en temps réel selon :
  - Arme détectée hors zone militaire : danger
  - Arme détectée en zone militaire : sécurisé
  - Personne avec vitesse anormale : anomalie

Les alertes sont exposées via `/api/alerts` et affichées côté frontend dans les logs et sur la carte (voir README principal).

## Configuration

Edit `app.py` to change:
- Server port
- Database type
- Secret key
- Cleanup parameters 