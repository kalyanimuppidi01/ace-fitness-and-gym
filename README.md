# 🏋️‍♀️ ACE Fitness & Gym — CI/CD with Jenkins, Docker & Kubernetes

This project demonstrates a complete **CI/CD pipeline** for the `ace-fitness-and-gym` microservice application.
It integrates **Jenkins**, **SonarCloud**, **Docker Hub**, and **Kubernetes** to achieve automated build, test, analysis, and deployment workflows.

---

## 🚀 Tech Stack

| Category             | Technology                     |
| -------------------- | ------------------------------ |
| **Language**         | Python 3.10                    |
| **CI/CD**            | Jenkins (Declarative Pipeline) |
| **Code Quality**     | SonarCloud                     |
| **Containerization** | Docker & Docker Hub            |
| **Deployment**       | Kubernetes                     |
| **Testing**          | Pytest + Pytest-Cov            |

---

## 🧩 Architecture Overview

### CI/CD Flow

1. Jenkins triggers automatically on every commit to `main`.
2. Pipeline stages:

   * **Checkout SCM** — fetches latest source from GitHub.
   * **Unit Tests & Coverage** — runs Pytest inside a Python container.
   * **SonarCloud Analysis** — uploads metrics and coverage.
   * **Docker Build & Push** — builds versioned images and pushes to Docker Hub.
   * **Kubernetes Deployments** — uses Blue-Green, Canary, and Rolling strategies.

### Container Registry

