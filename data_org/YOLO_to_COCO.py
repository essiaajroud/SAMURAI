import os
import json
from PIL import Image

def yolo_to_coco(base_dir, output_dir, class_names):
    """
    Convertit des annotations YOLO en format COCO pour une structure de dossier spécifique,
    avec un fichier JSON séparé pour chaque sous-ensemble (train, valid, test).

    :param base_dir: Répertoire de base contenant les dossiers test, valid, train
    :param output_dir: Répertoire où sauvegarder les fichiers JSON de sortie COCO
    :param class_names: Liste des noms de classes (dans l'ordre des IDs YOLO)
    """
    # Créer le répertoire de sortie s'il n'existe pas
    os.makedirs(output_dir, exist_ok=True)

    # Dossiers à traiter
    subsets = ['train', 'valid', 'test']

    for subset in subsets:
        # Structure de base du fichier COCO pour ce sous-ensemble
        coco_format = {
            "info": {  # Ajout du champ 'info'
                "description": f"Samurai {subset.capitalize()} Dataset",
                "url": "",
                "version": "1.0",
                "year": 2025,
                "contributor": "Your Name",
                "date_created": "2025/06/02"
            },
            "images": [],
            "annotations": [],
            "categories": []
        }

        # Ajouter les catégories (classes)
        for i, name in enumerate(class_names):
            coco_format["categories"].append({
                "id": i + 1,
                "name": name,
                "supercategory": "none"
            })

        annotation_id = 1
        image_id = 1  # ID d'image pour ce sous-ensemble

        images_dir = os.path.join(base_dir, subset, 'images')
        labels_dir = os.path.join(base_dir, subset, 'labels')

        # Vérifier si les dossiers existent
        if not os.path.exists(images_dir) or not os.path.exists(labels_dir):
            print(f"Avertissement: Dossiers manquants pour {subset} - traitement ignoré")
            continue

        # Parcourir toutes les images dans le dossier images
        for image_name in os.listdir(images_dir):
            if not image_name.lower().endswith(('.jpg', '.png', '.jpeg')):
                continue  # Ignorer les fichiers non-images

            # Chemin complet de l'image
            image_path = os.path.join(images_dir, image_name)
            with Image.open(image_path) as img:
                width, height = img.size

            # Chemin relatif seulement
            rel_file_name = f"{subset}/images/{image_name}"

            # Ajouter l'image à la structure COCO
            coco_format["images"].append({
                "id": image_id,
                "file_name": rel_file_name,  # Conserver l'information du sous-dossier
                "width": width,
                "height": height,
            })

            # Chemin du fichier texte YOLO correspondant
            txt_name = os.path.splitext(image_name)[0] + ".txt"
            txt_path = os.path.join(labels_dir, txt_name)

            # Lire les annotations YOLO
            if os.path.exists(txt_path):
                with open(txt_path, "r") as f:
                    lines = f.readlines()

                for line in lines:
                    parts = line.strip().split()
                    if len(parts) != 5:
                        continue  # Ignorer les lignes mal formatées

                    class_id, x_center, y_center, w, h = map(float, parts)

                    # Convertir les coordonnées YOLO (normalisées) en COCO (absolues)
                    x_min = (x_center - w / 2) * width
                    y_min = (y_center - h / 2) * height
                    box_width = w * width
                    box_height = h * height

                    # Ajouter l'annotation à la structure COCO
                    coco_format["annotations"].append({
                        "id": annotation_id,
                        "image_id": image_id,
                        "category_id": int(class_id) + 1,
                        "bbox": [x_min, y_min, box_width, box_height],
                        "area": box_width * box_height,
                        "iscrowd": 0,
                    })

                    annotation_id += 1

            image_id += 1

        # Sauvegarder le fichier JSON COCO pour ce sous-ensemble
        output_json = os.path.join(output_dir, f"{subset}_coco_annotations.json")
        with open(output_json, "w") as f:
            json.dump(coco_format, f, indent=4)

        print(f"Conversion terminée pour {subset}. Fichier COCO sauvegardé sous : {output_json}")

# Exemple d'utilisation
if __name__ == "__main__":
    BASE_DIR = "D:/samurai"
    OUTPUT_DIR = "D:/samurai/coco_annotations"  # Répertoire pour les fichiers JSON
    CLASS_NAMES = ["soldier", "person", "weapon", "civilian_vehicles", "military_vehicles", "military_aircraft", "civilian_aircraft"] 
    
    yolo_to_coco(BASE_DIR, OUTPUT_DIR, CLASS_NAMES)