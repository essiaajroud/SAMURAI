pipeline {
    // 1. Agent Docker pour tout le pipeline
    agent {
        docker {
            image 'python:3.11-slim'
            args '-u root --entrypoint="" --network=host'
        }
    }

    // 2. Définition des secrets
    environment {
        AZURE_STORAGE_CONNECTION_STRING = credentials('azure-storage-connection-string')
    }

    // 3. Les Étapes du Pipeline
    stages {
        // --- CORRECTION 1 : Remplacer 'checkout scm' par des commandes manuelles plus fiables ---
        stage('Prepare Workspace') {
            steps {
                echo 'Cleaning workspace...'
                cleanWs()
                
                echo 'Installing Git and checking out repository code...'
                // Installer Git D'ABORD
                sh 'apt-get update && apt-get install -y git'
                // Ensuite, clôner le dépôt
                sh 'git clone https://github.com/essiaajroud/SAMURAI.git .'
                sh 'git checkout main' // Spécifier la branche à utiliser
            }
        }

        stage('Install Dependencies') {
            steps {
                echo 'Installing OS and Python dependencies...'
                // On installe uniquement les dépendances pour OpenCV ici
                sh 'apt-get update && apt-get install -y libgl1 libglib2.0-0'
                
                echo 'Installing Python packages...'
                sh 'pip install --upgrade pip'
                sh 'pip install torch==2.1.2 torchvision==0.16.2 torchaudio==2.1.2 --index-url https://download.pytorch.org/whl/cu121'
                // On utilise le fichier requirements-ci.txt qui est plus léger
                sh 'pip install -r server/requirements-ci.txt'
            }
        }

        stage('Pull Data') {
            steps {
                echo 'Pulling data from DVC remote...'
                sh 'dvc pull -r myremote'
            }
        }

        // --- CORRECTION 2 : Combiner Train & Compare pour éviter l'erreur de sérialisation ---
        stage('Train and Evaluate') {
            steps {
                echo 'Running model training and evaluation...'
                // On exécute toute la logique dans un seul script shell
                sh '''
                    #!/bin/bash
                    set -e # Arrêter le script si une commande échoue

                    echo "--- Running model training script ---"
                    python mlops/scripts/train.py --epochs 2 --batch 2 --data dataset/samurai/data.yaml --model server/models/best.pt --device cpu > training_output.log
                    
                    echo "--- Comparing new model with production ---"
                    # Extraire l'ID du run depuis le log
                    RUN_ID=$(grep 'MLflow Run ID:' training_output.log | sed 's/.*MLflow Run ID: //')
                    
                    if [ -z "$RUN_ID" ]; then
                        echo "ERROR: Could not find MLflow Run ID in logs. Training may have failed."
                        exit 1 # Fait échouer l'étape
                    fi
                    
                    echo "Found MLflow Run ID: $RUN_ID"
                    python mlops/scripts/compare_models.py --run_id $RUN_ID
                    
                    IS_BETTER=$(cat comparison_result.txt)
                    
                    if [ "$IS_BETTER" = "true" ]; then
                        echo "🚀 DEPLOYMENT WOULD BE TRIGGERED HERE! 🚀"
                        # Ici on appellerait le script de déploiement
                        # python mlops/scripts/deploy.py --run_id $RUN_ID
                    else
                        echo "🛑 Deployment skipped. New model is not better."
                    fi
                '''
            }
        }
    } // Fin de 'stages'

    // La section 'post' est la meilleure façon de gérer les actions finales
    post {
        always {
            echo 'Archiving build artifacts...'
            archiveArtifacts artifacts: 'mlruns/**, training_output.log, comparison_result.txt', followSymlinks: false, allowEmptyArchive: true
        }
    }
}