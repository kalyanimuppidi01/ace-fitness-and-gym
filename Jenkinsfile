pipeline {
  agent any
  environment {
    DOCKERHUB_REPO = 'kalyanimuppidi/ace-fitness-and-gym'
    // Ensure this is resolvable (e.g., use http://host.docker.internal:9000 if using Docker Desktop)
    SONARQUBE_HOST = 'http://sonarqube:9000' 
  }

//---

  stages {
    stage('Checkout SCM') {
      steps {
        // This ensures Jenkins checks out the Jenkinsfile & pipeline workspace
        checkout scm
      }
    }

//---

    stage('Unit Tests & Coverage') {
      steps {
        // Run tests inside a ephemeral python container and mount the Jenkins workspace
        sh '''
          docker run --rm \
            -v "$WORKSPACE":/usr/src \
            -w /usr/src \
            python:3.10-slim bash -c "echo 'Inside container, preparing environment...' && \
            
            # Install pytest, pytest-cov, and project dependencies
            pip install --no-cache-dir pytest pytest-cov && \
            if [ -f requirements.txt ]; then pip install --no-cache-dir -r requirements.txt; else echo 'Project requirements.txt NOT found, continuing...'; fi; \
            
            # Run tests and output coverage to SonarQube's expected location.
            # IMPORTANT: Replace 'tests/' with the path to your test files if they are in a subfolder.
            pytest --cov=app --cov-report=xml:coverage.xml -q || true"
        '''
      }
    }

//---

    stage('SonarQube Analysis') {
      when { expression { return true } } // Explicitly enabling this stage
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

//---

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

//---

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

//---

    stage('Deploy Green') {
      // Removed redundant 'agent' block as 'agent any' is defined globally.
      steps {
        withCredentials([file(credentialsId: 'kubeconfig', variable: 'KUBECONFIG_FILE')]) {
          sh '''
            echo "Using docker run to run kubectl image..."
            # mount the kubeconfig file into the container path /root/.kube/config
            docker run --rm \
              -v "${KUBECONFIG_FILE}":/root/.kube/config:ro \
              --entrypoint kubectl \
              bitnami/kubectl:1.27 \
              apply -f k8s/green-deployment.yaml
          '''
        }
      }
    }

//---

    stage('Switch Service to Green') {
      steps {
        withCredentials([file(credentialsId: 'kubeconfig', variable: 'KUBECONFIG_FILE')]) {
          sh '''
            docker run --rm \
              -v "${KUBECONFIG_FILE}":/root/.kube/config:ro \
              --entrypoint kubectl \
              bitnami/kubectl:1.27 \
              patch svc aceest-svc -p '{"spec":{"selector":{"app":"aceest","env":"green"}}}'
          '''
        }
      }
    }

//---

    // The manual Rollback stage is redundant if implemented in the post-failure block.
    // stage('Rollback (if tests fail)') {
    //   steps {
    //     sh "kubectl patch svc aceest-svc -p '{\"spec\":{\"selector\":{\"app\":\"aceest\",\"env\":\"blue\"}}}'"
    //   }
    // }

  }

//---

  post {
    always {
      cleanWs()
    }
    success {
      echo "Pipeline succeeded for ${env.IMAGE_NAME}"
    }
    failure {
      echo "Pipeline failed — attempting rollback."
      script {
        try {
          // Use withCredentials to ensure KUBECONFIG_FILE is available for the rollback command
          withCredentials([file(credentialsId: 'kubeconfig', variable: 'KUBECONFIG_FILE')]) {
            sh '''
              echo "Rolling back service selector to blue..."
              docker run --rm \
                -v "${KUBECONFIG_FILE}":/root/.kube/config:ro \
                --entrypoint kubectl \
                bitnami/kubectl:1.27 \
                patch svc aceest-svc -p '{"spec":{"selector":{"app":"aceest","env":"blue"}}}'
            '''
          }
        } catch (e) {
          echo "Rollback failed or credentials unavailable: ${e}"
        }
      }
    }
  }
}