All versions of the application are available on Docker Hub:
🔗 [https://hub.docker.com/repository/docker/kalyanimuppidi/ace-fitness-and-gym/general](https://hub.docker.com/repository/docker/kalyanimuppidi/ace-fitness-and-gym/general)

**Available Tags**

```
v1.0, v1.1, v1.2, v1.2.1, v1.2.2, v1.2.3, v1.3
```

---

## ⚙️ Jenkins Pipeline Highlights

```groovy
pipeline {
  agent any
  environment {
    DOCKERHUB_REPO = 'kalyanimuppidi/ace-fitness-and-gym'
    SONARCLOUD_HOST = 'https://sonarcloud.io'
  }

  stages {
    stage('Unit Tests & Coverage') {
      steps {
        sh '''
          docker run --rm -v "$WORKSPACE":/usr/src -w /usr/src \
          python:3.10-slim bash -c "pip install pytest pytest-cov && pytest --cov=app --cov-report=xml:coverage.xml -q"
        '''
      }
    }

    stage('SonarCloud Analysis') {
      steps {
        withCredentials([string(credentialsId: 'sonar-token', variable: 'SONAR_TOKEN')]) {
          sh '''
            docker run --rm -v "$WORKSPACE":/usr/src -w /usr/src \
            -e SONAR_HOST_URL="${SONARCLOUD_HOST}" -e SONAR_LOGIN="$SONAR_TOKEN" \
            sonarsource/sonar-scanner-cli \
            -Dsonar.projectKey=kalyanimuppidi01_ace-fitness-and-gym \
            -Dsonar.organization=kalyanimuppidi01 \
            -Dsonar.sources=. \
            -Dsonar.python.coverage.reportPaths=coverage.xml
          '''
        }
      }
    }

    stage('Build & Push Docker Image') {
      steps {
        script {
          def tag = sh(script: "git describe --tags --abbrev=0 || echo 'v1.4'", returnStdout: true).trim()
          def image = "${DOCKERHUB_REPO}:${tag}"
          sh "docker build -t ${image} ."
          withCredentials([usernamePassword(credentialsId: 'docker-hub-creds', usernameVariable: 'DOCKER_USER', passwordVariable: 'DOCKER_PASS')]) {
            sh '''
              echo "$DOCKER_PASS" | docker login -u "$DOCKER_USER" --password-stdin
              docker push ${image}
            '''
          }
        }
      }
    }
  }
}
```

---

## ☸️ Kubernetes Deployment Strategies

| Strategy           | Deployment Files                                | Service File         | Description                                                | Local Endpoint          |
| ------------------ | ----------------------------------------------- | -------------------- | ---------------------------------------------------------- | ----------------------- |
| **Blue-Green**     | `blue-deployment.yaml`, `green-deployment.yaml` | `bluegreen-svc.yaml` | Switch between blue and green versions with zero downtime. | `http://localhost:8081` |
| **Canary**         | `canary-deploy.yaml`                            | `canary-svc.yaml`    | Gradual rollout of new version alongside stable one.       | `http://localhost:8082` |
| **Rolling Update** | `deployment-v1.yaml`                            | `service.yaml`       | Sequentially updates pods without downtime.                | `http://localhost:8080` |
| **Stable**         | `stable-deploy.yaml`                            | `service.yaml`       | Baseline production deployment.                            | `http://localhost:8080` |

### Run locally

```bash
kubectl apply -f k8s/
kubectl port-forward svc/aceest-svc 8080:80
```

---

## 🧪 Test Coverage

Coverage is generated using:

```bash
pytest --cov=app --cov-report=xml:coverage.xml -q
```

Then uploaded to SonarCloud for detailed analysis:
🔗 [https://sonarcloud.io/project/overview?id=kalyanimuppidi01_ace-fitness-and-gym](https://sonarcloud.io/project/overview?id=kalyanimuppidi01_ace-fitness-and-gym)

---
This script:

* Builds Docker images for every version (`v1.0` → `v1.3`)
* Tags them correctly
* Pushes them to Docker Hub.

---

## 🔐 Jenkins Credentials Setup

| ID                 | Type              | Purpose                   |
| ------------------ | ----------------- | ------------------------- |
| `docker-hub-creds` | Username/Password | Docker Hub authentication |
| `sonar-token`      | Secret Text       | SonarCloud access token   |
| `kubeconfig`       | File              | Kubernetes cluster access |

---

## 💡 Key Challenges & Mitigations

| Challenge                      | Mitigation                                                    |
| ------------------------------ | ------------------------------------------------------------- |
| SonarCloud coverage XML errors | Adjusted `pytest --cov` output path and XML schema            |
| Jenkins missing Docker         | Mounted `/var/run/docker.sock` and verified agent permissions |
| kubeconfig mounting error      | Used dynamic filename resolution before volume mount          |
| System performance (CPU/heat)  | Stopped unused Docker containers & limited concurrency        |
| Authentication failures        | Used Sonar token via Jenkins credentials securely             |

---

## 🏁 Outcomes

✅ Fully automated **CI/CD pipeline**
✅ Multi-version **Docker image management**
✅ Continuous **SonarCloud code analysis**
✅ Zero-downtime **Kubernetes deployments**
✅ Verified **Blue-Green, Canary, and Rolling** rollout models

---

## 📍 Access Summary

| Component             | URL                                                                                                                                                                        |
| --------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Application (Stable)  | `http://localhost:8080`                                                                                                                                                    |
| Blue-Green            | `http://localhost:8081`                                                                                                                                                    |
| Canary                | `http://localhost:8082`                                                                                                                                                    |
| SonarCloud Dashboard  | [https://sonarcloud.io/project/overview?id=kalyanimuppidi01_ace-fitness-and-gym](https://sonarcloud.io/project/overview?id=kalyanimuppidi01_ace-fitness-and-gym)           |
| Jenkins Dashboard     | `http://localhost:8080`                                                                                                                                                    |
| Docker Hub Repository | [https://hub.docker.com/repository/docker/kalyanimuppidi/ace-fitness-and-gym/general](https://hub.docker.com/repository/docker/kalyanimuppidi/ace-fitness-and-gym/general) |

---

## 👩‍💻 Maintainer

**Kalyani Muppidi**
📧 [https://github.com/kalyanimuppidi01](https://github.com/kalyanimuppidi01)
🐳 [https://hub.docker.com/repository/docker/kalyanimuppidi/ace-fitness-and-gym/general](https://hub.docker.com/repository/docker/kalyanimuppidi/ace-fitness-and-gym/general)

---

Would you like me to generate this as a downloadable `README.md` file (so you can just drop it into your repo)?
