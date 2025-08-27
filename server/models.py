"""
Ce fichier définit les modèles de la base de données (schémas des tables)
en utilisant SQLAlchemy.
"""
from .extensions import db
from datetime import datetime, timezone

class Detection(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    object_id = db.Column(db.Integer, nullable=False)
    label = db.Column(db.String(50), nullable=False)
    confidence = db.Column(db.Float, nullable=False)
    x = db.Column(db.Float, nullable=False)
    y = db.Column(db.Float, nullable=False)
    speed = db.Column(db.Float)
    distance = db.Column(db.Float)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    history_id = db.Column(db.String(100), unique=True, nullable=False)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)

    def to_dict(self):
        return {
            'id': self.object_id, 
            'label': self.label, 
            'confidence': self.confidence,
            'x': self.x, 
            'y': self.y, 
            'speed': self.speed, 
            'distance': self.distance,
            'timestamp': self.timestamp.isoformat(), 
            'historyId': self.history_id,
            'latitude': self.latitude, 
            'longitude': self.longitude
        }

class Trajectory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    object_id = db.Column(db.Integer, nullable=False)
    label = db.Column(db.String(50), nullable=False)
    start_time = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    last_seen = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    is_active = db.Column(db.Boolean, default=True)

    def to_dict(self):
        return {
            'id': self.object_id, 
            'label': self.label,
            'startTime': self.start_time.isoformat(),
            'lastSeen': self.last_seen.isoformat(), 
            'isActive': self.is_active
        }

class TrajectoryPoint(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    trajectory_id = db.Column(db.Integer, db.ForeignKey('trajectory.id'), nullable=False)
    x = db.Column(db.Float, nullable=False)
    y = db.Column(db.Float, nullable=False)
    speed = db.Column(db.Float)
    distance = db.Column(db.Float)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    latitude = db.Column(db.Float, nullable=True) 
    longitude = db.Column(db.Float, nullable=True)

    def to_dict(self):
        return {
            'x': self.x, 
            'y': self.y, 
            'speed': self.speed, 
            'distance': self.distance,
            'timestamp': self.timestamp.isoformat(),
            'latitude': self.latitude, 
            'longitude': self.longitude
        }