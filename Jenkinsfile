#!/usr/bin/env groovy

/*
 * Jenkins Pipeline for SPX Options Trading Bot
 * Advanced Deployment Strategies: Blue-Green, Canary, Rolling Updates, Feature Flags, Multi-Environment
 * Implements comprehensive CI/CD with zero-downtime deployments
 */

pipeline {
    agent {
        kubernetes {
            yaml """
apiVersion: v1
kind: Pod
spec:
  containers:
  - name: python
    image: python:3.11-slim
    command:
    - cat
    tty: true
    volumeMounts:
    - name: docker-sock
      mountPath: /var/run/docker.sock
  - name: docker
    image: docker:latest
    command:
    - cat
    tty: true
    volumeMounts:
    - name: docker-sock
      mountPath: /var/run/docker.sock
  - name: kubectl
    image: bitnami/kubectl:latest
    command:
    - cat
    tty: true
  volumes:
  - name: docker-sock
    hostPath:
      path: /var/run/docker.sock
"""
        }
    }
    
    environment {
        // Container Registry Configuration
        REGISTRY_URL = 'spxoptionsregistry.azurecr.io'
        IMAGE_NAME = 'spx-options-trading-bot'
        
        // Feature Flag Service
        FEATURE_FLAG_SERVICE = 'https://feature-flags.spxoptions.com'
        
        // Kubernetes Configuration
        KUBECONFIG = credentials('k8s-config')
        
        // Environment-specific configurations
        DEV_NAMESPACE = 'spx-options-dev'
        STAGING_NAMESPACE = 'spx-options-staging'
        PROD_NAMESPACE = 'spx-options-prod'
        
        // Security and Compliance
        SNYK_TOKEN = credentials('snyk-token')
        SONAR_TOKEN = credentials('sonar-token')
        
        // Notification Configuration
        SLACK_WEBHOOK = credentials('slack-webhook-url')
        TEAMS_WEBHOOK = credentials('teams-webhook-url')
    }
    
    parameters {
        choice(
            choices: ['dev', 'staging', 'production'],
            description: 'Target environment for deployment',
            name: 'DEPLOY_ENVIRONMENT'
        )
        booleanParam(
            defaultValue: false,
            description: 'Enable feature flags during deployment',
            name: 'ENABLE_FEATURE_FLAGS'
        )
        choice(
            choices: ['rolling', 'blue-green', 'canary'],
            description: 'Deployment strategy',
            name: 'DEPLOYMENT_STRATEGY'
        )
        string(
            defaultValue: '10,25,50,100',
            description: 'Canary deployment percentages (comma-separated)',
            name: 'CANARY_PERCENTAGES'
        )
    }
    
    options {
        buildDiscarder(logRotator(numToKeepStr: '50'))
        timeout(time: 60, unit: 'MINUTES')
        timestamps()
        ansiColor('xterm')
        skipStagesAfterUnstable()
    }
    
    stages {
        stage('Checkout & Environment Setup') {
            steps {
                script {
                    // Set dynamic environment variables
                    env.BUILD_VERSION = "${BUILD_NUMBER}-${GIT_COMMIT.take(7)}"
                    env.IMAGE_TAG = "${env.BUILD_VERSION}"
                    env.FULL_IMAGE_NAME = "${REGISTRY_URL}/${IMAGE_NAME}:${IMAGE_TAG}"
                    
                    // Determine deployment target based on branch
                    if (env.BRANCH_NAME == 'main') {
                        env.TARGET_ENV = params.DEPLOY_ENVIRONMENT ?: 'production'
                    } else if (env.BRANCH_NAME == 'develop') {
                        env.TARGET_ENV = 'dev'
                    } else {
                        env.TARGET_ENV = 'dev'
                    }
                    
                    echo "Building version: ${env.BUILD_VERSION}"
                    echo "Target environment: ${env.TARGET_ENV}"
                    echo "Deployment strategy: ${params.DEPLOYMENT_STRATEGY}"
                }
                
                checkout scm
                
                // Send build start notification
                script {
                    sendNotification('started', 'Build started', 'info')
                }
            }
        }
        
        stage('Code Quality & Security Analysis') {
            parallel {
                stage('Static Code Analysis') {
                    steps {
                        container('python') {
                            sh '''
                                pip install --upgrade pip
                                pip install black flake8 mypy pylint bandit safety pytest-cov
                                
                                # Code formatting check
                                echo "Checking code formatting with Black..."
                                black --check --diff .
                                
                                # Linting with flake8
                                echo "Running flake8 linting..."
                                flake8 . --max-line-length=88 --extend-ignore=E203,W503 --statistics
                                
                                # Type checking with mypy
                                echo "Running mypy type checking..."
                                mypy . --ignore-missing-imports --strict-optional
                                
                                # Advanced linting with pylint
                                echo "Running pylint analysis..."
                                pylint --rcfile=.pylintrc src/ || true
                            '''
                        }
                    }
                    post {
                        always {
                            publishHTML([
                                allowMissing: false,
                                alwaysLinkToLastBuild: true,
                                keepAll: true,
                                reportDir: 'reports',
                                reportFiles: 'pylint.html',
                                reportName: 'PyLint Report'
                            ])
                        }
                    }
                }
                
                stage('Security Vulnerability Scanning') {
                    steps {
                        container('python') {
                            sh '''
                                # Install dependencies
                                pip install -r requirements.txt
                                
                                # Safety check for known security vulnerabilities
                                echo "Running safety check for known vulnerabilities..."
                                safety check --json --output safety-report.json || true
                                
                                # Bandit security analysis
                                echo "Running bandit security analysis..."
                                bandit -r . -f json -o bandit-report.json -ll || true
                                
                                # Snyk vulnerability scanning
                                if [ ! -z "${SNYK_TOKEN}" ]; then
                                    npm install -g snyk
                                    snyk auth ${SNYK_TOKEN}
                                    snyk test --json > snyk-report.json || true
                                fi
                            '''
                        }
                    }
                    post {
                        always {
                            archiveArtifacts artifacts: '*-report.json', allowEmptyArchive: true
                        }
                    }
                }
                
                stage('SonarQube Analysis') {
                    when {
                        anyOf {
                            branch 'main'
                            branch 'develop'
                        }
                    }
                    steps {
                        container('python') {
                            withSonarQubeEnv('SonarQube') {
                                sh '''
                                    sonar-scanner \
                                        -Dsonar.projectKey=spx-options-trading-bot \
                                        -Dsonar.sources=. \
                                        -Dsonar.host.url=$SONAR_HOST_URL \
                                        -Dsonar.login=$SONAR_AUTH_TOKEN \
                                        -Dsonar.python.coverage.reportPaths=coverage.xml \
                                        -Dsonar.python.xunit.reportPath=test-results.xml
                                '''
                            }
                        }
                    }
                }
            }
        }
        
        stage('Comprehensive Testing') {
            parallel {
                stage('Unit & Integration Tests') {
                    steps {
                        container('python') {
                            sh '''
                                # Run comprehensive test suite
                                echo "Running unit and integration tests..."
                                python -m pytest tests/ \
                                    --cov=. \
                                    --cov-report=xml \
                                    --cov-report=html \
                                    --junitxml=test-results.xml \
                                    --maxfail=5 \
                                    --tb=short \
                                    -v
                            '''
                        }
                    }
                    post {
                        always {
                            junit 'test-results.xml'
                            publishHTML([
                                allowMissing: false,
                                alwaysLinkToLastBuild: true,
                                keepAll: true,
                                reportDir: 'htmlcov',
                                reportFiles: 'index.html',
                                reportName: 'Coverage Report'
                            ])
                        }
                    }
                }
                
                stage('Performance & Load Tests') {
                    when {
                        anyOf {
                            branch 'main'
                            branch 'develop'
                        }
                    }
                    steps {
                        container('python') {
                            sh '''
                                # Performance testing
                                echo "Running performance tests..."
                                pip install locust pytest-benchmark
                                
                                # Benchmark critical functions
                                python -m pytest tests/performance/ --benchmark-json=benchmark.json
                                
                                # Load testing with Locust (if available)
                                if [ -f "locustfile.py" ]; then
                                    locust --headless --users 50 --spawn-rate 5 --run-time 60s --host http://localhost:8000 || true
                                fi
                            '''
                        }
                    }
                    post {
                        always {
                            archiveArtifacts artifacts: 'benchmark.json', allowEmptyArchive: true
                        }
                    }
                }
            }
        }
        
        stage('Build & Push Container') {
            steps {
                container('docker') {
                    sh '''
                        # Build multi-stage Docker image
                        echo "Building Docker image: ${FULL_IMAGE_NAME}"
                        docker build \
                            --build-arg BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ') \
                            --build-arg VCS_REF=${GIT_COMMIT} \
                            --build-arg VERSION=${BUILD_VERSION} \
                            --tag ${FULL_IMAGE_NAME} \
                            --tag ${REGISTRY_URL}/${IMAGE_NAME}:latest \
                            --file Dockerfile.multi-stage \
                            .
                    '''
                }
                
                // Container Security Scanning
                container('docker') {
                    sh '''
                        # Install and run Trivy for container scanning
                        curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b /usr/local/bin
                        
                        # Scan the built image
                        trivy image --format json --output trivy-report.json ${FULL_IMAGE_NAME} || true
                        trivy image --format table ${FULL_IMAGE_NAME}
                    '''
                }
                
                // Push to registry
                script {
                    docker.withRegistry("https://${REGISTRY_URL}", 'acr-credentials') {
                        sh "docker push ${FULL_IMAGE_NAME}"
                        sh "docker push ${REGISTRY_URL}/${IMAGE_NAME}:latest"
                    }
                }
            }
            post {
                always {
                    archiveArtifacts artifacts: 'trivy-report.json', allowEmptyArchive: true
                }
            }
        }
        
        stage('Deploy to Development') {
            when {
                anyOf {
                    branch 'develop'
                    allOf {
                        branch 'feature/*'
                        expression { params.DEPLOY_ENVIRONMENT == 'dev' }
                    }
                }
            }
            steps {
                script {
                    deployToEnvironment('dev', 'rolling')
                }
            }
        }
        
        stage('Deploy to Staging') {
            when {
                branch 'main'
                expression { params.DEPLOY_ENVIRONMENT != 'dev' }
            }
            steps {
                script {
                    deployToEnvironment('staging', 'blue-green')
                }
            }
        }
        
        stage('Deploy to Production') {
            when {
                allOf {
                    branch 'main'
                    expression { params.DEPLOY_ENVIRONMENT == 'production' }
                }
            }
            steps {
                // Manual approval for production
                script {
                    try {
                        timeout(time: 10, unit: 'MINUTES') {
                            input message: 'Deploy to Production?', 
                                  ok: 'Deploy',
                                  parameters: [
                                      booleanParam(defaultValue: false, description: 'Confirm production deployment', name: 'PRODUCTION_CONFIRMED')
                                  ]
                        }
                    } catch (Exception e) {
                        currentBuild.result = 'ABORTED'
                        error('Production deployment cancelled by user or timeout')
                    }
                }
                
                script {
                    deployToEnvironment('production', params.DEPLOYMENT_STRATEGY)
                }
            }
        }
        
        stage('Post-Deployment Validation') {
            when {
                not { 
                    environment name: 'TARGET_ENV', value: 'dev'
                }
            }
            parallel {
                stage('End-to-End Tests') {
                    steps {
                        container('python') {
                            sh '''
                                # Run end-to-end tests against deployed environment
                                pip install selenium requests pytest-html
                                
                                export TEST_ENVIRONMENT=${TARGET_ENV}
                                export BASE_URL=https://spx-options-${TARGET_ENV}.domain.com
                                
                                python -m pytest tests/e2e/ \
                                    --html=e2e-report.html \
                                    --self-contained-html \
                                    -v
                            '''
                        }
                    }
                    post {
                        always {
                            publishHTML([
                                allowMissing: false,
                                alwaysLinkToLastBuild: true,
                                keepAll: true,
                                reportDir: '.',
                                reportFiles: 'e2e-report.html',
                                reportName: 'E2E Test Report'
                            ])
                        }
                    }
                }
                
                stage('Performance Validation') {
                    steps {
                        container('python') {
                            sh '''
                                # Performance validation against deployed service
                                pip install requests numpy matplotlib
                                
                                python scripts/performance_validation.py \
                                    --environment ${TARGET_ENV} \
                                    --duration 300 \
                                    --requests-per-second 100 \
                                    --generate-report
                            '''
                        }
                    }
                }
                
                stage('Security Validation') {
                    steps {
                        container('python') {
                            sh '''
                                # Security validation
                                pip install owasp-zap-api requests
                                
                                python scripts/security_validation.py \
                                    --target-url https://spx-options-${TARGET_ENV}.domain.com \
                                    --scan-type quick \
                                    --generate-report
                            '''
                        }
                    }
                }
            }
        }
        
        stage('Chaos Engineering') {
            when {
                allOf {
                    branch 'main'
                    expression { params.DEPLOY_ENVIRONMENT == 'production' }
                    expression { env.BUILD_NUMBER.toInteger() % 10 == 0 } // Run every 10th build
                }
            }
            steps {
                script {
                    try {
                        timeout(time: 5, unit: 'MINUTES') {
                            input message: 'Run Chaos Engineering Tests?', 
                                  ok: 'Proceed',
                                  parameters: [
                                      booleanParam(defaultValue: false, description: 'Execute chaos experiments', name: 'CHAOS_CONFIRMED')
                                  ]
                        }
                        
                        container('kubectl') {
                            sh '''
                                # Install Chaos Mesh or use Litmus
                                echo "Executing controlled chaos experiments..."
                                
                                # Pod failure experiment
                                python scripts/chaos_experiments.py \
                                    --experiment pod-failure \
                                    --namespace ${PROD_NAMESPACE} \
                                    --duration 300 \
                                    --safety-checks-enabled
                                
                                # Network latency experiment
                                python scripts/chaos_experiments.py \
                                    --experiment network-latency \
                                    --namespace ${PROD_NAMESPACE} \
                                    --duration 300 \
                                    --latency 100ms
                            '''
                        }
                    } catch (Exception e) {
                        echo "Chaos engineering tests skipped or cancelled"
                    }
                }
            }
        }
    }
    
    post {
        always {
            // Archive build artifacts
            archiveArtifacts artifacts: '**/*-report.*', allowEmptyArchive: true
            
            // Cleanup
            container('docker') {
                sh '''
                    docker rmi ${FULL_IMAGE_NAME} || true
                    docker system prune -f || true
                '''
            }
        }
        
        success {
            script {
                sendNotification('success', "Build ${BUILD_NUMBER} completed successfully", 'good')
                updateFeatureFlags('enable')
            }
        }
        
        failure {
            script {
                sendNotification('failure', "Build ${BUILD_NUMBER} failed", 'danger')
                if (env.TARGET_ENV == 'production') {
                    triggerRollback()
                }
            }
        }
        
        unstable {
            script {
                sendNotification('unstable', "Build ${BUILD_NUMBER} is unstable", 'warning')
            }
        }
        
        aborted {
            script {
                sendNotification('aborted', "Build ${BUILD_NUMBER} was aborted", 'warning')
            }
        }
    }
}

