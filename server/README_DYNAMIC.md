# 🚀 Military Detection System - Dynamic Version

## 📋 Overview

This military detection system is fully **dynamic** and **real-time**. All data is saved automatically, statistics are calculated in real time, and the system self-optimizes.

## 🔄 Dynamic Features

### ✅ **Automatic Detection Saving**
- **Real-time**: Each YOLO detection is saved instantly
- **Database**: SQLite with SQLAlchemy for persistence
- **Trajectories**: Automatic tracking of detected objects
- **Metadata**: Timestamp, confidence, position, speed

### ✅ **24h Automatic History**
- **Time windows**: 1h, 6h, 24h configurable
- **Dynamic filtering**: By confidence, object class, period
- **Chronological sorting**: Most recent first
- **Full export**: All data exportable

### ✅ **Real-Time Statistics**
- **Dynamic calculations**: FPS, object count, average confidence
- **Multiple windows**: 1s, 1min, 5min, 1h, 24h
- **Advanced metrics**: Speed, distance, trajectories
- **Real-time API**: `/api/statistics/realtime`

### ✅ **Automatic Maintenance**
- **Smart cleanup**: Deletes old data
- **DB optimization**: Automatic VACUUM and ANALYZE
- **Backups**: Daily with rotation
- **Monitoring**: Continuous health check

## 🛠️ Dynamic Architecture

### **Backend (Flask)**
```
server/
├── app.py                 # Main server with dynamic API
├── yolo_detector.py       # YOLO detector with real-time callback
├── config.py              # Centralized configuration
├── maintenance.py         # Automatic maintenance service
├── start_server_enhanced.py # Startup with all services
└── README_DYNAMIC.md      # This documentation
```

### **Frontend (React)**
```
client/src/components/
├── DetectionPanel.js      # Dynamic detection display
├── CameraView.js          # Real-time video streaming
├── PerformancePanel.js    # Dynamic statistics
└── Header.js              # System controls
```

## 🚀 Quick Start

### **1. Install dependencies**
```bash
cd server
pip install -r requirements.txt
```

### **2. Configuration**
```bash
# Copy YOLO model
cp your_model.onnx models/best.onnx

# Add videos
cp your_videos.mp4 videos/
```

### **3. Start the server**
```bash
# Simple start
python app.py

# Start with automatic maintenance
python start_server_enhanced.py
```

### **4. Start the client**
```bash
cd client
npm start
```


## 📊 Dynamic API

### **Alertes intelligentes IA + OSM**
```http
GET /api/alerts
```
- Retourne la liste des alertes générées dynamiquement selon la logique IA et la cartographie OSM.
- **Réponse** : liste d'alertes `{type, message, lat, lon, zone, timestamp, color}`
- **Logique** :
  - Arme détectée hors zone militaire : danger (rouge)
  - Arme détectée en zone militaire : sécurisé (vert)
  - Personne avec vitesse anormale : anomalie (orange)

### **Real-Time Detections**
```http
GET /api/detections/current?time_window=5&confidence=0.5&limit=10
```

### **Dynamic Statistics**
```http
GET /api/statistics/realtime
```

### **History with Filters**
```http
GET /api/detections?timeRange=24h&confidence=0.7&class=person
```

### **Full Export**
```http
POST /api/export
```

## 🔧 Dynamic Configuration

### **File `config.py`**
```python
class Config:
    # Detections
    DETECTION_CLEANUP_HOURS = 24
    DETECTION_LOW_CONFIDENCE_THRESHOLD = 0.3
    # Trajectories
    TRAJECTORY_INACTIVE_HOURS = 1
    TRAJECTORY_POINT_CLEANUP_DAYS = 3
    # Maintenance
    MAINTENANCE_CLEANUP_INTERVAL_MINUTES = 30
    MAINTENANCE_BACKUP_TIME = "02:00"
```

## 📈 Monitoring and Maintenance

### **Automatic Logs**
- **Detections**: Each detection is logged
- **Errors**: Automatic error handling
- **Performance**: Real-time system metrics
- **Maintenance**: Documented cleanup actions

### **Automatic Backups**
- **Daily**: At 2am
- **Rotation**: Keeps 7 days of backups
- **Integrity**: Automatic verification

### **Smart Cleanup**
- **Old detections**: Deleted after 24h
- **Low confidence**: Cleans detections < 30%
- **Inactive trajectories**: Marked after 1h
- **Old points**: Deleted after 3 days

## 🎯 Dynamic Usage

### **1. Start Detection**
- Click "Start Detection" in CameraView
- The system automatically starts streaming
- Detections are saved in real time

### **2. View History**
- "History" tab in DetectionPanel
- Dynamic filters: time, confidence, class
- Full export with metadata

### **3. Monitor Performance**
- PerformancePanel shows real-time metrics
- FPS, inference time, object count
- Dynamic graphs

### **4. Automatic Maintenance**
- The system self-optimizes
- Automatic data cleanup
- Daily backups

## 🔍 Troubleshooting

### **Problem: Video not displaying**
```bash
# Check OpenCV
pip install opencv-python
# Check YOLO model
ls models/best.onnx
```

### **Problem: Detections not saved**
```bash
# Check database
ls instance/detection_history.db
# Check logs
tail -f server.log
```

### **Problem: Slow performance**
```bash
# Manual cleanup
curl -X POST http://localhost:5000/api/cleanup/auto
# Check statistics
curl http://localhost:5000/api/statistics/realtime
```

## 📝 Important Notes

### **✅ Fully Dynamic System**
- **No static data**: Everything is calculated in real time
- **Automatic saving**: Each detection is persisted
- **Continuous optimization**: Automatic maintenance
- **Integrated monitoring**: Real-time system health

### **🎯 Optimized Performance**
- **Database**: Automatic indexes on timestamps
- **Optimized queries**: SQL-level filtering
- **Smart cache**: Statistics caching
- **Automatic cleanup**: Prevents data buildup

### **🔒 Security and Reliability**
- **Error handling**: Try-catch on all operations
- **Automatic rollback**: On database error
- **Complete logs**: Traceability of all operations
- **Backups**: Protection against data loss

---

**🎉 The system is now fully dynamic and ready for production!** 