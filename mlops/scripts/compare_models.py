import mlflow
import argparse
import os

#def compare_and_decide(new_run_id, model_name):
def compare_and_promote(new_run_id, model_name):
    """
    Compare la performance d'un nouveau modèle (new_run_id) avec le modèle
    actuellement en production dans le MLflow Model Registry.
    """
    print(f"--- Model Comparison ---")
    print(f"Model Name in Registry: {model_name}")
    print(f"New Run ID to evaluate: {new_run_id}")

    # Configurer le client MLflow pour qu'il pointe vers le tracking server local
    # Dans GitHub Actions, le dossier mlruns sera dans le répertoire de travail.
    mlflow.set_tracking_uri("file://" + os.path.abspath("./mlruns"))
    client = mlflow.tracking.MlflowClient()

    # --- 1. Obtenir la performance du NOUVEAU modèle ---
    try:
        new_run = client.get_run(new_run_id)
        new_metric = new_run.data.metrics.get("mAP50-95")
        if new_metric is None:
            raise ValueError("Metric 'mAP50-95' not found in the new run.")
        print(f"New model mAP50-95: {new_metric:.4f}")
    except Exception as e:
        print(f"Error getting new run's metric: {e}")
        return "false" # En cas d'erreur, on ne déploie pas

    # --- 2. Obtenir la performance du modèle en PRODUCTION ---
    try:
        production_model_versions = client.get_latest_versions(name=model_name, stages=["Production"])
        if not production_model_versions:
            print("No model found in 'Production' stage. Approving the new model by default.")
            return "true" # Si rien n'est en prod, le nouveau est forcément meilleur

        production_model_run_id = production_model_versions[0].run_id
        production_run = client.get_run(production_model_run_id)
        production_metric = production_run.data.metrics.get("mAP50-95")
        if production_metric is None:
            raise ValueError("Metric 'mAP50-95' not found in the production model's run.")
        print(f"Production model mAP50-95: {production_metric:.4f}")
    except Exception as e:
        print(f"Error getting production model's metric: {e}")
        return "false"

    # --- 3. Comparer et prendre une décision ---
    is_better = "false"
    # if new_metric > production_metric:
    #     print(f"Decision: New model is BETTER. (mAP {new_metric:.4f} > {production_metric:.4f})")
    #     is_better = "true"
    # else:
    #     print(f"Decision: New model is NOT better. (mAP {new_metric:.4f} <= {production_metric:.4f})")
    #     is_better = "false"
        
    # return is_better
    if new_metric > production_metric:
        print(f"Decision: New model is BETTER.")
        is_better = "true"
        
        # --- NOUVELLE ÉTAPE : Enregistrer et promouvoir le nouveau modèle ---
        print(f"Registering new model from Run ID: {new_run_id}")
        # Le chemin de l'artefact doit correspondre à celui dans train.py
        model_uri = f"runs:/{new_run_id}/best_model_pt" 
        registered_model = mlflow.register_model(model_uri, model_name)
        
        print(f"New model registered as Version: {registered_model.version}")
        print("Promoting new version to 'Staging'...")
        
        # Attendre un peu que le modèle soit bien enregistré
        import time
        time.sleep(5)
        
        client.transition_model_version_stage(
            name=model_name,
            version=registered_model.version,
            stage="Staging"
        )
        print("Model promoted to 'Staging' successfully.")
        
    else:
        print(f"Decision: New model is NOT better.")
        is_better = "false"
        
    return is_better

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--run_id", required=True, help="MLflow Run ID of the newly trained model")
    parser.add_argument("--model_name", default="samurai-yolo-detector", help="Name of the model in the MLflow Registry")
    args = parser.parse_args()
    
    #is_better = compare_and_decide(args.run_id, args.model_name)
    is_better = compare_and_promote(args.run_id, args.model_name)
    
    # C'est la partie clé pour GitHub Actions
    # On écrit la sortie dans un fichier que l'étape suivante pourra lire
    with open("comparison_result.txt", "w") as f:
        f.write(is_better)