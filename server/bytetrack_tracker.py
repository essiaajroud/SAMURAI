from collections import defaultdict
import numpy as np

class ByteTracker:
    def __init__(self, track_thresh=0.5, track_buffer=30, match_thresh=0.8):
        self.track_thresh = track_thresh
        self.track_buffer = track_buffer
        self.match_thresh = match_thresh
        self.track_history = defaultdict(list)
        self.tracks = []
        self.next_id = 1
        self.disappeared = defaultdict(int)

    def update(self, detections, frame=None):
        """
        Update tracks using a simple IoU-based tracking (ByteTrack-style placeholder)
        Args:
            detections: List of detections [x1,y1,x2,y2,conf,cls]
            frame: Current frame (unused)
        Returns:
            tracks: Updated tracks (dicts with track_id, bbox, confidence, class_id)
        """
        if len(detections) == 0:
            return []
        detections = [det for det in detections if det[4] >= self.track_thresh]
        current_tracks = []
        for detection in detections:
            bbox = detection[:4]
            confidence = detection[4]
            class_id = detection[5]
            best_iou = 0
            best_track_idx = -1
            for i, track in enumerate(self.tracks):
                track_bbox = track['bbox']
                iou = self._calculate_iou(bbox, track_bbox)
                if iou > best_iou and iou > self.match_thresh:
                    best_iou = iou
                    best_track_idx = i
            if best_track_idx >= 0:
                track_id = self.tracks[best_track_idx]['track_id']
                self.tracks[best_track_idx].update({
                    'bbox': bbox,
                    'confidence': confidence,
                    'class_id': class_id
                })
                self.disappeared[track_id] = 0
                current_tracks.append(self.tracks[best_track_idx])
            else:
                new_track = {
                    'track_id': self.next_id,
                    'bbox': bbox,
                    'confidence': confidence,
                    'class_id': class_id
                }
                self.tracks.append(new_track)
                self.disappeared[self.next_id] = 0
                self.track_history[self.next_id] = []
                current_tracks.append(new_track)
                self.next_id += 1
        for track in self.tracks:
            track_id = track['track_id']
            if track_id not in [t['track_id'] for t in current_tracks]:
                self.disappeared[track_id] += 1
                if self.disappeared[track_id] <= self.track_buffer:
                    current_tracks.append(track)
        self.tracks = current_tracks
        return self.tracks

    def _calculate_iou(self, bbox1, bbox2):
        x1 = max(bbox1[0], bbox2[0])
        y1 = max(bbox1[1], bbox2[1])
        x2 = min(bbox1[2], bbox2[2])
        y2 = min(bbox1[3], bbox2[3])
        intersection = max(0, x2 - x1) * max(0, y2 - y1)
        area1 = (bbox1[2] - bbox1[0]) * (bbox1[3] - bbox1[1])
        area2 = (bbox2[2] - bbox2[0]) * (bbox2[3] - bbox2[1])
        union = area1 + area2 - intersection
        return intersection / union if union > 0 else 0

    def reset(self):
        self.track_history = defaultdict(list)
        self.tracks = []
        self.next_id = 1
        self.disappeared = defaultdict(int)
