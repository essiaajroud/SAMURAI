import os
import shutil

# Définir les chemins
dataset_dir = "D:/dataset"  
images_dir = os.path.join(dataset_dir, "train/images")  
labels_dir = os.path.join(dataset_dir, "train/labels")  
valid_images_dir = os.path.join(dataset_dir, "valid/images")
valid_labels_dir = os.path.join(dataset_dir, "valid/labels")
test_images_dir = os.path.join(dataset_dir, "test/images")
test_labels_dir = os.path.join(dataset_dir, "test/labels")

# Nouveaux répertoires pour la version modifiée
new_images_dir = os.path.join(dataset_dir, "train_new/images")
new_labels_dir = os.path.join(dataset_dir, "train_new/labels")
new_valid_images_dir = os.path.join(dataset_dir, "valid_new/images")
new_valid_labels_dir = os.path.join(dataset_dir, "valid_new/labels")
new_test_images_dir = os.path.join(dataset_dir, "test_new/images")
new_test_labels_dir = os.path.join(dataset_dir, "test_new/labels")

# Créer les nouveaux répertoires
for dir_path in [new_images_dir, new_labels_dir, new_valid_images_dir, new_valid_labels_dir, new_test_images_dir, new_test_labels_dir]:
    os.makedirs(dir_path, exist_ok=True)

# Classes à fusionner en military_aircraft (ID 2)
classes_to_merge = {2: "jet", 4: "large_mil_plane", 5: "mil_helicopter", 6: "stealth"}
new_class_id = 2  # ID pour military_aircraft

# Classes à supprimer (civ_helicopter ID 0 et Mil_drone ID 1)
class_to_remove = [0, 1]

# Fonction pour copier et traiter un fichier d'annotation
def process_label_file(original_label_path, new_label_path):
    if not os.path.exists(original_label_path):
        return False
    with open(original_label_path, 'r') as file:
        lines = file.readlines()
    updated_lines = []
    has_only_removed_classes = True  # Vérifie si toutes les instances sont à supprimer

    for line in lines:
        parts = line.strip().split()
        if not parts:
            continue
        class_id = int(parts[0])
        # Vérifier si la classe doit être supprimée
        if class_id in class_to_remove:
            continue
        has_only_removed_classes = False
        # Fusionner les classes en military_aircraft
        if class_id in classes_to_merge:
            parts[0] = str(new_class_id)
            updated_lines.append(' '.join(parts) + '\n')
        else:
            updated_lines.append(line)

    # Écrire dans le nouveau fichier si le fichier contient des classes valides
    if updated_lines or not has_only_removed_classes:
        with open(new_label_path, 'w') as file:
            file.writelines(updated_lines)
        return True
    return False

# Copier et traiter les fichiers pour chaque split
def process_split(original_images_dir, original_labels_dir, new_images_dir, new_labels_dir):
    for label_file in os.listdir(original_labels_dir):
        if label_file.endswith('.txt'):
            original_label_path = os.path.join(original_labels_dir, label_file)
            new_label_path = os.path.join(new_labels_dir, label_file)
            # Traiter l'annotation
            keep_file = process_label_file(original_label_path, new_label_path)
            if keep_file:
                # Copier l'image correspondante
                image_file = os.path.splitext(label_file)[0] + '.jpg'  # Ajustez l'extension si nécessaire
                original_image_path = os.path.join(original_images_dir, image_file)
                new_image_path = os.path.join(new_images_dir, image_file)
                if os.path.exists(original_image_path):
                    shutil.copy(original_image_path, new_image_path)

# Traiter les fichiers d'entraînement
process_split(images_dir, labels_dir, new_images_dir, new_labels_dir)

# Traiter les fichiers de validation
process_split(valid_images_dir, valid_labels_dir, new_valid_images_dir, new_valid_labels_dir)

# Traiter les fichiers de test
process_split(test_images_dir, test_labels_dir, new_test_images_dir, new_test_labels_dir)

# Mettre à jour data.yaml (manuel après exécution)
print("Ancienne version conservée dans train/, valid/, test/")
print("Nouvelle version créée dans train_new/, valid_new/, test_new/")
print("Mettez à jour data.yaml pour la nouvelle version :")
print("- Réduisez nc (nombre de classes) de 17 à 14 (suppression de civ_helicopter et Mil_drone).")
print("- Mettez à jour names pour refléter la nouvelle classe 'military_aircraft' et supprimer 'civ_helicopter' et 'Mil_drone'.")