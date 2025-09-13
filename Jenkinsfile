pipeline {
    agent {
        docker {
            // Utiliser une image avec CUDA pour le GPU
            image 'nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04'
            args '''
                --user root 
                --gpus all 
                --shm-size=8g 
                --entrypoint=""
            '''
            // Alternative si vous n'avez pas de GPU : gardez python:3.11 mais optimisez les paramètres
        }
    }

    environment {
        AZURE_STORAGE_CONNECTION_STRING = credentials('azure-storage-connection-string')
        DVC_REMOTE_URL = 'your-dvc-remote-url-if-needed'
        // Forcer l'utilisation du GPU si disponible
        CUDA_VISIBLE_DEVICES = '0'
    }

    stages {
        stage('Prepare Workspace') {
            steps {
                echo 'Cleaning workspace...'
                cleanWs()

                echo 'Installing Git and Python...'
                sh '''
                    apt-get update && apt-get install -y \
                        git \
                        python3 \
                        python3-pip \
                        libgl1 \
                        libglib2.0-0
                '''
                
                echo 'Cloning repository...'
                sh '''
                    git clone https://github.com/essiaajroud/SAMURAI.git .
                    git checkout main
                '''
            }
        }

        stage('Check GPU Availability') {
            steps {
                echo 'Checking hardware configuration...'
                sh '''
                    echo "=== GPU Check ==="
                    nvidia-smi || echo "No GPU detected - will use CPU"
                    
                    echo "=== CPU Info ==="
                    lscpu | grep -E "^CPU\\(s\\):|Model name:"
                    
                    echo "=== Memory Info ==="
                    free -h
                '''
            }
        }

        stage('Install Dependencies') {
            steps {
                echo 'Installing Python packages...'
                sh '''
                    python3 -m pip install --upgrade pip
                    
                    # Détection automatique GPU/CPU pour PyTorch
                    if command -v nvidia-smi &> /dev/null && nvidia-smi &> /dev/null; then
                        echo "Installing PyTorch with CUDA support..."
                        pip3 install torch==2.1.2 torchvision==0.16.2 torchaudio==2.1.2 --index-url https://download.pytorch.org/whl/cu121
                    else
                        echo "Installing PyTorch CPU version..."
                        pip3 install torch==2.1.2 torchvision==0.16.2 torchaudio==2.1.2 --index-url https://download.pytorch.org/whl/cpu
                    fi
                    
                    pip3 install -r server/requirements-ci.txt
                '''
                
                echo 'Verifying PyTorch installation...'
                sh '''
                    python3 -c "
import torch
print(f'PyTorch version: {torch.__version__}')
print(f'CUDA available: {torch.cuda.is_available()}')
if torch.cuda.is_available():
    print(f'CUDA version: {torch.version.cuda}')
    print(f'GPU count: {torch.cuda.device_count()}')
    print(f'GPU name: {torch.cuda.get_device_name(0)}')
else:
    print('Running on CPU')
    "
                '''
            }
        }

        stage('Pull Data') {
            steps {
                echo 'Pulling data from DVC remote...'
                sh 'dvc pull -r myremote'
            }
        }

        stage('Train and Evaluate') {
            steps {
                echo 'Running optimized model training...'
                sh '''
                    #!/bin/bash
                    set -e

                    echo "--- Detecting optimal device ---"
                    # Détection automatique GPU/CPU
                    if python3 -c "import torch; exit(0 if torch.cuda.is_available() else 1)"; then
                        DEVICE="cuda:0"
                        BATCH_SIZE=16  # Batch plus grand avec GPU
                        echo "✅ GPU detected - using device: $DEVICE with batch size: $BATCH_SIZE"
                    else
                        DEVICE="cpu"
                        BATCH_SIZE=4   # Batch réduit pour CPU mais pas trop petit
                        echo "⚠️ No GPU - using device: $DEVICE with batch size: $BATCH_SIZE"
                        echo "WARNING: Training on CPU will be MUCH slower!"
                    fi

                    echo "--- Starting training with monitoring ---"
                    # Ajouter time pour mesurer la durée
                    time python3 mlops/scripts/train.py \
                        --epochs 2 \
                        --batch $BATCH_SIZE \
                        --data dataset/samurai/data.yaml \
                        --model server/models/best.pt \
                        --device $DEVICE \
                        --workers 4 \
                        | tee training_output.log

                    TRAIN_EXIT_CODE=${PIPESTATUS[0]}
                    
                    # Extraire les métriques de temps
                    echo "--- Training Performance Summary ---"
                    grep -E "(epoch|GPU|time|mAP)" training_output.log | tail -20
                    
                    if [ $TRAIN_EXIT_CODE -ne 0 ]; then
                        echo "ERROR: Training failed with exit code $TRAIN_EXIT_CODE"
                        exit $TRAIN_EXIT_CODE
                    fi

                    echo "--- Model comparison ---"
                    RUN_ID=$(grep 'MLflow Run ID:' training_output.log | head -1 | sed 's/.*MLflow Run ID: //')
                    
                    if [ -z "$RUN_ID" ]; then
                        echo "ERROR: Could not find MLflow Run ID"
                        exit 1
                    fi

                    echo "MLflow Run ID: $RUN_ID"
                    python3 mlops/scripts/compare_models.py --run_id "$RUN_ID" > comparison_result.txt 2>&1
                    
                    IS_BETTER=$(cat comparison_result.txt | tr -d '\n\r')
                    
                    if [ "$IS_BETTER" = "true" ]; then
                        echo "🚀 New model is better - Deployment would be triggered!"
                    else
                        echo "🛑 New model is not better - Deployment skipped"
                    fi
                '''
            }
        }

        stage('Collect Results') {
            steps {
                echo 'Collecting training results...'
                sh '''
                    echo "=== Training Results Location ==="
                    
                    # Afficher l'emplacement des modèles
                    echo "--- YOLO Models ---"
                    find . -name "*.pt" -o -name "*.onnx" | grep -E "(runs|mlruns)" | head -10
                    
                    echo "--- Training Metrics ---"
                    find . -name "results.csv" -o -name "*.png" | grep -E "(runs|mlruns)" | head -10
                    
                    # Afficher les métriques finales si disponibles
                    if [ -f training_output.log ]; then
                        echo "--- Final Metrics ---"
                        grep -E "mAP|epoch" training_output.log | tail -5
                    fi
                '''
            }
        }
    }

    post {
        always {
            echo 'Archiving artifacts...'
            archiveArtifacts artifacts: '''
                mlruns/**,
                runs/**/*.pt,
                runs/**/*.onnx,
                runs/**/*.png,
                runs/**/*.csv,
                training_output.log,
                comparison_result.txt
            ''', followSymlinks: false, allowEmptyArchive: true
            
            // Afficher un résumé
            sh '''
                if [ -f training_output.log ]; then
                    echo "=== Training Duration ==="
                    grep "real" training_output.log || echo "Duration not found"
                fi
            '''
        }
        success {
            echo '✅ Pipeline completed successfully!'
        }
        failure {
            echo '❌ Pipeline failed. Check logs for details.'
        }
    }
}