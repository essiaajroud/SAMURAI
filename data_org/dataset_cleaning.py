import os
import shutil
from PIL import Image

def verify_and_fix_dataset_structure(base_path, split='train'):
    """
    Vérifie et corrige la structure du dataset pour le split donné (train, val, test).
    - Déplace les fichiers .txt du dossier images vers le dossier labels.
    - Déplace les fichiers image (.jpg, .png, etc.) du dossier labels vers le dossier images.
    - Supprime les fichiers non pertinents (par exemple, ni image ni .txt).
    
    Args:
        base_path (str): Chemin de base du dataset (ex: '/kaggle/input/detection/dataset').
        split (str): Split du dataset ('train', 'val', 'test').
    """
    image_folder = os.path.join(base_path, split, 'images')
    label_folder = os.path.join(base_path, split, 'labels')


    # Extensions valides pour les images
    image_extensions = ('.jpg', '.jpeg', '.png', '.bmp')

    # 1. Vérifier le dossier images
    for file in os.listdir(image_folder):
        file_path = os.path.join(image_folder, file)
        if file.lower().endswith('.txt'):
            # Déplacer les fichiers .txt vers le dossier labels
            dst_path = os.path.join(label_folder, file)
            print(f"Déplacement de {file_path} vers {dst_path}")
            shutil.move(file_path, dst_path)
        elif not file.lower().endswith(image_extensions):
            # Supprimer les fichiers non pertinents
            print(f"Suppression de fichier non pertinent dans images : {file_path}")
            os.remove(file_path)

    # 2. Vérifier le dossier labels
    for file in os.listdir(label_folder):
        file_path = os.path.join(label_folder, file)
        if file.lower().endswith(image_extensions):
            # Déplacer les fichiers image vers le dossier images
            dst_path = os.path.join(image_folder, file)
            print(f"Déplacement de {file_path} vers {dst_path}")
            shutil.move(file_path, dst_path)
        elif not file.lower().endswith('.txt'):
            # Supprimer les fichiers non pertinents
            print(f"Suppression de fichier non pertinent dans labels : {file_path}")
            os.remove(file_path)

def check_images_and_labels(image_folder, label_folder):
    """
    Vérifie l'intégrité des images et des annotations :
    - Vérifie que chaque image a un fichier .txt correspondant et vice versa.
    - Vérifie que les images ne sont pas corrompues.
    - Vérifie que les annotations sont valides (format YOLO, valeurs normalisées).
    - Supprime les fichiers orphelins (image sans .txt ou .txt sans image).
    
    Args:
        image_folder (str): Chemin vers le dossier des images.
        label_folder (str): Chemin vers le dossier des annotations.
    """
    image_extensions = ('.jpg', '.jpeg', '.png', '.bmp')

    # Lister les fichiers dans les deux dossiers
    image_files = {os.path.splitext(f)[0] for f in os.listdir(image_folder) if f.lower().endswith(image_extensions)}
    label_files = {os.path.splitext(f)[0] for f in os.listdir(label_folder) if f.lower().endswith('.txt')}

    # 1. Vérifier les fichiers orphelins
    # Images sans annotation
    for img_base in image_files - label_files:
        img_path = os.path.join(image_folder, img_base + next(ext for ext in image_extensions if os.path.exists(os.path.join(image_folder, img_base + ext))))
        print(f"Suppression d'image sans annotation : {img_path}")
        os.remove(img_path)

    # Annotations sans image
    for label_base in label_files - image_files:
        label_path = os.path.join(label_folder, label_base + '.txt')
        print(f"Suppression d'annotation sans image : {label_path}")
        os.remove(label_path)

    # 2. Vérifier les images et annotations restantes
    for img_base in image_files & label_files:  # Intersection : fichiers ayant à la fois une image et une annotation
        img_path = os.path.join(image_folder, img_base + next(ext for ext in image_extensions if os.path.exists(os.path.join(image_folder, img_base + ext))))
        label_path = os.path.join(label_folder, img_base + '.txt')

        # Vérifier l'image
        try:
            img = Image.open(img_path)
            img.verify()
        except Exception as e:
            print(f"Image corrompue, suppression : {img_path}, erreur : {e}")
            os.remove(img_path)
            os.remove(label_path)  # Supprimer aussi l'annotation correspondante
            continue

        # Vérifier l'annotation
        try:
            with open(label_path, 'r') as f:
                lines = f.readlines()
                if not lines:  # Fichier vide
                    print(f"Annotation vide, suppression : {label_path} et {img_path}")
                    os.remove(label_path)
                    os.remove(img_path)
                    continue
                for line in lines:
                    parts = line.strip().split()
                    if len(parts) != 5:  # Format YOLO : class_id x_center y_center width height
                        raise ValueError(f"Format invalide : {line}")
                    class_id, x, y, w, h = map(float, parts)
                    if not (0 <= x <= 1 and 0 <= y <= 1 and 0 <= w <= 1 and 0 <= h <= 1):
                        raise ValueError(f"Valeurs hors limites : {line}")
        except Exception as e:
            print(f"Annotation invalide, suppression : {label_path} et {img_path}, erreur : {e}")
            os.remove(label_path)
            os.remove(img_path)

def clean_dataset(base_path):
    """
    Nettoie le dataset pour tous les splits (train, val, test).
    
    Args:
        base_path (str): Chemin de base du dataset .
    """
    for split in ['train', 'valid', 'test']:
        print(f"\n--- Nettoyage du split : {split} ---")
        # Vérifier et corriger la structure
        verify_and_fix_dataset_structure(base_path, split)
        # Vérifier l'intégrité des images et annotations
        image_folder = os.path.join(base_path, split, 'images')
        label_folder = os.path.join(base_path, split, 'labels')
        check_images_and_labels(image_folder, label_folder)
        print(f"Nettoyage terminé pour {split}.")

# Exemple d'utilisation
base_path = 'D:/samurai'
clean_dataset(base_path)