pipeline {
  agent any
  environment {
    DOCKERHUB_REPO = 'kalyanimuppidi01/ace-fitness-and-gym'
    SONARQUBE_SERVER = 'SonarQube'   // name configured in Jenkins
  }
  stages {
    stage('Checkout') {
      steps {
        checkout scm
      }
    }

    stage('Unit Tests') {
  steps {
    // debug: show where we are and what files exist
    sh '''
      echo "WORKSPACE = ${WORKSPACE}"
      echo "PWD = $(pwd)"
      echo "List workspace root:"
      ls -la "${WORKSPACE}" || true
      echo "List current dir:"
      ls -la . || true
    '''

    // run tests inside a python container, mounting the Jenkins workspace explicitly
    sh '''
      docker run --rm \
        -v "${WORKSPACE}":/usr/src \
        -w /usr/src \
        python:3.10-slim bash -c "ls -la && cat requirements.txt || true; pip install --no-cache-dir -r requirements.txt && pytest -q"
    '''
  }
}

}


    stage('SonarQube Analysis') {
      steps {
        withCredentials([string(credentialsId: 'sonar-token', variable: 'SONAR_TOKEN')]) {
          sh '''
            # install scanner if not installed
            docker run --rm \
              -v "${PWD}":/usr/src \
              -e SONAR_HOST_URL="http://sonarqube:9000" \
              -e SONAR_LOGIN="${SONAR_TOKEN}" \
              sonarsource/sonar-scanner-cli \
              -Dsonar.projectKey=aceest-fitness \
              -Dsonar.sources=. \
              -Dsonar.python.version=3.10
          '''
        }
      }
    }

    stage('Build Docker') {
      steps {
        script {
          // tag with git commit or git tag if present
          def tag = sh(script: "git describe --tags --abbrev=0 || echo 'v1.4'", returnStdout: true).trim()
          def image = "${DOCKERHUB_REPO}:${tag}"
          sh "docker build -t ${image} ."
          env.IMAGE_NAME = image
        }
      }
    }

    stage('Push Docker') {
      steps {
        withCredentials([usernamePassword(credentialsId: 'docker-hub-creds', passwordVariable: 'DOCKER_PASS', usernameVariable: 'DOCKER_USER')]) {
          sh '''
            echo "$DOCKER_PASS" | docker login -u "$DOCKER_USER" --password-stdin
            docker push ${IMAGE_NAME}
          '''
        }
      }
    }

    stage('Deploy (placeholder)') {
      steps {
        echo "Deployment stage would be here (k8s apply / helm / etc.)"
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
