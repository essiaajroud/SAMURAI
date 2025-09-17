// Jenkinsfile - Complete MLOps Pipeline for SAMURAI Project

pipeline {
    agent {
        docker {
            // Utiliser une image avec CUDA pour le GPU
            // Cette image doit inclure CUDA, cuDNN et un environnement Python.
            // Assurez-vous qu'elle est compatible avec votre version de GPU et de PyTorch.
            image 'nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04' 
            args '''
                --user root 
                --gpus all 
                --shm-size=8g 
                --entrypoint=""
            '''
            // Alternative si vous n'avez pas de GPU :
            // image 'python:3.11-slim' 
            // args '--user root --entrypoint=""' // Pas de --gpus all
        }
    }

    environment {
        // Variables d'environnement Jenkins. Utilisez 'credentials' pour les secrets.
        AZURE_CONNECTION_STRING = credentials('azure-storage-connection-string')

        DVC_REMOTE_URL = 'azure://samuraidatastore/samurai-data'
        
        // MLflow Tracking URI local (fichier)
        MLFLOW_TRACKING_URI = "file://${workspace}/mlruns"

        // Forcer l'utilisation du GPU si disponible.
        CUDA_VISIBLE_DEVICES = '0' 
        
        // Variables pour le suivi de l'exécution du pipeline
        TRAINING_RUN_ID = '' 
        MODEL_PROMOTED_TO_STAGING = 'false' // Initialisé à 'false'

        // Chemins principaux des données
        DATA_YAML_PATH = 'dataset/samurai/data.yaml' 
        
        // Chemin pour simuler les données d'inférence en production pour la détection de dérive.
        // C'est ici que votre service de production stockerait les images traitées.
        // Pour un test, cela peut être un sous-ensemble de vos images de validation.
        PRODUCTION_INFERENCE_DATA_PATH = 'dataset/samurai/val/images' 
        
        MODEL_NAME = 'samurai-yolo-detector' // Nom de votre modèle dans le registre MLflow
    }

    stages {
        stage('Prepare Workspace') {
            steps {
                echo 'Cleaning workspace...'
                cleanWs()

                echo 'Installing OS-level dependencies (Git, Python essentials, etc.)...'
                sh '''
                    apt-get update && apt-get install -y --no-install-recommends \
                        git \
                        python3 \
                        python3-pip \
                        libgl1 \
                        libglib2.0-0 \
                        time \
                        bash \
                        curl # Added curl for potential dvc remote needs if it uses HTTPS
                    
                    ln -sf /bin/bash /bin/sh
                '''
                
                echo 'Cloning repository...'
                sh '''
                    git clone https://github.com/essiaajroud/SAMURAI.git .
                    git checkout main
                '''
            }
        }

        stage('Check Environment & GPU') {
            steps {
                echo 'Checking hardware configuration and Python environment...'
                sh '''
                    echo "=== GPU Check ==="
                   
                    if command -v nvidia-smi &> /dev/null; then
                        nvidia-smi || echo "No GPU detected or nvidia-smi failed to execute (permissions?)."
                    else
                        echo "nvidia-smi command not found. Assuming no NVIDIA GPU or drivers."
                    fi
                    
                    echo "=== CPU Info ==="
                    lscpu | grep -E "^CPU\\(s\\):|Model name:" || true # `|| true` prevents pipeline failure if command is missing
                    
                    echo "=== Memory Info ==="
                    free -h || true
                    
                    echo "=== Disk Space ==="
                    df -h . || true
                '''
            }
        }

        stage('Install Python Dependencies') {
            steps {
                echo 'Installing Python packages...'
                sh '''
                    python3 -m pip install --upgrade pip
                    
                    # Détection robuste de CUDA en se basant sur la présence de nvidia-smi
                    if command -v nvidia-smi &> /dev/null; then
                        echo "✅ nvidia-smi found. Installing PyTorch with CUDA support..."
                        # Assurez-vous que la version de cuDNN dans l'URL correspond à votre image Docker
                        # Votre image est cuda:11.8.0-cudnn8, donc cu118 serait idéal.
                        # cu121 pourrait fonctionner mais cu118 est plus sûr.
                        pip3 install torch==2.1.2 torchvision==0.16.2 torchaudio==2.1.2 --index-url https://download.pytorch.org/whl/cu118
                    else
                        echo "⚠️ nvidia-smi not found. Installing PyTorch CPU version..."
                        pip3 install torch==2.1.2 torchvision==0.16.2 torchaudio==2.1.2 --index-url https://download.pytorch.org/whl/cpu
                    fi
                    
                    # Installer les autres dépendances
                    pip3 install -r server/requirements-ci.txt
                    pip3 install evidently
                '''
                
                echo 'Verifying PyTorch installation...'
                sh 'python3 mlops/scripts/check_env.py'
            }
        }

        stage('Pull Data (DVC)') {
    steps {
        // Le bloc withCredentials est la méthode sécurisée pour manipuler des secrets.
        withCredentials([string(credentialsId: 'azure-storage-connection-string', variable: 'DVC_CONN_STRING')]) {
            // 'credentialsId': L'ID de votre secret dans Jenkins (assurez-vous qu'il correspond).
            // 'variable': Le nom de la variable d'environnement que Jenkins va créer pour nous.
            
            echo 'Configuring DVC remote and pulling data...'
            
            sh '''
                #!/bin/bash
                set -e

                # Ce commentaire est correct car il utilise '#'
                echo "Configuring DVC remote 'myremote'..."
                
                # On utilise la variable $DVC_CONN_STRING qui a été injectée de manière sécurisée.
                dvc remote modify myremote connection_string "$DVC_CONN_STRING"
                
                echo "Pulling data with DVC..."
                dvc pull -r myremote
            '''

            echo "--- Verifying DVC pull results ---"
            sh '''
                # Vérifier si le modèle de base existe
                if [ -f "server/models/best2.pt" ]; then
                    echo "✅ SUCCESS: Base model server/models/best2.pt found after dvc pull."
                else
                    echo "❌ FAILURE: Base model server/models/best2.pt NOT FOUND after dvc pull. This is the root cause of the error."
                    exit 1
                fi

                # Vérifier si le fichier de configuration des données existe
                if [ -f "${DATA_YAML_PATH}" ]; then
                    echo "✅ SUCCESS: Data YAML ${DATA_YAML_PATH} found."
                    echo "--- Contents of data.yaml: ---"
                    cat "${DATA_YAML_PATH}"
                else
                    echo "❌ FAILURE: Data YAML ${DATA_YAML_PATH} NOT FOUND."
                    exit 1
                fi
            '''
        }
        
        // Cette commande est maintenant CORRECTEMENT PLACÉE à l'intérieur du bloc 'steps'
        sh 'ls -l ${DATA_YAML_PATH} || echo "WARNING: ${DATA_YAML_PATH} not found after DVC pull!"'
    }
}

        stage('Train Model') {
            steps {
                script {
                    echo 'Running optimized model training...'
                    sh '''
                        #!/bin/bash
                        set -e 

                        echo "--- Detecting optimal device for training ---"
                        
                        if python3 -c "import torch; exit(0 if torch.cuda.is_available() else 1)"; then
                            DEVICE="cuda:0"
                            BATCH_SIZE=16  # Larger batch size for GPU
                            echo "✅ GPU detected - using device: $DEVICE with batch size: $BATCH_SIZE"
                        else
                            DEVICE="cpu"
                            BATCH_SIZE=4   # Reduced batch size for CPU
                            echo "⚠️ No GPU detected - using device: $DEVICE with batch size: $BATCH_SIZE"
                            echo "WARNING: Training on CPU will be significantly slower!"
                        fi

                        echo "--- Début du débogage des chemins ---"
                        echo "1. Répertoire de travail actuel (pwd) :"
                        pwd

                        echo "2. Contenu du répertoire de travail (ls -la) :"
                        ls -la

                        echo "3. Vérification de l'existence du chemin relatif :"
                        if [ -f "mlops/scripts/train.py" ]; then
                            echo "✅ SUCCÈS: Le fichier 'mlops/scripts/train.py' a été trouvé avec un chemin relatif."
                        else
                            echo "❌ ÉCHEC: Le fichier 'mlops/scripts/train.py' est INTROUVABLE avec un chemin relatif."
                        fi
                        echo "--- Fin du débogage ---"

                        echo "--- Starting training with MLflow logging ---"
                       
                        time python3 mlops/scripts/train.py \
                            --epochs 1 \
                            --batch $BATCH_SIZE \
                            --data ${DATA_YAML_PATH} \
                            --model server/models/best2.pt \
                            --device $DEVICE \
                            --workers 4 \
                            | tee training_output.log

                        TRAIN_EXIT_CODE=${PIPESTATUS[0]} # Get exit code of the python command

                        if [ $TRAIN_EXIT_CODE -ne 0 ]; then
                            echo "ERROR: Model training script failed with exit code $TRAIN_EXIT_CODE."
                            cat training_output.log
                            exit $TRAIN_EXIT_CODE # Fail the Jenkins stage
                        fi

                        echo "--- Extracting MLflow Run ID from training logs ---"
                        RUN_ID_FROM_LOG=$(grep 'MLflow Run ID:' training_output.log | head -1 | sed 's/.*MLflow Run ID: //')
                        
                        if [ -z "$RUN_ID_FROM_LOG" ]; then
                            echo "ERROR: Could not find MLflow Run ID in training_output.log."
                            exit 1
                        fi
                        echo "Found MLflow Run ID: $RUN_ID_FROM_LOG"
                        env.TRAINING_RUN_ID = "$RUN_ID_FROM_LOG" # Set Jenkins environment variable
                    '''
                }
            }
        }

        stage('Comprehensive Model Tests') {
            steps {
                script {
                    echo 'Running comprehensive model validation tests using mlops/scripts/test_model.py...'
                    if ("${env.TRAINING_RUN_ID}" == "") {
                        echo "ERROR: TRAINING_RUN_ID is empty. Cannot run comprehensive model tests."
                        exit 1
                    }

                    echo "--- Downloading best2.pt model artifact from MLflow Run ID: ${env.TRAINING_RUN_ID} ---"
                     //Configure MLflow client to download the model
                    sh '''
                        #!/bin/bash
                        set -e
                        export MLFLOW_TRACKING_URI="${env.MLFLOW_TRACKING_URI}"
                        
                        MLFLOW_DOWNLOAD_DIR="mlflow_model_for_test"
                        mkdir -p "\${MLFLOW_DOWNLOAD_DIR}"

                        mlflow artifacts download --run-id "${env.TRAINING_RUN_ID}" --artifact-path "best_model_pt" --dst-path "\${MLFLOW_DOWNLOAD_DIR}"
                        
                        MODEL_TO_TEST_PATH="\${MLFLOW_DOWNLOAD_DIR}/best_model_pt/best2.pt"
                        if [ ! -f "\${MODEL_TO_TEST_PATH}" ]; then
                            echo "ERROR: best2.pt model artifact not found at \${MODEL_TO_TEST_PATH} after download."
                            exit 1
                        fi
                        echo "Model downloaded for testing: \${MODEL_TO_TEST_PATH}"

                        echo "--- Executing test_model.py ---"
                        python3 mlops/scripts/test_model.py \
                            --model_path "\${MODEL_TO_TEST_PATH}" \
                            --test_data_path "${env.DATA_YAML_PATH}" \
                            | tee model_test_report.log
                        
                        TEST_SCRIPT_EXIT_CODE=${PIPESTATUS[0]}

                        if [ $TEST_SCRIPT_EXIT_CODE -ne 0 ]; then
                            echo "ERROR: Comprehensive model tests failed with exit code $TEST_SCRIPT_EXIT_CODE."
                            cat model_test_report.log
                            exit $TEST_SCRIPT_EXIT_CODE
                        fi
                        echo "✅ Comprehensive model tests PASSED."
                    '''
                    archiveArtifacts artifacts: 'model_test_report.log, model_test_report.json', followSymlinks: false, allowEmptyArchive: true
                }
            }
        }

        stage('Data Drift Detection') {
            steps {
                script {
                    echo 'Collecting production inference data and checking for drift using Evidently AI...'
                    // The `detect_data_drift.py` script will handle its own MLflow logging.
                    // It needs the path to the training data (reference) and a path to some "production-like" data.
                    // Assuming `PRODUCTION_INFERENCE_DATA_PATH` contains images.

                    sh '''
                        #!/bin/bash
                        set -e
                        export MLFLOW_TRACKING_URI="${env.MLFLOW_TRACKING_URI}"

                        python3 mlops/scripts/detect_data_drift.py \
                            --reference_data_path "${env.DATA_YAML_PATH}" \
                            --production_data_path "${env.PRODUCTION_INFERENCE_DATA_PATH}" \
                            --output_report_path "data_drift_report.html" \
                            --run_id "${env.TRAINING_RUN_ID}" \
                            | tee data_drift_output.log

                        DRIFT_EXIT_CODE=${PIPESTATUS[0]}

                        if [ $DRIFT_EXIT_CODE -ne 0 ]; then
                            echo "ERROR: Data drift detection failed with exit code $DRIFT_EXIT_CODE."
                            cat data_drift_output.log
                            # Decide if drift failure should fail the pipeline.
                            # For now, we'll just log it. You might want to 'exit $DRIFT_EXIT_CODE' here
                            # if critical drift should stop deployment.
                            # exit $DRIFT_EXIT_CODE
                        fi
                        echo "✅ Data drift detection completed. Check data_drift_report.html for details."
                    '''
                    archiveArtifacts artifacts: 'data_drift_report.html, data_drift_output.log', followSymlinks: false, allowEmptyArchive: true
                }
            }
        }

        stage('Compare & Promote to Staging') {
            steps {
                script {
                    echo 'Comparing new model with current production candidate and promoting to Staging if better...'
                    if ("${env.TRAINING_RUN_ID}" == "") {
                        echo "ERROR: TRAINING_RUN_ID is empty. Cannot compare models."
                        exit 1
                    }

                    sh '''
                        #!/bin/bash
                        set -e
                        export MLFLOW_TRACKING_URI="${env.MLFLOW_TRACKING_URI}"
                        
                        echo "--- Running compare_models.py ---"
                        python3 mlops/scripts/compare_models.py \
                            --run_id "${env.TRAINING_RUN_ID}" \
                            --model_name "${env.MODEL_NAME}" \
                            | tee comparison_result.log

                        COMPARE_EXIT_CODE=${PIPESTATUS[0]}
                        
                        if [ $COMPARE_EXIT_CODE -ne 0 ]; then
                            echo "ERROR: Model comparison script failed with exit code $COMPARE_EXIT_CODE."
                            cat comparison_result.log
                            exit $COMPARE_EXIT_CODE
                        fi
                        
                        IS_PROMOTED=$(tail -n 1 comparison_result.log | tr -d '[:space:]')
                        
                        if [ "$IS_PROMOTED" = "true" ]; then
                            echo "🚀 New model is better and PROMOTED TO STAGING! 🚀"
                            env.MODEL_PROMOTED_TO_STAGING = "true"
                        else
                            echo "🛑 Model not better or failed internal comparison criteria. Promotion to Staging skipped."
                            env.MODEL_PROMOTED_TO_STAGING = "false"
                        fi
                    '''
                    archiveArtifacts artifacts: 'comparison_result.log', followSymlinks: false, allowEmptyArchive: true
                }
            }
        }

        stage('Manual Approval for Production') {
            // This stage only runs if a model was promoted to Staging
            when { expression { return env.MODEL_PROMOTED_TO_STAGING == 'true' } }
            steps {
                timeout(time: 24, unit: 'HOURS') { // Timeout for manual approval
                    input message: "Approve Model '${env.MODEL_NAME}' (Run ID: ${env.TRAINING_RUN_ID}) deployment to Production?", ok: 'Deploy'
                }
                echo '✅ Manual approval granted for Production deployment.'
            }
        }

        stage('Deploy to Production') {
            // This stage only runs if a model was promoted to Staging AND manually approved
            when { expression { return env.MODEL_PROMOTED_TO_STAGING == 'true' } }
            steps {
                script {
                    echo "Deploying approved model '${env.MODEL_NAME}' from Staging to Production..."
                    //The `promote_and_deploy.py` script orchestrates the transition in MLflow Registry
                    // and then calls `deploy.py` to copy the ONNX model to the server directory.
                    sh '''
                        #!/bin/bash
                        set -e
                        export MLFLOW_TRACKING_URI="${env.MLFLOW_TRACKING_URI}"

                        python3 mlops/scripts/promote_and_deploy.py \
                            --model_name "${env.MODEL_NAME}" \
                            | tee promote_deploy_output.log

                        PROMOTE_DEPLOY_EXIT_CODE=${PIPESTATUS[0]}

                        if [ $PROMOTE_DEPLOY_EXIT_CODE -ne 0 ]; then
                            echo "ERROR: Production promotion/deployment failed with exit code $PROMOTE_DEPLOY_EXIT_CODE."
                            cat promote_deploy_output.log
                            exit $PROMOTE_DEPLOY_EXIT_CODE
                        fi
                        echo "✅ Model successfully promoted to Production and deployed."
                    '''
                    archiveArtifacts artifacts: 'promote_deploy_output.log', followSymlinks: false, allowEmptyArchive: true
                }
            }
        }
    }

    post {
        always {
            script {
                echo 'Archiving all relevant artifacts...'
                archiveArtifacts artifacts: '''
                    mlruns/**,
                    runs/**/*.pt,
                    runs/**/*.onnx,
                    runs/**/*.png,
                    runs/**/*.csv,
                    training_output.log,
                    comparison_result.log,
                    model_test_report.log,
                    model_test_report.json,
                    data_drift_report.html,
                    data_drift_output.log,
                    promote_deploy_output.log
                ''', followSymlinks: false, allowEmptyArchive: true
                
                echo 'Cleaning up temporary MLflow download directory if it exists...'
                sh 'rm -rf mlflow_model_for_test || true'
                
                echo '--- Pipeline Finished ---'
            }
        }
        success {
            script {
                echo '✅ Pipeline completed successfully!'
            }
        }
        failure {
            script {
                echo '❌ Pipeline failed. Check logs for details.'
            }
        }
        unstable {
            script {
                echo '⚠️ Pipeline completed with some warnings/unstable results.'
            }
        }
    }
}