pipeline {
    agent any
    options {
        skipDefaultCheckout()
    }

    triggers {
        githubPush()
    }

    environment {
        AWS_REGION = 'us-east-1'
        ECR_REGISTRY = '505342848876.dkr.ecr.us-east-1.amazonaws.com'
        IMAGE = "${ECR_REGISTRY}/devops-project-repo"
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
                script {
                    env.IMAGE_TAG = sh(
                        script: 'git rev-parse HEAD',
                        returnStdout: true
                    ).trim()
                }
            }
        }

        stage('Test') {
            steps {
                sh '''
                    docker run --rm \
                        -e PYTHONDONTWRITEBYTECODE=1 \
                        -v "$WORKSPACE:/workspace:ro" \
                        -w /workspace \
                        python:3.12-slim \
                        sh -c 'pip install --no-cache-dir -r requirements.txt && python -m unittest discover -s tests -v'
                '''.stripIndent().trim()
            }
        }

        stage('Build image') {
            steps {
                sh 'docker build -t "$IMAGE:${IMAGE_TAG:?Missing image tag}" .'
            }
        }

        stage('Push to ECR') {
            steps {
                sh '''
                    #!/bin/bash
                    set -euo pipefail
                    set +x
                    export DOCKER_CONFIG="$(mktemp -d)"
                    trap 'rm -rf "$DOCKER_CONFIG"' EXIT
                    aws ecr get-login-password --region "$AWS_REGION" |
                        docker login --username AWS --password-stdin "$ECR_REGISTRY"
                    docker push "$IMAGE:$IMAGE_TAG"
                '''.stripIndent().trim()
            }
        }
    }
}
