import mlflow
from ultralytics import YOLO
import argparse
import os
import yaml
import torch

def train(args):
    """
    Fonction pour entraîner un modèle YOLO avec des paramètres d'augmentation contrôlables,
    et suivre l'expérience complète avec MLflow.
    """
    epochs = args.epochs
    batch_size = args.batch
    data_yaml_path = args.data
    model_path_arg = args.model
    device = args.device if args.device else None
    print(f"Requested device: {args.device}. Effective device will be auto-selected by Ultralytics.")
    # --- 1. Validation des Chemins (plus de validation de device ici) ---
    print("--- Step 1: Validating input paths ---")
    if not os.path.exists(data_yaml_path):
        print(f"[ERROR] Data config file not found at: {data_yaml_path}")
        return
    # # Si le chemin du modèle de base ne se termine pas par .pt, on l'ajoute.
    # # Cela permet de passer soit 'yolov8s' soit 'path/to/model.pt'.
    # if not model_path_arg.endswith('.pt'):
    #     model_path_arg += '.pt'

    # Vérifier si le modèle de base existe (s'il s'agit d'un chemin local)
    if not os.path.exists(model_path_arg) and model_path_arg not in ['yolov11n.pt', 'yolov11s.pt', 'yolov11m.pt', 'yolov11l.pt', 'yolov11x.pt']:
        print(f"[ERROR] Base model not found at: {model_path_arg}")
        print("Please make sure the file exists or specify a valid official model name (e.g., 'yolov11m').")
        return
    print(f"Inputs validated. Using data from '{data_yaml_path}' and base model '{model_path_arg}'.")

    # --- 2. Configuration de MLflow ---
    print("\n--- Step 2: Configuring MLflow ---")
    MLFLOW_TRACKING_URI = "file://" + os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'mlruns'))# Correction pour la compatibilité MLflow sur Windows
    abs_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'mlruns'))
    MLFLOW_TRACKING_URI = "file:///" + abs_path.replace("\\", "/")
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    
    experiment_name = "YOLOv11_Military_Detection"
    mlflow.set_experiment(experiment_name)
    print(f"MLflow tracking URI set to: {MLFLOW_TRACKING_URI}")
    print(f"MLflow experiment set to: {experiment_name}")

    with mlflow.start_run() as run:
        run_id = run.info.run_id
        print(f"MLflow Run ID: {run_id}")
        
        # Créer un nom de run descriptif pour l'interface MLflow
        run_name = f"{os.path.basename(model_path_arg).replace('.pt','')} e{epochs} b{batch_size} aug"
        mlflow.set_tag("mlflow.runName", run_name)

        # --- 3. Log des Paramètres ---
        print("\n--- Step 3: Logging parameters to MLflow ---")
        params_to_log = {
            "base_model": model_path_arg,
            "epochs": epochs,
            "batch_size": batch_size,
            "image_size": 640,
            "device": device,
            "learning_rate": args.lr0,
            "data_yaml_path": data_yaml_path,
            "aug_degrees": args.degrees,
            "aug_translate": args.translate,
            "aug_scale": args.scale,
            "aug_flipud": args.flipud,
            "aug_mosaic": args.mosaic
        }
        mlflow.log_params(params_to_log)
        
        with open(data_yaml_path, 'r') as f:
            data_config = yaml.safe_load(f)
            mlflow.log_param("dataset_classes", data_config.get('names', []))
        print("Parameters logged successfully.")

        # --- 4. Entraînement du Modèle ---
        print("\n--- Step 4: Starting model training ---")
        try:
            model = YOLO(model_path_arg) 

            # On lance l'entraînement
            results = model.train(
                data=data_yaml_path,
                epochs=epochs,
                imgsz=640,
                batch=batch_size,
                device=device,
                lr0=args.lr0,
                name=f'{os.path.basename(model_path_arg).replace(".pt","")}_run_{run_id}',
                degrees=args.degrees,
                translate=args.translate,
                scale=args.scale,
                flipud=args.flipud,
                mosaic=args.mosaic,
                val=True,
                workers=args.workers
            )
            print("Training finished successfully.")

        except Exception as e:
             print(f"\nFATAL ERROR: An exception occurred during the training process.")
             import traceback
             traceback.print_exc()
             import sys
             sys.exit(1)

        # --- 5. Log des Métriques ---
        print("\n--- Step 5: Logging performance metrics ---")

        # --- AJOUT DE DÉBOGAGE ---
        # Affichez le contenu de l'objet results pour voir ce qui est disponible
        print(f"DEBUG: Type of results object: {type(results)}")
        # Affichez les clés disponibles dans les métriques, si elles existent
        if hasattr(results, 'metrics') and results.metrics:
            print(f"DEBUG: Available metrics keys: {results.metrics.keys()}")
        else:
            print("DEBUG: results.metrics is empty or does not exist.")
        # --- FIN DU DÉBOGAGE ---

        # --- AJOUT DE ROBUSTESSE ---
        # Vérifiez que l'objet metrics et l'attribut box existent avant d'y accéder
        if hasattr(results, 'metrics') and results.metrics and hasattr(results.metrics, 'box'):
            final_map50_95 = results.metrics.box.map    
            final_map50 = results.metrics.box.map50
            
            mlflow.log_metrics({
                "mAP50-95": final_map50_95,
                "mAP50": final_map50,
            })
            print(f"Metrics logged: mAP50-95={final_map50_95:.4f}, mAP50={final_map50:.4f}")
        else:
            print("[WARNING] No validation metrics found in results. Skipping metrics logging.")
            print("[INFO] This usually happens if the validation dataset is empty or not configured correctly in data.yaml.")
            # On pourrait décider de ne pas faire échouer le script ici, 
            # car l'entraînement a réussi. C'est un choix de conception.
            # Pour l'instant, on continue pour que le reste du script s'exécute.

        # --- 6. Log des Artefacts ---
        print("\n--- Step 6: Logging artifacts (models and charts) ---")
        model_output_path = results.save_dir
        
        mlflow.log_artifacts(model_output_path, artifact_path="yolo_training_output")
        print(f"Logged all training outputs from: {model_output_path}")
        
        best_pt_model_path = os.path.join(model_output_path, 'weights', 'best.pt')
        if os.path.exists(best_pt_model_path):
            print(f"Best model found at: {best_pt_model_path}")
            mlflow.log_artifact(best_pt_model_path, artifact_path="best_model_pt")

            print("Exporting model to ONNX format for deployment...")
            model_to_export = YOLO(best_pt_model_path)
            onnx_path = model_to_export.export(format='onnx', imgsz=640, opset=12) # Spécifier imgsz et opset est une bonne pratique
            print(f"Model successfully exported to: {onnx_path}")
            mlflow.log_artifact(onnx_path, artifact_path="best_model_onnx")
        else:
            print(f"[WARNING] 'best.pt' file not found. The best model could not be logged or exported.")

        print(f"\n✅ Run '{run_name}' (ID: {run_id}) finished successfully.")
        print(f"Final mAP50-95: {final_map50_95:.4f}")
        print("To view the results, run 'mlflow ui' in a separate terminal.")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Train YOLO model with MLflow tracking and data augmentation.")
    
    # Arguments d'entraînement
    parser.add_argument('--epochs', type=int, default=50, help='Number of training epochs.')
    parser.add_argument('--batch', type=int, default=8, help='Batch size for training.')
    parser.add_argument('--data', type=str, required=True, help='Path to the data.yaml file.')
    parser.add_argument('--model', type=str, default='yolov11n', help='Base YOLO model: name (e.g., yolov11m) or path to a local .pt file.')
    parser.add_argument('--lr', type=float, default=0.01, dest='lr0', help='Initial learning rate (e.g., 0.01).')
    parser.add_argument('--device', type=str, default='cuda:0', help="Device to run on, e.g., 'cpu' or 'cuda:0'")
    # Arguments d'augmentation de données
    parser.add_argument('--degrees', type=float, default=0.0, help='Image rotation (+/- degrees).')
    parser.add_argument('--translate', type=float, default=0.1, help='Image translation (+/- fraction).')
    parser.add_argument('--scale', type=float, default=0.5, help='Image scale (+/- gain).')
    parser.add_argument('--flipud', type=float, default=0.0, help='Image flip up-down (probability).')
    parser.add_argument('--mosaic', type=float, default=1.0, help='Use mosaic data augmentation (probability).')

    parser.add_argument('--workers', type=int, default=4, help='nombre de workers pour le chargement des données')
    
    args = parser.parse_args()
    
    # Passer l'objet 'args' en entier pour que la fonction ait accès aux paramètres d'augmentation
    train(args)