// Helper Functions
def deployToEnvironment(String environment, String strategy) {
    container('kubectl') {
        switch(strategy) {
            case 'rolling':
                deployRolling(environment)
                break
            case 'blue-green':
                deployBlueGreen(environment)
                break
            case 'canary':
                deployCanary(environment)
                break
            default:
                deployRolling(environment)
        }
    }
}

def deployRolling(String environment) {
    sh """
        echo "Deploying to ${environment} using rolling update strategy..."
        
        # Update deployment with new image
        kubectl set image deployment/spx-options-trading-bot \\
            spx-options-trading-bot=${FULL_IMAGE_NAME} \\
            -n ${environment == 'dev' ? DEV_NAMESPACE : environment == 'staging' ? STAGING_NAMESPACE : PROD_NAMESPACE}
        
        # Wait for rollout to complete
        kubectl rollout status deployment/spx-options-trading-bot \\
            -n ${environment == 'dev' ? DEV_NAMESPACE : environment == 'staging' ? STAGING_NAMESPACE : PROD_NAMESPACE} \\
            --timeout=300s
        
        # Verify deployment
        python scripts/deployment_verification.py --environment ${environment} --strategy rolling
    """
}

def deployBlueGreen(String environment) {
    sh """
        echo "Deploying to ${environment} using blue-green strategy..."
        
        # Deploy to blue environment
        kubectl apply -f k8s/${environment}/deployment-blue.yaml
        kubectl set image deployment/spx-options-trading-bot-blue \\
            spx-options-trading-bot=${FULL_IMAGE_NAME} \\
            -n ${environment == 'staging' ? STAGING_NAMESPACE : PROD_NAMESPACE}
        
        # Wait for blue deployment
        kubectl rollout status deployment/spx-options-trading-bot-blue \\
            -n ${environment == 'staging' ? STAGING_NAMESPACE : PROD_NAMESPACE} \\
            --timeout=300s
        
        # Health check blue environment
        python scripts/health_checker.py \\
            --environment ${environment}-blue \\
            --timeout 300 \\
            --retry-count 5
        
        # Switch traffic to blue
        kubectl apply -f k8s/${environment}/service-blue-main.yaml
        
        # Cleanup old green deployment
        kubectl delete deployment spx-options-trading-bot-green \\
            -n ${environment == 'staging' ? STAGING_NAMESPACE : PROD_NAMESPACE} \\
            --ignore-not-found=true
    """
}

