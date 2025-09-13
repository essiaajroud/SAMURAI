"""
mlops/scripts/detect_data_drift.py
Script pour détecter la dérive des données en comparant les nouvelles images avec le dataset d'entraînement
"""

import numpy as np
import cv2
import os
import json
from pathlib import Path
from datetime import datetime
import mlflow
from evidently import ColumnMapping
from evidently.report import Report
from evidently.metric_preset import DataDriftPreset, DataQualityPreset
from evidently.metrics import *
import torch
from torchvision import transforms
from PIL import Image
import yaml
import warnings
warnings.filterwarnings('ignore')

class DataDriftDetector:
    def __init__(self, reference_data_path, model_run_id=None):
        """
        Initialise le détecteur de dérive
        
        Args:
            reference_data_path: Chemin vers le dataset de référence (training)
            model_run_id: ID du run MLflow du modèle en production
        """
        self.reference_data_path = reference_data_path
        self.model_run_id = model_run_id
        self.reference_features = None
        self.drift_threshold = 0.3  # Seuil de dérive
        
        # Charger la configuration du dataset
        with open(os.path.join(reference_data_path, 'data.yaml'), 'r') as f:
            self.data_config = yaml.safe_load(f)
        
        # Extracteur de features pour les images
        self.transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], 
                               std=[0.229, 0.224, 0.225])
        ])
        
    def extract_image_features(self, image_paths):
        """
        Extrait des caractéristiques statistiques des images
        """
        features = []
        
        for img_path in image_paths:
            img = cv2.imread(str(img_path))
            if img is None:
                continue
                
            # Caractéristiques basiques
            height, width, channels = img.shape
            
            # Statistiques par canal (BGR)
            b_mean, g_mean, r_mean = img[:,:,0].mean(), img[:,:,1].mean(), img[:,:,2].mean()
            b_std, g_std, r_std = img[:,:,0].std(), img[:,:,1].std(), img[:,:,2].std()
            
            # Luminosité moyenne (conversion en grayscale)
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            brightness = gray.mean()
            contrast = gray.std()
            
            # Histogramme de luminosité
            hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
            hist = hist.flatten() / hist.sum()
            
            # Détection de flou (variance du Laplacien)
            laplacian = cv2.Laplacian(gray, cv2.CV_64F)
            blur_score = laplacian.var()
            
            # Détection de bruit (high-frequency content)
            noise_score = np.std(img - cv2.GaussianBlur(img, (5,5), 0))
            
            feature_dict = {
                'width': width,
                'height': height,
                'aspect_ratio': width / height,
                'brightness': brightness,
                'contrast': contrast,
                'r_mean': r_mean,
                'g_mean': g_mean,
                'b_mean': b_mean,
                'r_std': r_std,
                'g_std': g_std,
                'b_std': b_std,
                'blur_score': blur_score,
                'noise_score': noise_score,
                'histogram_entropy': -np.sum(hist * np.log2(hist + 1e-10))
            }
            
            features.append(feature_dict)
            
        return features
    
    def load_reference_features(self):
        """
        Charge ou calcule les features du dataset de référence
        """
        cache_path = Path(self.reference_data_path) / 'reference_features.npy'
        
        if cache_path.exists():
            print("Loading cached reference features...")
            self.reference_features = np.load(cache_path, allow_pickle=True)
        else:
            print("Computing reference features...")
            # Collecter toutes les images du dataset de référence
            train_images = []
            train_path = Path(self.reference_data_path) / 'images' / 'train'
            
            for img_file in train_path.glob('*.jpg'):
                train_images.append(img_file)
            for img_file in train_path.glob('*.png'):
                train_images.append(img_file)
            
            # Limiter à un échantillon représentatif pour la performance
            if len(train_images) > 1000:
                import random
                train_images = random.sample(train_images, 1000)
            
            self.reference_features = self.extract_image_features(train_images)
            
            # Sauvegarder en cache
            np.save(cache_path, self.reference_features)
            
        print(f"Reference features loaded: {len(self.reference_features)} samples")
        
    def detect_drift(self, current_data_path, output_dir='drift_reports'):
        """
        Détecte la dérive entre les données de référence et les nouvelles données
        """
        # Créer le dossier de sortie
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Charger les features de référence
        if self.reference_features is None:
            self.load_reference_features()
        
        # Extraire les features des nouvelles données
        print("Extracting features from current data...")
        current_images = []
        current_path = Path(current_data_path)
        
        for img_file in current_path.glob('**/*.jpg'):
            current_images.append(img_file)
        for img_file in current_path.glob('**/*.png'):
            current_images.append(img_file)
        
        if not current_images:
            print("No images found in current data path")
            return None
            
        current_features = self.extract_image_features(current_images[:500])  # Limiter pour la performance
        
        # Convertir en DataFrames pour Evidently
        import pandas as pd
        reference_df = pd.DataFrame(self.reference_features)
        current_df = pd.DataFrame(current_features)
        
        # Générer le rapport de dérive
        print("Generating drift report...")
        drift_report = Report(metrics=[
            DataDriftPreset(),
            DatasetDriftMetric(),
            DatasetMissingValuesMetric(),
            DatasetCorrelationMetric(),
        ])
        
        drift_report.run(reference_data=reference_df, 
                        current_data=current_df)
        
        # Sauvegarder le rapport
        report_path = os.path.join(output_dir, f'drift_report_{timestamp}.html')
        drift_report.save_html(report_path)
        print(f"Drift report saved to: {report_path}")
        
        # Extraire les métriques de dérive
        drift_results = {
            'timestamp': timestamp,
            'reference_samples': len(reference_df),
            'current_samples': len(current_df),
            'features_drifted': {},
            'overall_drift_detected': False,
            'drift_score': 0.0
        }
        
        # Calculer la dérive pour chaque feature
        drifted_features = 0
        for column in reference_df.columns:
            if column in current_df.columns:
                # Test de Kolmogorov-Smirnov pour détecter la dérive
                from scipy import stats
                ks_statistic, p_value = stats.ks_2samp(
                    reference_df[column], 
                    current_df[column]
                )
                
                is_drifted = p_value < 0.05  # Seuil de significativité
                drift_results['features_drifted'][column] = {
                    'drifted': is_drifted,
                    'ks_statistic': float(ks_statistic),
                    'p_value': float(p_value)
                }
                
                if is_drifted:
                    drifted_features += 1
        
        # Calculer le score de dérive global
        drift_results['drift_score'] = drifted_features / len(reference_df.columns)
        drift_results['overall_drift_detected'] = drift_results['drift_score'] > self.drift_threshold
        
        # Logger dans MLflow si un run est actif
        if mlflow.active_run():
            mlflow.log_metric("data_drift_score", drift_results['drift_score'])
            mlflow.log_metric("features_drifted", drifted_features)
            mlflow.log_artifact(report_path)
        
        # Sauvegarder les résultats en JSON
        results_path = os.path.join(output_dir, f'drift_results_{timestamp}.json')
        with open(results_path, 'w') as f:
            json.dump(drift_results, f, indent=2)
        
        # Afficher le résumé
        print("\n" + "="*50)
        print("DRIFT DETECTION SUMMARY")
        print("="*50)
        print(f"Reference samples: {drift_results['reference_samples']}")
        print(f"Current samples: {drift_results['current_samples']}")
        print(f"Drift score: {drift_results['drift_score']:.2%}")
        print(f"Features drifted: {drifted_features}/{len(reference_df.columns)}")
        print(f"Overall drift detected: {'YES ⚠️' if drift_results['overall_drift_detected'] else 'NO ✅'}")
        
        if drift_results['overall_drift_detected']:
            print("\n⚠️ ALERTE: Dérive significative détectée!")
            print("Les features suivantes ont dérivé:")
            for feature, info in drift_results['features_drifted'].items():
                if info['drifted']:
                    print(f"  - {feature}: p-value={info['p_value']:.4f}")
            print("\n👉 Recommandation: Envisagez de ré-entraîner le modèle avec les nouvelles données")
        
        return drift_results
    
    def monitor_continuous(self, monitoring_dir, check_interval_hours=24):
        """
        Surveillance continue de la dérive (à intégrer dans un cron job)
        """
        print(f"Starting continuous drift monitoring every {check_interval_hours} hours...")
        
        while True:
            try:
                # Vérifier les nouvelles données
                results = self.detect_drift(monitoring_dir)
                
                if results and results['overall_drift_detected']:
                    # Déclencher une alerte (email, Slack, etc.)
                    self.send_alert(results)
                    
                    # Optionnel: déclencher automatiquement un ré-entraînement
                    if results['drift_score'] > 0.5:  # Dérive sévère
                        print("Severe drift detected! Triggering retraining...")
                        self.trigger_retraining()
                
                # Attendre avant la prochaine vérification
                import time
                time.sleep(check_interval_hours * 3600)
                
            except Exception as e:
                print(f"Error in monitoring: {e}")
                import time
                time.sleep(3600)  # Attendre 1h en cas d'erreur
    
    def send_alert(self, drift_results):
        """
        Envoie une alerte en cas de dérive détectée
        """
        # Exemple d'intégration Slack ou email
        alert_message = f"""
        🚨 DATA DRIFT ALERT 🚨
        
        Drift Score: {drift_results['drift_score']:.2%}
        Features Affected: {sum(1 for f in drift_results['features_drifted'].values() if f['drifted'])}
        Timestamp: {drift_results['timestamp']}
        
        Action Required: Review the drift report and consider model retraining.
        """
        
        print(alert_message)
        
        # TODO: Implémenter l'envoi réel (Slack, email, etc.)
        # import requests
        # requests.post(SLACK_WEBHOOK_URL, json={'text': alert_message})
    
    def trigger_retraining(self):
        """
        Déclenche automatiquement un ré-entraînement via Jenkins
        """
        # TODO: Implémenter le déclenchement Jenkins
        print("Triggering Jenkins job for model retraining...")
        # import requests
        # requests.post(f"{JENKINS_URL}/job/{JOB_NAME}/build", auth=(USER, TOKEN))


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Detect data drift in production")
    parser.add_argument('--reference', type=str, required=True, 
                       help='Path to reference dataset (training data)')
    parser.add_argument('--current', type=str, required=True,
                       help='Path to current/production data')
    parser.add_argument('--output', type=str, default='drift_reports',
                       help='Output directory for reports')
    parser.add_argument('--threshold', type=float, default=0.3,
                       help='Drift threshold (0-1)')
    parser.add_argument('--monitor', action='store_true',
                       help='Enable continuous monitoring')
    
    args = parser.parse_args()
    
    detector = DataDriftDetector(args.reference)
    detector.drift_threshold = args.threshold
    
    if args.monitor:
        detector.monitor_continuous(args.current)
    else:
        detector.detect_drift(args.current, args.output)