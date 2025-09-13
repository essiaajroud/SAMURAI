import os

# Chemins
custom_label_dir = "D:/4"  
output_dir = "D:/4/labels_modified"  
offset = 12 

# Dictionnaire de mappage des class_id
class_id_mapping = {
    
    5: 4
}

# Créer le répertoire de sortie s'il n'existe pas
os.makedirs(output_dir, exist_ok=True)

# Parcourir les fichiers .txt
for label_file in os.listdir(custom_label_dir):
    if label_file.endswith(".txt"):
        file_path = os.path.join(custom_label_dir, label_file)
        output_file_path = os.path.join(output_dir, label_file)

        with open(file_path, "r") as f:
            lines = f.readlines()

        # Modifier les class_id
        new_lines = []
        for line in lines:
            if line.strip():  # Ignorer les lignes vides
                parts = line.strip().split()
                class_id = int(parts[0])
                
                # Mapper les class_id selon le dictionnaire
                if class_id in class_id_mapping:
                    class_id = class_id_mapping[class_id]
                
                new_line = f"{class_id} {' '.join(parts[1:])}\n"
                new_lines.append(new_line)

        # Écrire le fichier modifié dans le nouveau répertoire
        with open(output_file_path, "w") as f:
            f.writelines(new_lines)

print(f"Annotations personnalisées mises à jour et sauvegardées dans {output_dir}.")