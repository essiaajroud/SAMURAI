import mlflow
import argparse
import os
import shutil

def deploy_model(run_id):
    """
    Télécharge l'artefact du modèle depuis une 'run' MLflow et le déploie
    en le copiant dans le dossier de production du serveur.
    """
    print(f"--- Deployment Script Started ---")
    print(f"Fetching model from Run ID: {run_id}")

    # Configurer le client MLflow pour trouver le dossier mlruns local
    mlflow.set_tracking_uri("file://" + os.path.abspath("./mlruns"))
    client = mlflow.tracking.MlflowClient()

    # Définir les chemins
    destination_dir = os.path.abspath("./server/models")
    model_artifact_path = "best_model_onnx"
    
    try:
        # 1. Télécharger les artefacts du modèle
        local_path = client.download_artifacts(run_id, model_artifact_path)
        print(f"Model artifacts downloaded to: {local_path}")

        # Le fichier est à l'intérieur du dossier téléchargé
        source_model_file = os.path.join(local_path, "best.onnx")
        destination_model_file = os.path.join(destination_dir, "best.onnx")

        # 2. Vérifier que le fichier existe
        if not os.path.exists(source_model_file):
            raise FileNotFoundError(f"best.onnx not found in downloaded artifacts at {local_path}")

        # 3. Copier le nouveau modèle vers le dossier de production
        print(f"Copying {source_model_file} to {destination_model_file}")
        shutil.copy(source_model_file, destination_model_file)
        
        print(f"✅ Model successfully deployed to {destination_dir}")
        print("Backend must be restarted to use the new model.")

    except Exception as e:
        print(f"❌ Deployment failed: {e}")
        exit(1) # Quitter avec un code d'erreur pour faire échouer le build Jenkins

if __name__ == "__main__":
    # --- C'EST LE PARSER QUI MANQUAIT ---
    parser = argparse.ArgumentParser(description="Deploy a model from an MLflow run.")
    parser.add_argument("--run_id", required=True, help="MLflow Run ID of the model to deploy.")
    args = parser.parse_args()
    
    deploy_model(args.run_id)