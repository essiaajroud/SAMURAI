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

    stages {
        stage('Checkout Code') {
            steps {
                echo 'Checking out repository code...'
                checkout scm
            }
        }

        stage('Install Dependencies') {
            steps {
                echo 'Installing OS and Python dependencies...'
                sh 'apt-get update && apt-get install -y libgl1 libglib2.0-0 git'
                echo 'Installing CI dependencies inside the Docker agent...'
                sh 'apt-get update && apt-get install -y libgl1 libglib2.0-0'
                sh 'pip --version'
                sh 'pip install --upgrade pip'
                sh 'pip install torch==2.1.2 torchvision==0.16.2 torchaudio==2.1.2 --index-url https://download.pytorch.org/whl/cu121'
                sh 'pip install -r server/requirements-ci.txt'
            }
        }

        stage('Pull Data') {
            steps {
                echo 'Pulling data from DVC remote...'
                sh 'dvc pull -r myremote'
                echo 'Listing files after DVC pull to verify paths...'
                sh 'ls -R'
            }
        }

        stage('Train Model') {
            steps {
                sh 'python mlops/scripts/train.py --epochs 10 --batch 8 --data dataset/samurai/data.yaml --model server/models/best.pt --device cpu | tee training_output.log'
            }
        }

        stage('Compare Models') {
            steps {
                echo 'Comparing new model with production...'
                script {
                    def runId = sh(
                        script: "grep 'MLflow Run ID:' training_output.log | sed 's/.*MLflow Run ID: //'",
                        returnStdout: true
                    ).trim()
                    if (runId) {
                       echo "Found MLflow Run ID: ${runId}"
                        sh "python mlops/scripts/compare_models.py --run_id ${runId}"
                        def isBetter = readFile('comparison_result.txt').trim()

                        if (isBetter == 'true') {
                            echo '🚀 DEPLOYMENT TRIGGERED! 🚀'
                        } else {
                            echo '🛑 Deployment skipped.'
                        }
                    } else {
                        error("Could not find 'MLflow Run ID:' in the training output. The training script might have failed.")
                    }
                }
            }
        }

        stage('Deploy to Production') {
            when { expression { readFile('comparison_result.txt').trim() == 'true' } }
            steps {
                echo '🚀 DEPLOYMENT TRIGGERED! 🚀'
                script {
                    def output = readFile 'training_output.log'
                    def runIdMatch = (output =~ /MLflow Run ID: (\S+)/)
                    if (runIdMatch) {
                        def runId = runIdMatch[0][1]
                        
                        sh "python mlops/scripts/deploy.py --run_id ${runId}"
                    } else {
                        echo "Skipping deployment, could not determine Run ID."
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