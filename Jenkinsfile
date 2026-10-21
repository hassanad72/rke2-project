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
        GITOPS_REPO = 'git@github.com:hassanad72/rke2-project-gitops.git'
        TRIVY_IMAGE = 'aquasec/trivy:0.76.0'
        AWS_REGION = 'us-east-1'
        ECR_REGISTRY = '505342848876.dkr.ecr.us-east-1.amazonaws.com'
        IMAGE = "${ECR_REGISTRY}/devops-project-repo"
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
                sh 'mkdir -p reports .trivy-cache; rm -f reports/junit.xml reports/trivy.json'
                script {
                    env.IMAGE_TAG = sh(
                        script: 'git rev-parse HEAD',
                        returnStdout: true
                    ).trim()
                }
            }
        }

        stage('Lint') {
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
            steps {
                sh 'docker build --pull --build-arg APP_VERSION="$IMAGE_TAG" -t "$IMAGE:${IMAGE_TAG:?Missing image tag}" .'
            }
        }

        stage('Scan image') {
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

        stage('Update GitOps image') {
            steps {
                withCredentials([sshUserPrivateKey(
                    credentialsId: 'github-rke2-gitops',
                    keyFileVariable: 'GITOPS_KEY'
                )]) {
                    sh '''#!/bin/bash
                        set -euo pipefail
                        set +x
                        export GIT_SSH_COMMAND='ssh -i "$GITOPS_KEY" -o IdentitiesOnly=yes -o BatchMode=yes -o StrictHostKeyChecking=yes'
                        work_dir=$(mktemp -d)
                        trap 'rm -rf "$work_dir"' EXIT
                        git clone --depth 1 --branch main "$GITOPS_REPO" "$work_dir/repo"
                        cd "$work_dir/repo"

                        # This PoC has exactly one container image in its Deployment.
                        awk -v image="$IMAGE:$IMAGE_TAG" '
                            $1 == "image:" {
                                sub(/image:.*/, "image: " image)
                                count++
                            }
                            { print }
                            END { if (count != 1) exit 1 }
                        ' k8s/deployment.yaml > "$work_dir/deployment.yaml"
                        mv "$work_dir/deployment.yaml" k8s/deployment.yaml
                        git diff --check

                        if git diff --quiet -- k8s/deployment.yaml; then
                            echo 'GitOps already references this image; nothing to push.'
                            exit 0
                        fi
                        git config user.name 'Jenkins CI'
                        git config user.email 'jenkins@localhost'
                        git add k8s/deployment.yaml
                        git commit -m "Update rke2-project image to $IMAGE_TAG"
                        git push origin HEAD:main
                    '''
                }
            }
        }
    }

    post {
        always {
            archiveArtifacts artifacts: 'reports/*.xml,reports/*.json', allowEmptyArchive: true
        }
    }
}
