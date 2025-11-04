pipeline {
  agent any
  environment {
    DOCKERHUB_REPO = 'kalyanimuppidi/ace-fitness-and-gym'
    // Ensure this URL is reachable by the Jenkins agent (e.g., use http://host.docker.internal:9000)
    SONARQUBE_HOST = 'http://sonarqube:9000' 
  }

  stages {
    stage('Checkout SCM') {
      steps {
        checkout scm
      }
    }

    // --- FIX: Installing pytest and generating coverage report ---
    stage('Unit Tests & Coverage') {
      steps {
        sh '''
          docker run --rm \
            -v "$WORKSPACE":/usr/src \
            -w /usr/src \
            python:3.10-slim bash -c "echo 'Inside container, preparing environment...' && \
            
            # Install necessary tools: pytest, pytest-cov, and project dependencies
            pip install --no-cache-dir pytest pytest-cov && \
            if [ -f requirements.txt ]; then pip install --no-cache-dir -r requirements.txt; else echo 'Project requirements.txt NOT found, continuing...'; fi; \
            
            # Run tests and output coverage to SonarQube's expected location.
            pytest --cov=app --cov-report=xml:coverage.xml -q || true"
        '''
      }
    }

    // --- FIX: SonarQube URL and Coverage Import ---
    stage('SonarQube Analysis') {
      when { expression { return true } } // Explicitly enabled
      steps {
        withCredentials([string(credentialsId: 'sonar-token', variable: 'SONAR_TOKEN')]) {
          sh '''
            docker run --rm -v "$WORKSPACE":/usr/src -w /usr/src \
              -e SONAR_HOST_URL="${SONARQUBE_HOST}" \
              -e SONAR_LOGIN="$SONAR_TOKEN" \
              sonarsource/sonar-scanner-cli \
              -Dsonar.projectKey=aceest-fitness \
              -Dsonar.sources=. \
              -Dsonar.python.version=3.10 \
              -Dsonar.python.coverage.reportPaths=coverage.xml
          '''
        }
      }
    }

    stage('Build Docker Image') {
      steps {
        script {
          def tag = sh(script: "git describe --tags --abbrev=0 || echo 'v1.4'", returnStdout: true).trim()
          def image = "${DOCKERHUB_REPO}:${tag}"
          sh "docker build -t ${image} ."
          env.IMAGE_NAME = image
          echo "Built image: ${image}"
        }
      }
    }

    stage('Push Docker Image') {
      steps {
        withCredentials([usernamePassword(credentialsId: 'docker-hub-creds', passwordVariable: 'DOCKER_PASS', usernameVariable: 'DOCKER_USER')]) {
          sh '''
            echo "$DOCKER_PASS" | docker login -u "$DOCKER_USER" --password-stdin
            docker push ${IMAGE_NAME} || true
          '''
        }
      }
    }

    stage('Deploy (placeholder)') {
      steps {
        echo "Deployment step would be implemented here (kubectl/helm)."
      }
    }

    // --- FIX: Credential Mounting (Apply Green) ---
    stage('Deploy Green') {
      steps {
        withCredentials([file(credentialsId: 'kubeconfig', variable: 'KUBECONFIG_FILE')]) {
          sh '''
            echo "Using docker run to run kubectl image..."

            # 1. Find the actual FILENAME (only the leaf name) inside the directory.
            KUBECONFIG_FILENAME=$(basename $(find "${KUBECONFIG_FILE}" -type f -print -quit))

            # 2. Mount the directory (${KUBECONFIG_FILE}) to a fixed directory in the container (/tmp/kube).
            # 3. Set the KUBECONFIG env var to the file's path *inside* the container.
            docker run --rm \
              -v "${KUBECONFIG_FILE}":/tmp/kube:ro \
              -e KUBECONFIG="/tmp/kube/${KUBECONFIG_FILENAME}" \
              --entrypoint kubectl \
              lachlanevenson/k8s-kubectl:latest \
              apply -f k8s/green-deployment.yaml
          '''
        }
      }
    }

    // --- FIX: Credential Mounting (Switch Service) ---
    stage('Switch Service to Green') {
      steps {
        withCredentials([file(credentialsId: 'kubeconfig', variable: 'KUBECONFIG_FILE')]) {
          sh '''
            # Find the actual FILENAME
            KUBECONFIG_FILENAME=$(basename $(find "${KUBECONFIG_FILE}" -type f -print -quit))

            # Mount the directory and set KUBECONFIG env var
            docker run --rm \
              -v "${KUBECONFIG_FILE}":/tmp/kube:ro \
              -e KUBECONFIG="/tmp/kube/${KUBECONFIG_FILENAME}" \
              --entrypoint kubectl \
              lachlanevenson/k8s-kubectl:latest \
              patch svc aceest-svc -p '{"spec":{"selector":{"app":"aceest","env":"green"}}}'
          '''
        }
      }
    }

    // --- FIX: Credential Mounting (Rollback) ---
    stage('Rollback (if tests fail)') {
      steps {
        withCredentials([file(credentialsId: 'kubeconfig', variable: 'KUBECONFIG_FILE')]) {
          sh '''
            # Find the actual FILENAME
            KUBECONFIG_FILENAME=$(basename $(find "${KUBECONFIG_FILE}" -type f -print -quit))

            # Mount the directory and set KUBECONFIG env var
            docker run --rm \
              -v "${KUBECONFIG_FILE}":/tmp/kube:ro \
              -e KUBECONFIG="/tmp/kube/${KUBECONFIG_FILENAME}" \
              --entrypoint kubectl \
              lachlanevenson/k8s-kubectl:latest \
              patch svc aceest-svc -p '{"spec":{"selector":{"app":"aceest","env":"blue"}}}'
          '''
        }
      }
    }

  }

  post {
    always {
      cleanWs()
    }
    success {
      echo "Pipeline succeeded for ${env.IMAGE_NAME}"
    }
    failure {
      echo "Pipeline failed — check console output"
    }
  }
}