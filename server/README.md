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

## Configuration

Edit `app.py` to change:
- Server port
- Database type
- Secret key
- Cleanup parameters 