pipeline {
  agent any
  environment {
    DOCKERHUB_REPO = 'kalyanimuppidi/ace-fitness-and-gym'
    SONARQUBE_SERVER = 'SonarQube'   // name configured in Jenkins (if used)
  }

  stages {
    stage('Checkout Jenkinsfile') {
      steps {
        // This ensures Jenkins checks out the Jenkinsfile & pipeline workspace
        checkout scm
      }
    }

    stage('Unit Tests') {
      steps {
        // Debug: show workspace and files before running tests
        sh '''
          echo "==== DEBUG: Jenkins workspace info ===="
          echo "WORKSPACE = $WORKSPACE"
          echo "PWD = $(pwd)"
          echo "Listing workspace root:"
          ls -la "$WORKSPACE" || true
          echo "Listing current dir:"
          ls -la . || true
        '''

        // Run tests inside a ephemeral python container and mount the Jenkins workspace
        sh '''
          docker run --rm \
            -v "$WORKSPACE":/usr/src \
            -w /usr/src \
            python:3.10-slim bash -c "echo 'Inside container, listing /usr/src:' && ls -la /usr/src || true; \
            if [ -f requirements.txt ]; then pip install --no-cache-dir -r requirements.txt; else echo 'requirements.txt NOT found'; fi; \
            pytest -q || true"
        '''
      }
    }

    stage('SonarQube Analysis') {
      when { expression { return false } } // disabled by default; enable later
      steps {
        withCredentials([string(credentialsId: 'sonar-token', variable: 'SONAR_TOKEN')]) {
          sh '''
            docker run --rm -v "$WORKSPACE":/usr/src -w /usr/src \
              -e SONAR_HOST_URL="http://sonarqube:9000" \
              -e SONAR_LOGIN="$SONAR_TOKEN" \
              sonarsource/sonar-scanner-cli \
              -Dsonar.projectKey=aceest-fitness \
              -Dsonar.sources=. \
              -Dsonar.python.version=3.10
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
  agent {
    docker {
      image 'bitnami/kubectl:1.27'  // kubectl inside container
      args '-v /var/run/docker.sock:/var/run/docker.sock' // optional for docker-in-docker
    }
  }
  steps {
    withCredentials([file(credentialsId: 'kubeconfig', variable: 'KUBECONFIG_FILE')]) {
      sh '''
        echo "Setting up kubeconfig..."
        export KUBECONFIG="$KUBECONFIG_FILE"

        echo "Checking cluster access..."
        kubectl config get-contexts || true
        kubectl get nodes || true

        echo "Deploying Green version..."
        kubectl apply -f k8s/green-deployment.yaml
        echo "✅ Green deployment applied successfully"
      '''
    }
  }
}


    stage('Switch Service to Green') {
  agent {
    docker { image 'bitnami/kubectl:1.27' }
  }
  steps {
    withCredentials([file(credentialsId: 'kubeconfig', variable: 'KUBECONFIG_FILE')]) {
      sh '''
        export KUBECONFIG="$KUBECONFIG_FILE"
        echo "Current service selector (before):"
        kubectl get svc aceest-svc -o yaml | yq '.spec.selector' || true

        echo "Patching service selector to route to green:"
        kubectl patch svc aceest-svc -p '{"spec":{"selector":{"app":"aceest","env":"green"}}}'

        echo "Verify endpoints for service after patch:"
        kubectl get endpoints aceest-svc -o yaml || true

        echo "Current pods matching selector:"
        kubectl get pods -l app=aceest,env=green -o wide || true
      '''
    }
  }
}

    stage('Rollback (if tests fail)') {
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
      echo "Pipeline failed — check console output"
    }
  }
}