def deployCanary(String environment) {
    def percentages = params.CANARY_PERCENTAGES.split(',')
    
    for (int i = 0; i < percentages.size(); i++) {
        def percentage = percentages[i].trim()
        
        sh """
            echo "Deploying canary with ${percentage}% traffic..."
            
            # Deploy canary version
            kubectl apply -f k8s/${environment}/deployment-canary.yaml
            kubectl set image deployment/spx-options-trading-bot-canary \\
                spx-options-trading-bot=${FULL_IMAGE_NAME} \\
                -n ${PROD_NAMESPACE}
            
            # Update Istio virtual service for traffic splitting
            envsubst < k8s/${environment}/istio-virtual-service-template.yaml | \\
                sed "s/CANARY_PERCENTAGE/${percentage}/g" | \\
                kubectl apply -f -
        """
        
        // Monitor canary for specified duration
        def monitorDuration = percentage.toInteger() < 50 ? 600 : 900 // 10 or 15 minutes
        
        sh """
            python scripts/canary_monitor.py \\
                --traffic-percentage ${percentage} \\
                --duration ${monitorDuration} \\
                --error-threshold 0.01 \\
                --latency-threshold-p99 500 \\
                --business-metrics-check \\
                --rollback-on-failure
        """
        
        // Ask for approval before next phase (except for final deployment)
        if (i < percentages.size() - 1) {
            try {
                timeout(time: 5, unit: 'MINUTES') {
                    input message: "Continue to ${percentages[i+1].trim()}% traffic?", 
                          ok: 'Continue'
                }
            } catch (Exception e) {
                error("Canary deployment cancelled")
            }
        }
    }
}

