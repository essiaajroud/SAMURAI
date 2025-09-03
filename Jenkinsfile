pipeline {
    agent {
        docker {
            image 'python:3.11-slim'
            // Added --user root to ensure permissions for apt-get and other root operations
            // --network=host might not be strictly necessary unless your DVC/MLflow setup needs direct host network access
            args '--user root --entrypoint=""'
        }
    }

    environment {
        // Ensure this credential ID exists in Jenkins
        AZURE_STORAGE_CONNECTION_STRING = credentials('azure-storage-connection-string')
        // DVC remote URL might also be good to define here if it's dynamic
        DVC_REMOTE_URL = 'your-dvc-remote-url-if-needed' // Replace if you use a dynamic DVC remote
    }

    stages {
        stage('Prepare Workspace') {
            steps {
                echo 'Cleaning workspace...'
                cleanWs()

                echo 'Installing Git and checking out repository code...'
                // Install Git FIRST
                sh 'apt-get update && apt-get install -y git'
                // Then, clone the repository
                sh 'git clone https://github.com/essiaajroud/SAMURAI.git .'
                sh 'git checkout main' // Specify the branch to use
            }
        }

        stage('Install Dependencies') {
            steps {
                echo 'Installing OS and Python dependencies...'
                // Install dependencies for OpenCV/image processing
                sh 'apt-get update && apt-get install -y libgl1 libglib2.0-0'

                echo 'Installing Python packages...'
                sh 'pip install --upgrade pip'
                // Using specific PyTorch version with CUDA 12.1 index
                sh 'pip install torch==2.1.2 torchvision==0.16.2 torchaudio==2.1.2 --index-url https://download.pytorch.org/whl/cu121'
                // Using the lighter requirements-ci.txt
                sh 'pip install -r server/requirements-ci.txt'
            }
        }

        stage('Pull Data') {
            steps {
                echo 'Pulling data from DVC remote...'
                // Ensure DVC is installed as part of requirements-ci.txt
                // If your DVC remote requires credentials, they should be set as environment variables or passed securely.
                sh 'dvc pull -r myremote'
            }
        }

        stage('Train and Evaluate') {
            steps {
                echo 'Running model training and evaluation...'
                // Execute all logic in a single shell script block
                sh '''
                    #!/bin/bash
                    set -e # Exit immediately if a command exits with a non-zero status

                    echo "--- Running model training script ---"
                    # Redirect output to a log file for later parsing and debugging
                    python mlops/scripts/train.py --epochs 2 --batch 2 --data dataset/samurai/data.yaml --model server/models/best.pt --device cpu > training_output.log 2>&1
                    # Check the exit code of the python script explicitly
                    TRAIN_EXIT_CODE=$?
                    if [ $TRAIN_EXIT_CODE -ne 0 ]; then
                        echo "ERROR: Model training script failed with exit code $TRAIN_EXIT_CODE."
                        cat training_output.log # Print logs for immediate inspection in Jenkins console
                        exit $TRAIN_EXIT_CODE # Fail the stage
                    fi

                    echo "--- Comparing new model with production ---"
                    # Extract the run ID from the log file
                    RUN_ID=$(grep 'MLflow Run ID:' training_output.log | head -1 | sed 's/.*MLflow Run ID: //')

                    if [ -z "$RUN_ID" ]; then
                        echo "ERROR: Could not find MLflow Run ID in training_output.log. Training may have failed or log format changed."
                        cat training_output.log # Print logs for immediate inspection
                        exit 1 # Fail the stage
                    fi

                    echo "Found MLflow Run ID: $RUN_ID"
                    # Run comparison, directing output to a file
                    python mlops/scripts/compare_models.py --run_id "$RUN_ID" > comparison_result.txt 2>&1
                    COMPARE_EXIT_CODE=$?
                    if [ $COMPARE_EXIT_CODE -ne 0 ]; then
                        echo "ERROR: Model comparison script failed with exit code $COMPARE_EXIT_CODE."
                        cat comparison_result.txt # Print logs
                        exit $COMPARE_EXIT_CODE # Fail the stage
                    fi

                    IS_BETTER=$(cat comparison_result.txt | tr -d '\n' | tr -d '\r') # Remove newlines/carriage returns

                    if [ "$IS_BETTER" = "true" ]; then
                        echo "🚀 DEPLOYMENT WOULD BE TRIGGERED HERE! 🚀"
                        # Example: python mlops/scripts/deploy.py --run_id "$RUN_ID"
                    else
                        echo "🛑 Deployment skipped. New model is not better."
                    fi
                '''
            }
        }
    }

    post {
        always {
            echo 'Archiving build artifacts...'
            // Archive MLflow runs, training logs, and comparison results
            archiveArtifacts artifacts: 'mlruns/**, training_output.log, comparison_result.txt', followSymlinks: false, allowEmptyArchive: true
            echo 'Pipeline finished.'
        }
        failure {
            echo 'Pipeline failed. Check logs for details.'
        }
    }
}