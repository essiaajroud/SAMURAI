import os
import cv2
import yaml
from pathlib import Path

# Configuration
base_dir = 'C:/Users/rteen/Desktop/mini_dataset'
splits = ['train', 'valid']  # Traiter tous les dossiers
yaml_path = os.path.join(base_dir, 'data.yaml')
output_base_dir = 'D:/dataset_anno'

# Lire les classes depuis le fichier YAML
try:
    with open(yaml_path, 'r') as f:
        data_yaml = yaml.safe_load(f)
    class_names = data_yaml['names']
except FileNotFoundError:
    print(f"Erreur : Fichier {yaml_path} non trouvé.")
    exit(1)
except KeyError:
    print(f"Erreur : 'names' non défini dans {yaml_path}.")
    exit(1)

# Couleurs pour les boîtes englobantes (BGR)
colors = [
    (0, 255, 0),    # Vert pour soldier
    (255, 0, 0),    # Bleu pour person
    (0, 0, 255),    # Rouge pour weapon
    (255, 255, 0),  # Cyan pour civilian_vehicles
    (0, 255, 255),  # Jaune pour military_vehicles
    (255, 0, 255),   # Magenta pour military_aircraft
    (128, 128, 128) # Gris pour civilian_aircraft
]

# Traiter chaque split
for split in splits:
    image_dir = os.path.join(base_dir, split, 'images')
    label_dir = os.path.join(base_dir, split, 'labels')
    output_dir = os.path.join(output_base_dir, split)
    
    # Créer le dossier de sortie
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    if not os.path.exists(image_dir):
        print(f"Dossier non trouvé : {image_dir}")
        continue
    
    # Parcourir toutes les images
    for image_file in os.listdir(image_dir):
        if not image_file.lower().endswith(('.jpg', '.jpeg', '.png')):
            continue
        
        # Charger l'image
        image_path = os.path.join(image_dir, image_file)
        image = cv2.imread(image_path)
        if image is None:
            print(f"Impossible de charger : {image_path}")
            continue
        
        # Dimensions de l'image
        height, width = image.shape[:2]
        
        # Charger l'annotation correspondante
        label_file = os.path.splitext(image_file)[0] + '.txt'
        label_path = os.path.join(label_dir, label_file)
        
        if not os.path.exists(label_path):
            print(f"Annotation manquante : {label_path}")
            continue
        
        # Lire les annotations
        try:
            with open(label_path, 'r') as f:
                lines = f.readlines()
        except Exception as e:
            print(f"Erreur de lecture de {label_path} : {e}")
            continue
        
        # Dessiner chaque boîte englobante
        for line in lines:
            parts = line.strip().split()
            if len(parts) != 5:
                print(f"Format incorrect dans {label_path} : {line.strip()}")
                continue
            
            try:
                class_id, x_center, y_center, w, h = map(float, parts)
                class_id = int(class_id)
            except ValueError:
                print(f"Valeurs invalides dans {label_path} : {line.strip()}")
                continue
            
            # Convertir les coordonnées YOLO en pixels
            x_center *= width
            y_center *= height
            w *= width
            h *= height
            
            # Calculer les coordonnées de la boîte
            x1 = int(x_center - w / 2)
            y1 = int(y_center - h / 2)
            x2 = int(x_center + w / 2)
            y2 = int(y_center + h / 2)
            
            # Dessiner la boîte englobante
            color = colors[class_id % len(colors)]
            cv2.rectangle(image, (x1, y1), (x2, y2), color, 2)
            
            # Ajouter l'étiquette de classe
            label = class_names[class_id]
            cv2.putText(image, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        
        # Sauvegarder l'image annotée
        output_path = os.path.join(output_dir, image_file)
        cv2.imwrite(output_path, image)
        print(f"Image annotée sauvegardée : {output_path}")
    
    print(f"Toutes les images de {split} ont été sauvegardées dans : {output_dir}")

print(f"Traitement terminé pour tous les dossiers.")