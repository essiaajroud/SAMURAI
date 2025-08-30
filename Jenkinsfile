pipeline {
    agent {
        docker {
            image 'python:3.11-slim'
            args '-u root --entrypoint="" --network=host'
        }
    }

    options {
        
        skipDefaultCheckout true
    }


    environment {
        AZURE_STORAGE_CONNECTION_STRING = credentials('azure-storage-connection-string')
    }

    
    stages {
        stage('Prepare Workspace') {
            steps {
                echo 'Cleaning workspace...'
                cleanWs()
                echo 'Checking out repository code...'
                checkout scm
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
                sh 'dvc pull -r myremote'
            }
        }

        stage('Train Model') {
            steps {
                echo 'Running model training script...'
                
                sh 'python mlops/scripts/train.py --epochs 10 --batch 8 --data dataset/samurai/data.yaml --model server/models/best.pt --device cpu | tee training_output.log'
            }
        }

        stage('Evaluate & Compare') {
            steps {
                echo 'Comparing new model with production...'
                script {
                    def output = readFile 'training_output.log'
                    
                    def runId = (output =~ /MLflow Run ID: (\S+)/).find() ? (output =~ /MLflow Run ID: (\S+)/)[0][1] : null
                    
                    if (runId) {
                        echo "Found MLflow Run ID: ${runId}"
                        sh "python mlops/scripts/compare_models.py --run_id ${runId}"
                    } else {
                        
                        error("Could not find 'MLflow Run ID:' in the training output. The training script likely failed.")
                    }
                }
            }
        }

        stage('Deploy if Better') {
            
            steps {
                script {
                    def isBetter = readFile('comparison_result.txt').trim()
                    if (isBetter == 'true') {
                        echo '🚀 DEPLOYMENT SCRIPT WOULD RUN HERE! 🚀'
                       
                    } else {
                        echo '🛑 Deployment skipped. New model is not better than production.'
                    }
                }
            }
        }

        stage('Archive Artifacts') {
            
            always {
                steps {
                    echo 'Archiving MLflow results...'
                    archiveArtifacts artifacts: 'mlruns/**', followSymlinks: false, allowEmptyArchive: true
                }
            }
        }
    } 
} 