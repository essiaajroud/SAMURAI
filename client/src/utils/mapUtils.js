// mapUtils.js - Utility functions for tracking map and geospatial operations
// Provides random data generation, coordinate conversion, filtering, and formatting for detections and trajectories

// --- Paris Test Area Bounds ---
const PARIS_BOUNDS = {
  north: 48.9022,
  south: 48.8156,
  east: 2.4150,
  west: 2.2241
};

// --- Supported Object Types ---
export const OBJECT_TYPES = {
  PERSON: 'person',
  CAR: 'car',
  TRUCK: 'truck',
  BICYCLE: 'bicycle',
  MOTORCYCLE: 'motorcycle',
  BUS: 'bus'
};

// --- Color Mapping for Object Types ---
export const OBJECT_COLORS = {
  [OBJECT_TYPES.PERSON]: '#ff4444',
  [OBJECT_TYPES.CAR]: '#4444ff',
  [OBJECT_TYPES.TRUCK]: '#44ff44',
  [OBJECT_TYPES.BICYCLE]: '#ffff44',
  [OBJECT_TYPES.MOTORCYCLE]: '#ff44ff',
  [OBJECT_TYPES.BUS]: '#44ffff'
};

// --- Generate a Random Position within Paris Bounds ---
export const generateRandomPosition = () => {
  const lat = PARIS_BOUNDS.south + Math.random() * (PARIS_BOUNDS.north - PARIS_BOUNDS.south);
  const lng = PARIS_BOUNDS.west + Math.random() * (PARIS_BOUNDS.east - PARIS_BOUNDS.west);
  return { latitude: lat, longitude: lng };
};

// --- Generate a Random Trajectory for an Object ---
export const generateRandomTrajectory = (objectId, label, duration = 60000) => {
  const startTime = Date.now() - duration;
  const endTime = Date.now();
  const pointCount = Math.floor(duration / 5000); // One point every 5 seconds
  const points = [];
  let currentPos = generateRandomPosition();
  for (let i = 0; i < pointCount; i++) {
    const progress = i / (pointCount - 1);
    const timestamp = startTime + (endTime - startTime) * progress;
    // Add some random movement
    currentPos = {
      latitude: currentPos.latitude + (Math.random() - 0.5) * 0.001,
      longitude: currentPos.longitude + (Math.random() - 0.5) * 0.001
    };
    points.push({
      latitude: currentPos.latitude,
      longitude: currentPos.longitude,
      timestamp: timestamp
    });
  }
  return {
    id: objectId,
    label: label,
    startTime: startTime,
    lastSeen: endTime,
    points: points
  };
};

// --- Convert Camera (image) Coordinates to GPS Coordinates ---
// Simulates conversion from image coordinates to GPS using camera bounds
export const convertCameraToGPS = (x, y, imageWidth, imageHeight, cameraBounds) => {
  // Normalize coordinates (0-1)
  const normalizedX = x / imageWidth;
  const normalizedY = y / imageHeight;
  // Convert to GPS coordinates
  const latitude = cameraBounds.south + (cameraBounds.north - cameraBounds.south) * (1 - normalizedY);
  const longitude = cameraBounds.west + (cameraBounds.east - cameraBounds.west) * normalizedX;
  return { latitude, longitude };
};

// --- Calculate Distance Between Two GPS Points (Haversine Formula) ---
export const calculateDistance = (lat1, lng1, lat2, lng2) => {
  const R = 6371; // Earth radius in km
  const dLat = (lat2 - lat1) * Math.PI / 180;
  const dLng = (lng2 - lng1) * Math.PI / 180;
  const a = 
    Math.sin(dLat/2) * Math.sin(dLat/2) +
    Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) * 
    Math.sin(dLng/2) * Math.sin(dLng/2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
  return R * c;
};

// --- Filter Detections by Geographic Area ---
export const filterDetectionsByArea = (detections, bounds) => {
  return detections.filter(detection => {
    return detection.latitude >= bounds.south &&
           detection.latitude <= bounds.north &&
           detection.longitude >= bounds.west &&
           detection.longitude <= bounds.east;
  });
};

// --- Generate Test Detections for Demo Purposes ---
export const generateTestDetections = (count = 5) => {
  const objectTypes = Object.values(OBJECT_TYPES);
  const detections = [];
  for (let i = 0; i < count; i++) {
    const position = generateRandomPosition();
    const objectType = objectTypes[Math.floor(Math.random() * objectTypes.length)];
    detections.push({
      id: `test_${i}`,
      label: objectType,
      confidence: 0.7 + Math.random() * 0.3, // 70-100%
      latitude: position.latitude,
      longitude: position.longitude,
      timestamp: Date.now() - Math.random() * 30000, // Last 30 seconds
      bbox: {
        x: Math.random() * 640,
        y: Math.random() * 480,
        width: 50 + Math.random() * 100,
        height: 50 + Math.random() * 100
      }
    });
  }
  return detections;
};

// --- Generate Test Trajectories for Demo Purposes ---
export const generateTestTrajectories = (count = 3) => {
  const objectTypes = Object.values(OBJECT_TYPES);
  const trajectories = {};
  for (let i = 0; i < count; i++) {
    const objectType = objectTypes[Math.floor(Math.random() * objectTypes.length)];
    const trajectory = generateRandomTrajectory(`traj_${i}`, objectType);
    trajectories[trajectory.id] = trajectory;
  }
  return trajectories;
};

// --- Validate GPS Coordinates ---
export const isValidGPS = (latitude, longitude) => {
  return latitude >= -90 && latitude <= 90 &&
         longitude >= -180 && longitude <= 180;
};

// --- Format Coordinates for Display ---
export const formatCoordinates = (latitude, longitude, precision = 6) => {
  return {
    lat: latitude.toFixed(precision),
    lng: longitude.toFixed(precision)
  };
};

// --- Calculate the Center of a Set of Detections ---
export const calculateCenter = (detections) => {
  if (detections.length === 0) {
    return { latitude: 48.8566, longitude: 2.3522 }; // Default: Paris
  }
  const sumLat = detections.reduce((sum, d) => sum + d.latitude, 0);
  const sumLng = detections.reduce((sum, d) => sum + d.longitude, 0);
  return {
    latitude: sumLat / detections.length,
    longitude: sumLng / detections.length
  };
}; 