pipeline {
    agent any
    options {
        skipDefaultCheckout()
        timeout(time: 20, unit: 'MINUTES')
        disableConcurrentBuilds()
        buildDiscarder(logRotator(numToKeepStr: '10'))
        timestamps()
    }

    triggers {
        githubPush()
    }

    environment {
        TRIVY_IMAGE = 'aquasec/trivy:0.76.0'
        AWS_REGION = 'us-east-1'
        ECR_REGISTRY = '505342848876.dkr.ecr.us-east-1.amazonaws.com'
        IMAGE = "${ECR_REGISTRY}/devops-project-repo"
    }

    stages {
        stage('Checkout') {
            steps {
                script {
                    def gitInfo = checkout scm
                    env.CI_BASE_COMMIT = gitInfo.GIT_PREVIOUS_SUCCESSFUL_COMMIT ?: ''
                    env.IMAGE_TAG = sh(
                        script: 'git rev-parse HEAD',
                        returnStdout: true
                    ).trim()
                }
                sh 'mkdir -p reports .trivy-cache; rm -f reports/junit.xml reports/trivy.json'
            }
        }

        stage('Check changes') {
            steps {
                script {
                    env.RUN_CI = sh(
                        script: '''
                            # First builds, missing history and manual reruns run full CI.
                            if [ -z "$CI_BASE_COMMIT" ] ||
                               ! git cat-file -e "$CI_BASE_COMMIT^{commit}" 2>/dev/null ||
                               [ "$CI_BASE_COMMIT" = "$IMAGE_TAG" ]; then
                                echo true
                            elif git diff --quiet "$CI_BASE_COMMIT" "$IMAGE_TAG" -- . ':(exclude)k8s/**'; then
                                echo false
                            else
                                diff_status=$?
                                if [ "$diff_status" -ne 1 ]; then
                                    exit "$diff_status"
                                fi
                                echo true
                            fi
                        ''',
                        returnStdout: true
                    ).trim()
                    if (env.RUN_CI == 'true') {
                        echo 'Application or CI changes detected: running CI.'
                    } else {
                        echo 'Only Kubernetes manifests changed: skipping CI stages.'
                    }
                }
            }
        }

        stage('Lint') {
            when {
                environment name: 'RUN_CI', value: 'true'
            }
            steps {
                sh '''
                    docker run --rm \
                        -e PYTHONDONTWRITEBYTECODE=1 \
                        -v "$WORKSPACE:/workspace:ro" \
                        -w /workspace \
                        python:3.12-slim \
                        sh -c 'pip install --no-cache-dir -r requirements-dev.txt && ruff check --no-cache app.py tests && ruff format --check --no-cache app.py tests'
                '''
            }
        }

        stage('Test') {
            when {
                environment name: 'RUN_CI', value: 'true'
            }
            steps {
                sh '''
                    docker run --rm \
                        -e PYTHONDONTWRITEBYTECODE=1 \
                        -v "$WORKSPACE:/workspace:ro" \
                        -v "$WORKSPACE/reports:/reports" \
                        -w /workspace \
                        python:3.12-slim \
                        sh -c 'pip install --no-cache-dir -r requirements-dev.txt && python -m pytest tests -v -p no:cacheprovider --junitxml=/reports/junit.xml'
                '''
            }
            post {
                always {
                    junit testResults: 'reports/junit.xml'
                }
            }
        }

        stage('Build image') {
            when {
                environment name: 'RUN_CI', value: 'true'
            }
            steps {
                sh 'docker build --pull --build-arg APP_VERSION="$IMAGE_TAG" -t "$IMAGE:${IMAGE_TAG:?Missing image tag}" .'
            }
        }

        stage('Scan image') {
            when {
                environment name: 'RUN_CI', value: 'true'
            }
            steps {
                sh '''
                    # Save all known vulnerability findings as a Jenkins artifact.
                    docker run --rm \
                        -v /var/run/docker.sock:/var/run/docker.sock \
                        -v "$WORKSPACE/.trivy-cache:/root/.cache/trivy" \
                        -v "$WORKSPACE/reports:/reports" \
                        "$TRIVY_IMAGE" image --image-src docker --scanners vuln \
                        --format json --output /reports/trivy.json \
                        --exit-code 0 "$IMAGE:$IMAGE_TAG"

                    # Block publication when High/Critical findings have fixes available.
                    docker run --rm \
                        -v /var/run/docker.sock:/var/run/docker.sock \
                        -v "$WORKSPACE/.trivy-cache:/root/.cache/trivy" \
                        "$TRIVY_IMAGE" image --image-src docker --scanners vuln \
                        --severity HIGH,CRITICAL --ignore-unfixed \
                        --exit-code 1 "$IMAGE:$IMAGE_TAG"
                '''
            }
        }

        stage('Push to ECR') {
            when {
                environment name: 'RUN_CI', value: 'true'
            }
            steps {
                sh '''#!/bin/bash
                    set -euo pipefail
                    set +x
                    export DOCKER_CONFIG="$(mktemp -d)"
                    trap 'rm -rf "$DOCKER_CONFIG"' EXIT
                    aws ecr get-login-password --region "$AWS_REGION" |
                        docker login --username AWS --password-stdin "$ECR_REGISTRY"
                    docker push "$IMAGE:$IMAGE_TAG"
                '''
            }
        }
    }

    post {
        always {
            archiveArtifacts artifacts: 'reports/*.xml,reports/*.json', allowEmptyArchive: true
        }
    }
}
