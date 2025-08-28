pipeline {
    agent any // Exécuter sur n'importe quel "agent" Jenkins disponible

    environment {
        // Définir la variable d'environnement à partir des secrets Jenkins
        AZURE_STORAGE_CONNECTION_STRING = credentials('azure-storage-connection-string')
    }

    stages {
        stage('Checkout Code') {
            steps {
                echo 'Checking out repository code...'
                checkout scm
            }
        }

        stage('Setup Environment') {
            steps {
                echo 'Installing Python dependencies...'
                // Assumer que le runner a Python. Pour plus de robustesse, on utiliserait un conteneur Docker.
                sh 'python3 -m pip install --upgrade pip'
                sh 'pip3 install -r server/requirements.txt'
                sh 'pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121'
                sh 'pip3 install mlflow PyYAML dvc[azure]'
            }
        }

        stage('Pull Data') {
            steps {
                echo 'Pulling data from DVC remote...'
                // La variable d'environnement AZURE_STORAGE_CONNECTION_STRING est utilisée automatiquement
                sh 'dvc pull -r myremote'
            }
        }

        stage('Train Model') {
            steps {
                echo 'Running model training script...'
                // On sauvegarde la sortie pour en extraire l'ID du run
                sh 'python3 mlops/scripts/train.py --epochs 10 --batch 8 --data dataset/samurai/data.yaml --model yolov11m > training_output.log'
            }
        }

        stage('Compare Models') {
            steps {
                echo 'Comparing new model with production...'
                script {
                    def output = readFile 'training_output.log'
                    def runId = (output =~ /MLflow Run ID: (\S+)/)[0][1]
                    
                    sh "python3 mlops/scripts/compare_models.py --run_id ${runId}"
                    def isBetter = readFile('comparison_result.txt').trim()

                    if (isBetter == 'true') {
                        echo '🚀 DEPLOYMENT TRIGGERED! 🚀'
                        // Ici, on pourrait déclencher un autre job de déploiement
                    } else {
                        echo '🛑 Deployment skipped. The new model is not better.'
                    }
                }
            }
        }

        stage('Archive Artifacts') {
            steps {
                echo 'Archiving MLflow results...'
                archiveArtifacts artifacts: 'mlruns/**', followSymlinks: false
            }
        }
    }
}