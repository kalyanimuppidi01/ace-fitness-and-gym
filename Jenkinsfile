pipeline {
  agent any
  environment {
    DOCKER_IMAGE = "aceest/fitness"
  }
  stages {
    stage('Checkout') {
      steps {
        checkout scm
      }
    }
    stage('Unit Tests') {
      steps {
        sh 'pytest -q'
        // publish test results later
      }
    }
    stage('Build Docker') {
      steps {
        sh "docker build -t ${DOCKER_IMAGE}:${GIT_COMMIT} ."
      }
    }
    stage('Push Docker') {
      steps {
        // login credential binding required in Jenkins
        // sh "docker push ${DOCKER_IMAGE}:${GIT_COMMIT}"
        echo "Docker push would go here"
      }
    }
  }
  post {
    always {
      archiveArtifacts artifacts: 'reports/**', fingerprint: true
    }
  }
}
