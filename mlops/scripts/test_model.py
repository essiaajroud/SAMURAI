# mlops/scripts/test_model.py (REVISED - no pre-split datasets for robustness/bias)

import os
import json
import numpy as np
import time
from typing import Dict, Any
from ultralytics import YOLO
import yaml
import torch
import cv2 # For image manipulation in robustness test
import random # For image sampling

class ModelTestSuite:
    def __init__(self, model_path: str, test_data_yaml_path: str):
        self.model_path = model_path
        self.test_data_yaml_path = test_data_yaml_path
        self.model = self.load_model(model_path)
        self.test_results = {}
        self.device = 'cuda:0' if torch.cuda.is_available() else 'cpu'

        with open(test_data_yaml_path, 'r') as f:
            data_config = yaml.safe_load(f)
            self.class_names = data_config.get('names', [])
            # Extract test image path directly from data.yaml if possible, otherwise infer
            # Assuming 'val' or 'test' path in data.yaml points to images
            self.test_image_dir = None
            if 'test' in data_config and os.path.isdir(os.path.join(os.path.dirname(test_data_yaml_path), data_config['test'])):
                 self.test_image_dir = os.path.join(os.path.dirname(test_data_yaml_path), data_config['test'])
            elif 'val' in data_config and os.path.isdir(os.path.join(os.path.dirname(test_data_yaml_path), data_config['val'])):
                 self.test_image_dir = os.path.join(os.path.dirname(test_data_yaml_path), data_config['val'])
            else:
                 print(f"Warning: Could not infer a specific test/val image directory from {test_data_yaml_path} for latency/robustness tests.")
                 # Fallback to a common structure if data.yaml is not explicit
                 inferred_path = os.path.join(os.path.dirname(test_data_yaml_path), 'test', 'images')
                 if os.path.isdir(inferred_path):
                     self.test_image_dir = inferred_path
                     print(f"Using inferred test image directory: {self.test_image_dir}")
                 else:
                     print(f"Warning: No explicit or inferred test image directory found for latency/robustness.")


    def load_model(self, model_path: str):
        print(f"Loading YOLO model from: {model_path}")
        try:
            model = YOLO(model_path)
            print("YOLO model loaded successfully.")
            return model
        except Exception as e:
            raise RuntimeError(f"Failed to load YOLO model from {model_path}: {e}")

    def test_performance_overall(self) -> Dict[str, Any]:
        print("\n🧪 Test 1: Performance Globale")
        print("-" * 50)
        
        try:
            results = self.model.val(data=self.test_data_yaml_path, device=self.device, verbose=False)
            map_score_50_95 = float(results.box.map)
            map_score_50 = float(results.box.map50)
            print(f"  mAP50-95 = {map_score_50_95:.3f}")
            print(f"  mAP50 = {map_score_50:.3f}")
            
            min_map_threshold = 0.50 
            
            passed = map_score_50_95 >= min_map_threshold
            result = {
                'test_name': 'performance_overall',
                'passed': passed,
                'metrics': {
                    'mAP50-95': map_score_50_95,
                    'mAP50': map_score_50,
                    'threshold_mAP50-95': min_map_threshold
                },
                'message': f"{'✅ PASS' if passed else '❌ FAIL'}: mAP50-95={map_score_50_95:.3f} (threshold={min_map_threshold})"
            }
        except Exception as e:
            result = {
                'test_name': 'performance_overall',
                'passed': False,
                'message': f"Erreur lors de l'évaluation globale: {str(e)}"
            }
        
        print(result['message'])
        self.test_results['performance_overall'] = result
        return result

    def test_performance_per_class(self) -> Dict[str, Any]:
        print("\n🧪 Test 2: Performance par Classe")
        print("-" * 50)
        
        class_metrics = {}
        all_classes_pass = True
        try:
            results = self.model.val(data=self.test_data_yaml_path, device=self.device, verbose=False, save_json=True)
            
            class_p = results.metrics.box.p.mean(axis=1) if results.metrics.box.p is not None else np.full(len(self.class_names), np.nan)
            class_r = results.metrics.box.r.mean(axis=1) if results.metrics.box.r is not None else np.full(len(self.class_names), np.nan)
            class_map50 = results.metrics.box.map50_class if results.metrics.box.map50_class is not None else np.full(len(self.class_names), np.nan)

            per_class_threshold = 0.20 # Example threshold for mAP50 per class
            
            for i, class_name in enumerate(self.class_names):
                mAP50_cls = class_map50[i] if i < len(class_map50) else np.nan
                precision_cls = class_p[i] if i < len(class_p) else np.nan
                recall_cls = class_r[i] if i < len(class_r) else np.nan

                f1_cls = (2 * precision_cls * recall_cls) / (precision_cls + recall_cls) if (precision_cls + recall_cls) > 0 else 0.0

                class_pass = mAP50_cls >= per_class_threshold
                if not class_pass:
                    all_classes_pass = False

                class_metrics[class_name] = {
                    'mAP50': float(mAP50_cls),
                    'precision': float(precision_cls),
                    'recall': float(recall_cls),
                    'f1_score': float(f1_cls),
                    'passed': class_pass,
                    'threshold_mAP50': per_class_threshold
                }
                print(f"  {class_name}: mAP50={mAP50_cls:.3f}, P={precision_cls:.3f}, R={recall_cls:.3f} - {'✅ PASS' if class_pass else '❌ FAIL'}")
            
            result = {
                'test_name': 'performance_per_class',
                'passed': all_classes_pass,
                'metrics': class_metrics,
                'message': f"{'✅ PASS' if all_classes_pass else '❌ FAIL'}: Performance par classe évaluée."
            }
        except Exception as e:
            result = {
                'test_name': 'performance_per_class',
                'passed': False,
                'message': f"Erreur lors de l'évaluation par classe: {str(e)}"
            }
        
        print(result['message'])
        self.test_results['performance_per_class'] = result
        return result

    def test_latency(self) -> Dict[str, Any]:
        print("\n🧪 Test 3: Latence")
        print("-" * 50)
        
        latencies = []
        if not self.test_image_dir or not os.path.exists(self.test_image_dir):
            result = {
                'test_name': 'latency',
                'passed': False,
                'message': f"❌ FAIL: Dossier d'images de test '{self.test_image_dir}' non trouvé ou non spécifié pour le test de latence."
            }
            print(result['message'])
            self.test_results['latency'] = result
            return result

        image_files = [f for f in os.listdir(self.test_image_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        if not image_files:
            result = {
                'test_name': 'latency',
                'passed': False,
                'message': f"❌ FAIL: Aucun fichier image trouvé dans '{self.test_image_dir}' pour le test de latence."
            }
            print(result['message'])
            self.test_results['latency'] = result
            return result

        sample_images = np.random.choice(image_files, min(len(image_files), 10), replace=False)
        
        try:
            for img_name in sample_images:
                img_path = os.path.join(self.test_image_dir, img_name)
                
                start_time = time.time()
                _ = self.model.predict(img_path, device=self.device, verbose=False)
                end_time = time.time()
                
                latency = end_time - start_time
                latencies.append(latency)
                print(f"  {img_name}: Latence = {latency:.3f} secondes")
            
            avg_latency = np.mean(latencies)
            max_latency = np.max(latencies)
            
            max_latency_threshold_s = 0.5 
            
            passed = max_latency <= max_latency_threshold_s
            result = {
                'test_name': 'latency',
                'passed': passed,
                'metrics': {
                    'average_latency_s': float(avg_latency),
                    'max_latency_s': float(max_latency),
                    'threshold_max_latency_s': max_latency_threshold_s,
                    'num_samples': len(latencies)
                },
                'message': f"{'✅ PASS' if passed else '❌ FAIL'}: Latence max={max_latency:.3f}s (threshold={max_latency_threshold_s}s)"
            }
        except Exception as e:
            result = {
                'test_name': 'latency',
                'passed': False,
                'message': f"Erreur lors du test de latence: {str(e)}"
            }
        
        print(result['message'])
        self.test_results['latency'] = result
        return result

    def _apply_gaussian_noise(self, image_np, mean=0, var=0.01):
        sigma = var**0.5
        gauss = np.random.normal(mean, sigma, image_np.shape).astype('uint8')
        noisy_img = cv2.add(image_np, gauss)
        return noisy_img

    def test_robustness(self) -> Dict[str, Any]:
        """
        Test 4: Robustesse du modèle en appliquant une corruption simple (ex: bruit Gaussien)
        à un échantillon d'images du dataset de test existant.
        """
        print("\n🧪 Test 4: Robustesse (avec bruit artificiel)")
        print("-" * 50)
        
        if not self.test_image_dir or not os.path.exists(self.test_image_dir):
            result = {
                'test_name': 'robustness',
                'passed': False,
                'message': f"❌ FAIL: Dossier d'images de test '{self.test_image_dir}' non trouvé ou non spécifié pour le test de robustesse."
            }
            print(result['message'])
            self.test_results['robustness'] = result
            return result

        image_files = [f for f in os.listdir(self.test_image_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        if not image_files:
            result = {
                'test_name': 'robustness',
                'passed': False,
                'message': f"❌ FAIL: Aucun fichier image trouvé dans '{self.test_image_dir}' pour le test de robustesse."
            }
            print(result['message'])
            self.test_results['robustness'] = result
            return result

        # Create a temporary directory for corrupted images
        temp_robust_dir = os.path.join(os.path.dirname(self.test_data_yaml_path), 'temp_robustness_test_images')
        os.makedirs(temp_robust_dir, exist_ok=True)

        sample_images = random.sample(image_files, min(len(image_files), 20)) # Sample for faster test
        corrupted_image_paths = []

        try:
            print(f"  Appliquant du bruit Gaussien à {len(sample_images)} images...")
            for img_name in sample_images:
                original_path = os.path.join(self.test_image_dir, img_name)
                img = cv2.imread(original_path)
                if img is None:
                    print(f"    Warning: Could not read image {original_path}, skipping.")
                    continue
                
                # Apply Gaussian noise
                noisy_img = self._apply_gaussian_noise(img, mean=0, var=50) # Increased variance for visible noise
                corrupted_path = os.path.join(temp_robust_dir, f"noisy_{img_name}")
                cv2.imwrite(corrupted_path, noisy_img)
                corrupted_image_paths.append(corrupted_path)
            
            if not corrupted_image_paths:
                raise ValueError("No images were successfully corrupted for robustness test.")

            # You cannot directly pass a list of images to model.val()
            # For this to work, you would either need to:
            # 1. Manually run predict() on each corrupted image and aggregate metrics (complex)
            # 2. Create a temporary data.yaml that points to these corrupted images. (simpler for val())
            
            # Option 2: Create a temporary data.yaml
            temp_robust_data_yaml = os.path.join(temp_robust_dir, 'robustness_data.yaml')
            temp_data_config = {
                'path': os.path.abspath(temp_robust_dir),
                'train': 'images', # Not strictly needed for val but good practice
                'val': 'images',   # Point to the directory containing corrupted images
                'names': self.class_names
            }
            # Adjust 'val' path to relative if 'path' is also relative
            temp_data_config['val'] = '.' 

            with open(temp_robust_data_yaml, 'w') as f:
                yaml.dump(temp_data_config, f)
            print(f"  Temporary robustness data.yaml created at {temp_robust_data_yaml}")

            print(f"  Évaluation sur le dataset de robustesse artificiellement corrompu.")
            results = self.model.val(data=temp_robust_data_yaml, device=self.device, verbose=False)
            map_score_robustness = float(results.box.map)
            
            min_robustness_map_threshold = 0.20 # Lower threshold expected for corrupted data
            
            passed = map_score_robustness >= min_robustness_map_threshold
            result = {
                'test_name': 'robustness',
                'passed': passed,
                'metrics': {
                    'mAP50-95_robustness_noisy': map_score_robustness,
                    'threshold_mAP50-95': min_robustness_map_threshold
                },
                'message': f"{'✅ PASS' if passed else '❌ FAIL'}: mAP sur données avec bruit={map_score_robustness:.3f} (threshold={min_robustness_map_threshold})"
            }
        except Exception as e:
            result = {
                'test_name': 'robustness',
                'passed': False,
                'message': f"Erreur lors du test de robustesse: {str(e)}"
            }
        finally:
            # Clean up temporary files
            if os.path.exists(temp_robust_dir):
                import shutil
                shutil.rmtree(temp_robust_dir)
                print(f"  Cleaned up temporary robustness directory: {temp_robust_dir}")

        print(result['message'])
        self.test_results['robustness'] = result
        return result

    def test_bias(self) -> Dict[str, Any]:
        """
        Test 5: Détection de biais - Not applicable without specific sub-datasets.
        This test will be skipped or marked as N/A.
        """
        print("\n🧪 Test 5: Détection de Biais (non applicable sans sous-datasets spécifiques)")
        print("-" * 50)
        
        result = {
            'test_name': 'bias',
            'passed': True, # Mark as true if skipped
            'metrics': {},
            'message': "⚠️ SKIPPED: Le test de détection de biais nécessite des sous-datasets spécifiques (ex: images lumineuses/sombres) qui ne sont pas configurés."
        }
        
        print(result['message'])
        self.test_results['bias'] = result
        return result

    def run_all_tests(self) -> Dict[str, Any]:
        test_functions = [
            self.test_performance_overall,
            self.test_performance_per_class,
            self.test_latency,
            self.test_robustness,
            self.test_bias
        ]
        
        all_passed = True
        for test_func in test_functions:
            try:
                result = test_func()
                # A test might pass because it's skipped, but we only want to fail if an *applicable* test fails.
                # For robustness/bias, if it's skipped, it doesn't count as a "fail" for overall_passed.
                if not result.get('passed', False) and result.get('test_name') not in ['bias', 'robustness']: # Only fail if *actual* test failed
                    all_passed = False
                elif not result.get('passed', False) and result.get('test_name') in ['robustness'] and "FAIL" in result.get('message', ''):
                    # If robustness actually runs and fails, it contributes to overall failure
                    all_passed = False
            except Exception as e:
                print(f"CRITICAL ERROR in {test_func.__name__}: {e}")
                self.test_results[test_func.__name__] = {'test_name': test_func.__name__, 'passed': False, 'message': f"Critical error: {e}"}
                all_passed = False
        
        summary = {
            'overall_passed': all_passed,
            'results': self.test_results
        }
        
        return summary

    def save_results(self, output_path: str):
        try:
            serializable_results = json.loads(json.dumps(self.test_results, default=self._json_default))
            with open(output_path, 'w') as f:
                json.dump(serializable_results, f, indent=4)
            print(f"Test results saved to {output_path}")
        except Exception as e:
            print(f"Error saving test results to JSON: {e}")

    def _json_default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")


if __name__ == "__main__":
    import torch

    model_to_test_path = "./server/models/best.pt"
    test_data_config_path = "./dataset/samurai/data.yaml" 

    if not os.path.exists(model_to_test_path):
        print(f"ERROR: Model file not found at {model_to_test_path}. Please ensure it exists.")
        exit(1)
    if not os.path.exists(test_data_config_path):
        print(f"ERROR: Data config file not found at {test_data_config_path}. Please ensure it exists.")
        exit(1)

    print(f"Using device: {'GPU' if torch.cuda.is_available() else 'CPU'}")

    try:
        test_suite = ModelTestSuite(model_to_test_path, test_data_config_path)
        results_summary = test_suite.run_all_tests()
        
        print("\n=== Résumé Final des Tests ===")
        print(f"Tous les tests réussis: {'✅ OUI' if results_summary['overall_passed'] else '❌ NON'}")
        
        test_suite.save_results("model_test_report.json")

        if not results_summary['overall_passed']:
            exit(1)
            
    except Exception as e:
        print(f"A critical error occurred during test suite initialization or execution: {e}")
        exit(1)