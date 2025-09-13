import os
import shutil

def read_annotation_id(annotation_path):
    """
    Lit l'ID de classe dans un fichier d'annotation YOLO (.txt).
    Retourne l'ID si trouvé, None sinon.
    """
    try:
        with open(annotation_path, 'r') as f:
            for line in f:
                if line.strip():  # Ignorer les lignes vides
                    class_id = line.split()[0]  # L'ID est la première colonne
                    return class_id
        return None
    except Exception as e:
        print(f"Erreur lors de la lecture de {annotation_path}: {e}")
        return None

def copy_data_for_id(source_img_dir, source_labels_dir, dest_dir, target_id):
    """
    Copie les images et annotations avec l'ID cible dans les annotations.
    
    :param source_img_dir: Répertoire source des images
    :param source_labels_dir: Répertoire source des annotations
    :param dest_dir: Répertoire destination pour les fichiers copiés
    :param target_id: ID à filtrer (ex. '3')
    """
    # Créer les sous-répertoires de destination
    dest_img_dir = os.path.join(dest_dir, "images")
    dest_labels_dir = os.path.join(dest_dir, "labels")
    os.makedirs(dest_img_dir, exist_ok=True)
    os.makedirs(dest_labels_dir, exist_ok=True)

    # Parcourir les fichiers d'annotations
    for label_filename in os.listdir(source_labels_dir):
        src_label_path = os.path.join(source_labels_dir, label_filename)
        
        # Vérifier si le fichier est une annotation valide
        if os.path.isfile(src_label_path) and label_filename.endswith('.txt'):
            # Lire l'ID dans l'annotation
            class_id = read_annotation_id(src_label_path)
            
            # Si l'ID correspond à target_id
            if class_id == str(target_id):
                # Trouver l'image correspondante
                base_filename = os.path.splitext(label_filename)[0]
                img_filename = base_filename + ".jpg"  # Supposons extension .jpg
                src_img_path = os.path.join(source_img_dir, img_filename)
                dst_img_path = os.path.join(dest_img_dir, img_filename)
                dst_label_path = os.path.join(dest_labels_dir, label_filename)
                
                # Copier l'image si elle existe
                if os.path.isfile(src_img_path):
                    shutil.copy2(src_img_path, dst_img_path)
                    print(f"Copié image: {src_img_path} -> {dst_img_path}")
                else:
                    print(f"Image non trouvée: {src_img_path}")
                
                # Copier l'annotation
                shutil.copy2(src_label_path, dst_label_path)
                print(f"Copié annotation: {src_label_path} -> {dst_label_path}")

def delete_data_for_id(dest_dir, delete_id):
    """
    Supprime les images et annotations avec l'ID spécifié dans le répertoire de destination.
    
    :param dest_dir: Répertoire destination
    :param delete_id: ID à supprimer (ex. '0')
    """
    dest_labels_dir = os.path.join(dest_dir, "labels")
    dest_img_dir = os.path.join(dest_dir, "images")
    
    if not os.path.exists(dest_labels_dir):
        print(f"Le répertoire {dest_labels_dir} n'existe pas.")
        return

    # Parcourir les fichiers d'annotations dans le répertoire destination
    for label_filename in os.listdir(dest_labels_dir):
        label_path = os.path.join(dest_labels_dir, label_filename)
        
        if os.path.isfile(label_path) and label_filename.endswith('.txt'):
            class_id = read_annotation_id(label_path)
            
            # Si l'ID correspond à delete_id
            if class_id == str(delete_id):
                # Supprimer l'annotation
                try:
                    os.remove(label_path)
                    print(f"Supprimé annotation: {label_path}")
                except Exception as e:
                    print(f"Erreur lors de la suppression de {label_path}: {e}")
                
                # Supprimer l'image correspondante
                base_filename = os.path.splitext(label_filename)[0]
                img_filename = base_filename + ".jpg"
                img_path = os.path.join(dest_img_dir, img_filename)
                if os.path.isfile(img_path):
                    try:
                        os.remove(img_path)
                        print(f"Supprimé image: {img_path}")
                    except Exception as e:
                        print(f"Erreur lors de la suppression de {img_path}: {e}")

def main():
    # Chemins des répertoires
    #source_img_dir = "D:/samurai/valid/images"
    #source_labels_dir = "D:/data collection/Military vehicles object detection.v16i.yolov8/valid/labels_modified"
    dest_dir = "D:/samurai/test"
    #target_id = "6"  # ID à copier
    delete_id = "7"  # ID à supprimer

    # Copier les données pour l'ID 3
    #copy_data_for_id(source_img_dir, source_labels_dir, dest_dir, target_id)
    
    # Supprimer les données pour l'ID 0 dans le répertoire destination
    delete_data_for_id(dest_dir, delete_id)
    
    print("Opérations terminées.")

if __name__ == "__main__":
    main()