def sendNotification(String status, String message, String color) {
    def payload = [
        channel: '#deployments',
        color: color,
        message: "${message} - ${env.JOB_NAME} #${env.BUILD_NUMBER}",
        teamDomain: 'your-team',
        token: env.SLACK_TOKEN,
        baseUrl: 'https://hooks.slack.com/services/',
        botUser: true
    ]
    
    try {
        slackSend(payload)
    } catch (Exception e) {
        echo "Failed to send Slack notification: ${e.message}"
    }
    
    // Also send to Microsoft Teams if configured
    if (env.TEAMS_WEBHOOK) {
        def teamsPayload = [
            "@type": "MessageCard",
            "@context": "http://schema.org/extensions",
            "themeColor": color == 'good' ? '00FF00' : color == 'danger' ? 'FF0000' : 'FFFF00',
            "summary": message,
            "sections": [[
                "activityTitle": "Jenkins Build Notification",
                "activitySubtitle": "${env.JOB_NAME} #${env.BUILD_NUMBER}",
                "markdown": true,
                "facts": [
                    ["name": "Status", "value": status],
                    ["name": "Branch", "value": env.BRANCH_NAME],
                    ["name": "Environment", "value": env.TARGET_ENV],
                    ["name": "Build URL", "value": env.BUILD_URL]
                ]
            ]]
        ]
        
        try {
            httpRequest(
                httpMode: 'POST',
                contentType: 'APPLICATION_JSON',
                url: env.TEAMS_WEBHOOK,
                requestBody: groovy.json.JsonOutput.toJson(teamsPayload)
            )
        } catch (Exception e) {
            echo "Failed to send Teams notification: ${e.message}"
        }
    }
}

def updateFeatureFlags(String action) {
    if (params.ENABLE_FEATURE_FLAGS && env.TARGET_ENV in ['staging', 'production']) {
        container('python') {
            sh """
                python scripts/feature_flag_manager.py \\
                    --environment ${env.TARGET_ENV} \\
                    --action ${action} \\
                    --flags advanced-algorithms,ml-predictions \\
                    --version ${env.BUILD_VERSION}
            """
        }
    }
}

def triggerRollback() {
    if (env.TARGET_ENV == 'production') {
        container('kubectl') {
            sh """
                echo "Triggering emergency rollback..."
                
                # Rollback deployment
                kubectl rollout undo deployment/spx-options-trading-bot -n ${PROD_NAMESPACE}
                
                # Disable feature flags
                python scripts/feature_flag_manager.py \\
                    --environment production \\
                    --action emergency-disable \\
                    --flags advanced-algorithms,ml-predictions
                
                # Send critical alert
                python scripts/alert_manager.py \\
                    --severity critical \\
                    --message "Production rollback triggered for build ${BUILD_NUMBER}" \\
                    --notify-oncall \\
                    --create-incident
            """
        }
    }
}
