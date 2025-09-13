import os
from collections import defaultdict

# Chemin vers le dossier des annotations d'entraînement
label_dir = "D:/samurai/train/labels"
class_names = ["soldier", "person", "weapon", "civilian_vehicles", "military_vehicles", "military_aircraft", "civilian_aircraft"]

# Compteur pour les images et les instances par classe
images_per_class = defaultdict(int)
instances_per_class = defaultdict(int)

# Parcourir tous les fichiers d'annotations
for label_file in os.listdir(label_dir):
    if label_file.endswith(".txt"):
        with open(os.path.join(label_dir, label_file), "r") as f:
            lines = f.readlines()
            classes_in_image = set()
            for line in lines:
                try:
                    class_id = int(line.split()[0])
                    if class_id >= len(class_names) or class_id < 0:
                        print(f"Skipping invalid class_id {class_id} in {label_file}")
                        continue
                    classes_in_image.add(class_id)
                    instances_per_class[class_names[class_id]] += 1
                except (IndexError, ValueError):
                    print(f"Error parsing line in {label_file}: {line.strip()}")
                    continue
            for class_id in classes_in_image:
                images_per_class[class_names[class_id]] += 1

# Afficher les résultats
print("Répartition des classes dans l'ensemble train:")
for class_name in class_names:
    print(f"{class_name}: {images_per_class[class_name]} images, {instances_per_class[class_name]} instances")