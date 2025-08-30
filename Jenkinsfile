pipeline {
    agent {
        docker {
            image 'python:3.11-slim'
            args '-u root --entrypoint="" --network=host'
        }
    }

    stages {
        stage('Setup Workspace') {
            steps {
                echo 'Cleaning workspace and checking out code...'
                cleanWs()
                
                sh 'git clone https://github.com/essiaajroud/SAMURAI.git .'
                sh 'git checkout main' 
            }
        }

        stage('Install Dependencies') {
            steps {
                echo 'Installing OS and Python dependencies...'
                sh 'apt-get update && apt-get install -y libgl1 libglib2.0-0 git'
                sh 'pip install --upgrade pip'
                sh 'pip install torch==2.1.2 torchvision==0.16.2 torchaudio==2.1.2 --index-url https://download.pytorch.org/whl/cu121'
                sh 'pip install -r requirements-ci.txt'
            }
        }

        stage('Pull Data') {
            steps {
                echo 'Pulling data from DVC remote...'
                
                withCredentials([string(credentialsId: 'azure-storage-connection-string', variable: 'AZURE_CONN_STR')]) {
                    sh 'AZURE_STORAGE_CONNECTION_STRING=$AZURE_CONN_STR dvc pull -r myremote'
                }
            }
        }

        stage('Train and Evaluate') {
            steps {
                echo 'Running model training and comparison...'
               
                sh '''
                    #!/bin/bash
                    set -e # Arrêter le script si une commande échoue

                    echo "--- Running model training script ---"
                    python mlops/scripts/train.py --epochs 10 --batch 8 --data dataset/samurai/data.yaml --model server/models/best.pt --device cpu > training_output.log
                    
                    echo "--- Comparing new model with production ---"
                    RUN_ID=$(grep 'MLflow Run ID:' training_output.log | sed 's/.*MLflow Run ID: //')
                    
                    if [ -z "$RUN_ID" ]; then
                        echo "ERROR: Could not find MLflow Run ID in logs."
                        exit 1
                    fi
                    
                    echo "Found MLflow Run ID: $RUN_ID"
                    python mlops/scripts/compare_models.py --run_id $RUN_ID
                    
                    IS_BETTER=$(cat comparison_result.txt)
                    
                    if [ "$IS_BETTER" = "true" ]; then
                        echo "🚀 DEPLOYMENT SCRIPT WOULD RUN HERE! 🚀"
                        # python mlops/scripts/deploy.py --run_id $RUN_ID
                    else
                        echo "🛑 Deployment skipped. New model is not better than production."
                    fi
                '''
            }
        }
    }

    post {
        always {
            steps {
                echo 'Archiving MLflow results and logs...'
                archiveArtifacts artifacts: 'mlruns/**, training_output.log, comparison_result.txt', followSymlinks: false, allowEmptyArchive: true
            }
        }
    } 
} 