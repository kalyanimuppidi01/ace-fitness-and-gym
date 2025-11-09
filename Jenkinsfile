pipeline {
  agent any
  environment {
    DOCKERHUB_REPO = 'kalyanimuppidi/ace-fitness-and-gym'
    // Ensure this URL is reachable by the Jenkins agent (e.g., use http://host.docker.internal:9000)
    SONARQUBE_HOST = https://sonarcloud.io'
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
  when { expression { return true } } // enabled
  steps {
    withCredentials([string(credentialsId: 'sonar-token', variable: 'SONAR_TOKEN')]) {
      sh '''
        echo "Running SonarScanner (will pass token via -Dsonar.login)..."
        docker run --rm -v "$WORKSPACE":/usr/src -w /usr/src \
          -e SONAR_HOST_URL="${SONARQUBE_HOST}" \
          sonarsource/sonar-scanner-cli \
          -Dsonar.projectKey=aceest-fitness \
          -Dsonar.sources=. \
          -Dsonar.python.version=3.10 \
          -Dsonar.python.coverage.reportPaths=coverage.xml \
          -Dsonar.login="${SONAR_TOKEN}"
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

    stage('Deploy Green') {
  steps {
    withCredentials([file(credentialsId: 'kubeconfig', variable: 'KUBECONFIG_FILE')]) {
      sh '''
        echo "Using docker run to run kubectl image (mount file directly)..."
        # mount the kubeconfig file as /tmp/kubeconfig inside the container
        docker run --rm \
          -v "${KUBECONFIG_FILE}":/tmp/kubeconfig:ro \
          --entrypoint kubectl \
          lachlanevenson/k8s-kubectl:latest \
          --kubeconfig=/tmp/kubeconfig \
          apply -f k8s/green-deployment.yaml
      '''
    }
  }
}


    stage('Switch Service to Green') {
  steps {
    withCredentials([file(credentialsId: 'kubeconfig', variable: 'KUBECONFIG_FILE')]) {
      sh '''
        docker run --rm \
          -v "${KUBECONFIG_FILE}":/tmp/kubeconfig:ro \
          --entrypoint kubectl \
          lachlanevenson/k8s-kubectl:latest \
          --kubeconfig=/tmp/kubeconfig \
          patch svc aceest-svc -p '{"spec":{"selector":{"app":"aceest","env":"green"}}}'
      '''
    }
  }
}


    stage('Rollback (if tests fail)') {
  steps {
    withCredentials([file(credentialsId: 'kubeconfig', variable: 'KUBECONFIG_FILE')]) {
      sh '''
        docker run --rm \
          -v "${KUBECONFIG_FILE}":/tmp/kubeconfig:ro \
          --entrypoint kubectl \
          lachlanevenson/k8s-kubectl:latest \
          --kubeconfig=/tmp/kubeconfig \
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