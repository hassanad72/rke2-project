// CI only. The selected Jenkins node needs Git, Docker, Bash and AWS CLI.
pipeline {
    agent any
    options { skipDefaultCheckout() }

    environment {
        AWS_REGION = 'us-east-1'
        ECR_REGISTRY = '505342848876.dkr.ecr.us-east-1.amazonaws.com'
        IMAGE = "${ECR_REGISTRY}/devops-project-repo"
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Build image') {
            steps {
                sh 'docker build -t "$IMAGE:$GIT_COMMIT" .'
            }
        }

        stage('Push to ECR') {
            steps {
                sh '''#!/bin/bash
set -euo pipefail
set +x
export DOCKER_CONFIG="$(mktemp -d)"
trap 'rm -rf "$DOCKER_CONFIG"' EXIT
aws ecr get-login-password --region "$AWS_REGION" |
    docker login --username AWS --password-stdin "$ECR_REGISTRY"
docker push "$IMAGE:$GIT_COMMIT"
'''
            }
        }
    }
}
