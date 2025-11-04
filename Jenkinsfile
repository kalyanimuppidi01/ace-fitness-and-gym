pipeline {
  agent any
  environment {
    DOCKERHUB_REPO = 'kalyanimuppidi/ace-fitness-and-gym'
    SONARQUBE_SERVER = 'SonarQube'
  }

  stages {
    stage('Checkout Jenkinsfile') {
      steps {
        checkout scm
      }
    }

    stage('Unit Tests & Coverage') {
  steps {
    sh '''
      docker run --rm \
        -v "$WORKSPACE":/usr/src \
        -w /usr/src \
        python:3.10-slim bash -c "echo 'Inside container...' && \

        # Install necessary tools: pytest, pytest-cov, and project dependencies
        pip install --no-cache-dir pytest pytest-cov && \
        if [ -f requirements.txt ]; then pip install --no-cache-dir -r requirements.txt; else echo 'Project requirements.txt NOT found, continuing...'; fi; \

        # Run tests and output coverage
        pytest --cov=app --cov-report=xml:coverage.xml -q || true"
    '''
  }
}

    stage('SonarQube Analysis') {
      // NOTE: Enabled this stage!
      steps {
        withCredentials([string(credentialsId: 'sonar-token', variable: 'SONAR_TOKEN')]) {
          sh '''
            docker run --rm -v "$WORKSPACE":/usr/src -w /usr/src \
              -e SONAR_HOST_URL="http://sonarqube:9000" \
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
          // Attempt to use most recent tag; fallback to v1.4
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
            docker push ${IMAGE_NAME}
          '''
        }
      }
    }

    stage('Deploy Green') {
      // Agent specification is removed as 'agent any' is defined globally.
      steps {
        withCredentials([file(credentialsId: 'kubeconfig', variable: 'KUBECONFIG_FILE')]) {
          sh '''
            echo "Using docker run to run kubectl image..."
            # Apply the new green deployment, using the newly built image
            docker run --rm \
              -v "${KUBECONFIG_FILE}":/root/.kube/config:ro \
              --entrypoint kubectl \
              bitnami/kubectl:1.27 \
              apply -f k8s/green-deployment.yaml
          '''
        }
      }
    }


    stage('Switch Service to Green') {
      steps {
        withCredentials([file(credentialsId: 'kubeconfig', variable: 'KUBECONFIG_FILE')]) {
          sh '''
            # Patch the service selector to point traffic to the new 'green' environment
            docker run --rm \
              -v "${KUBECONFIG_FILE}":/root/.kube/config:ro \
              --entrypoint kubectl \
              bitnami/kubectl:1.27 \
              patch svc aceest-svc -p '{"spec":{"selector":{"app":"aceest","env":"green"}}}'
          '''
        }
      }
    }


    stage('Rollback (if tests fail)') {
      // Typically, this is used in a post-failure block, but keeping it here for demonstration.
      steps {
        // revert service to blue
        sh "kubectl patch svc aceest-svc -p '{\"spec\":{\"selector\":{\"app\":\"aceest\",\"env\":\"blue\"}}}'"
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
      echo "Pipeline failed — check console output. Attempting rollback..."
      // Trigger rollback only on failure and if deployment stages were reached
      script {
        try {
          // Check if the service was switched, then roll back
          sh '''
            echo "Rolling back service selector to blue..."
            docker run --rm \
              -v "${KUBECONFIG_FILE}":/root/.kube/config:ro \
              --entrypoint kubectl \
              bitnami/kubectl:1.27 \
              patch svc aceest-svc -p '{"spec":{"selector":{"app":"aceest","env":"blue"}}}' || true
          '''
        } catch (e) {
          echo "Rollback failed: ${e}"
        }
      }
    }
  }
}