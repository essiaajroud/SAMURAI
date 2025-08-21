from datetime import datetime, timezone
from database import db

class Detection(db.Model):
    """Detection model for storing object detection results"""
    id = db.Column(db.Integer, primary_key=True)
    object_id = db.Column(db.Integer, nullable=False)
    label = db.Column(db.String(50), nullable=False)
    confidence = db.Column(db.Float, nullable=False)
    x = db.Column(db.Float, nullable=False)
    y = db.Column(db.Float, nullable=False)
    speed = db.Column(db.Float)
    distance = db.Column(db.Float)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    history_id = db.Column(db.String(100), unique=True)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)

    def to_dict(self):
        """Convert detection to dictionary format"""
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
