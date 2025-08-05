# 🗺️ Carte de Tracking - Samurai Dashboard

## Vue d'ensemble

La carte de tracking est un composant interactif qui permet de visualiser en temps réel la localisation des objets détectés par votre système YOLO. Elle utilise Leaflet pour afficher une carte interactive avec des marqueurs colorés et des trajectoires.

## 🚀 Installation

### 1. Installer les dépendances

```bash
cd client
npm install leaflet react-leaflet
```

### 2. Vérifier l'installation

Les CDN de Leaflet sont déjà inclus dans `public/index.html`. Si vous préférez utiliser npm, vous pouvez supprimer les CDN et importer directement :

```javascript
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
```

## 📋 Fonctionnalités

### ✅ Fonctionnalités implémentées

- **Carte interactive** avec OpenStreetMap
- **Marqueurs colorés** selon le type d'objet détecté
- **Trajectoires** historiques des objets
- **Popups informatifs** avec détails des détections
- **Contrôles de couches** (activer/désactiver détections et trajectoires)
- **Centrage automatique** sur les détections
- **Légende** avec codes couleur
- **Design responsive** pour mobile et desktop
- **Mode démonstration** avec données simulées

### 🎯 Types d'objets supportés

- 👤 **Personne** (rouge)
- 🚗 **Voiture** (bleu)
- 🚛 **Camion** (vert)
- 🚲 **Vélo** (jaune)
- 🏍️ **Moto** (magenta)
- 🚌 **Bus** (cyan)

## 🔧 Utilisation

### Composant principal

```javascript
import TrackingMap from './components/TrackingMap';

<TrackingMap
  detections={currentDetections}
  trajectoryHistory={trajectoryHistory}
  isConnected={isConnected}
  mapCenter={[48.8566, 2.3522]} // Paris par défaut
  zoomLevel={13}
/>
```

### Mode démonstration

```javascript
import MapDemo from './components/MapDemo';

<MapDemo />
```

## 📊 Format des données

### Détections

```javascript
{
  id: "unique_id",
  label: "person", // Type d'objet
  confidence: 0.95, // Confiance (0-1)
  latitude: 48.8566, // Coordonnée GPS
  longitude: 2.3522, // Coordonnée GPS
  timestamp: 1640995200000, // Timestamp
  bbox: { // Coordonnées dans l'image
    x: 100,
    y: 150,
    width: 80,
    height: 120
  }
}
```

### Trajectoires

```javascript
{
  id: "trajectory_id",
  label: "person",
  startTime: 1640995200000,
  lastSeen: 1640995260000,
  points: [
    {
      latitude: 48.8566,
      longitude: 2.3522,
      timestamp: 1640995200000
    }
    // ... autres points
  ]
}
```

## � Affichage des alertes sur la carte

Depuis la version dynamique, la carte affiche aussi les alertes générées par l'IA et la cartographie OSM :
- Marqueurs colorés (rouge = danger, vert = sécurisé, orange = anomalie)
- Popups détaillées (type, message, coordonnées, zone)
- Contrôle pour afficher/masquer les alertes
- Polling automatique de l'API `/api/alerts` toutes les 5s

### Exemple d'alerte (format)
```json
{
  "type": "danger",
  "message": "Arme détectée en zone non-militaire (objet 42)",
  "lat": 48.8566,
  "lon": 2.3522,
  "zone": "civile",
  "timestamp": "2025-08-05T12:34:56Z",
  "color": "red"
}
```

## �🛠️ Utilitaires

Le fichier `utils/mapUtils.js` contient des fonctions utiles :
- `generateRandomPosition()` - Génère une position aléatoire
- `generateTestDetections(count)` - Génère des détections de test
- `generateTestTrajectories(count)` - Génère des trajectoires de test
- `convertCameraToGPS(x, y, width, height, bounds)` - Conversion coordonnées caméra → GPS
- `calculateDistance(lat1, lng1, lat2, lng2)` - Calcul de distance entre points
- `isValidGPS(lat, lng)` - Validation des coordonnées GPS

## 🎨 Personnalisation

### Changer les couleurs

Modifiez `OBJECT_COLORS` dans `utils/mapUtils.js` :

```javascript
export const OBJECT_COLORS = {
  'person': '#ff4444',
  'car': '#4444ff',
  // ... autres couleurs
};
```

### Changer le centre de la carte

```javascript
<TrackingMap
  mapCenter={[VOTRE_LAT, VOTRE_LNG]}
  zoomLevel={15}
/>
```

### Ajouter de nouveaux types d'objets

1. Ajoutez le type dans `OBJECT_TYPES`
2. Ajoutez la couleur dans `OBJECT_COLORS`
3. Mettez à jour la légende dans `TrackingMap.js`

## 🔗 Intégration avec le backend

### Endpoint pour les détections avec GPS

```python
# Dans votre backend Flask
@app.route('/api/detections/current')
def get_current_detections():
    # Ajouter les coordonnées GPS aux détections
    detections = []
    for detection in current_detections:
        # Convertir les coordonnées de l'image en GPS
        gps_coords = convert_image_to_gps(
            detection['bbox']['x'],
            detection['bbox']['y'],
            image_width,
            image_height,
            camera_bounds
        )
        
        detection['latitude'] = gps_coords['latitude']
        detection['longitude'] = gps_coords['longitude']
        detections.append(detection)
    
    return jsonify({'detections': detections})
```

### Endpoint pour les trajectoires

```python
@app.route('/api/trajectories')
def get_trajectories():
    # Retourner l'historique des trajectoires
    return jsonify(trajectory_history)
```

## 🐛 Dépannage

### La carte ne s'affiche pas

1. Vérifiez que Leaflet est installé : `npm list leaflet`
2. Vérifiez les CDN dans `public/index.html`
3. Ouvrez la console du navigateur pour les erreurs

### Les marqueurs n'apparaissent pas

1. Vérifiez que les données contiennent `latitude` et `longitude`
2. Vérifiez que les coordonnées sont valides (-90 à 90 pour lat, -180 à 180 pour lng)
3. Utilisez `isValidGPS()` pour valider les coordonnées

### Performance lente

1. Limitez le nombre de marqueurs affichés
2. Utilisez `useCallback` pour optimiser les re-renders
3. Implémentez une pagination pour les trajectoires

## 📱 Responsive Design

La carte s'adapte automatiquement aux différentes tailles d'écran :

- **Desktop** : Carte complète avec tous les contrôles
- **Tablet** : Contrôles réorganisés
- **Mobile** : Interface simplifiée, carte en pleine hauteur

## 🔮 Prochaines étapes

- [ ] Intégration avec des données GPS réelles
- [ ] Clustering des marqueurs pour les zones denses
- [ ] Animations de mouvement en temps réel
- [ ] Export des trajectoires en KML/GPX
- [ ] Zones d'intérêt et alertes géographiques
- [ ] Mode 3D avec élévation

## 📞 Support

Pour toute question ou problème avec la carte de tracking, consultez :

1. La documentation Leaflet : https://leafletjs.com/
2. Les logs de la console du navigateur
3. Les exemples dans `MapDemo.js` 