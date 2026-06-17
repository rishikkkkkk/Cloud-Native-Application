# DevOps Portfolio Project — AWS EKS Full Stack

Production-grade DevOps project showcasing EKS, Terraform, Helm, CI/CD, observability, and centralized logging.

## Stack
- **Cloud**: AWS (ap-south-1)
- **IaC**: Terraform
- **Container Orchestration**: AWS EKS + Helm
- **CI/CD**: GitHub Actions
- **Monitoring**: Prometheus + Grafana
- **Logging**: EFK (Elasticsearch + Fluentd + Kibana)
- **Registry**: DockerHub
- **Notifications**: Slack Webhooks

## Project Structure
```
devops-portfolio/
├── app/                        # Dockerized web application
├── helm/devops-app/            # Helm chart with dev/prod values
├── terraform/
│   ├── modules/
│   │   ├── vpc/               # VPC, subnets, IGW, NAT
│   │   ├── eks/               # EKS cluster + node groups
│   │   ├── iam/               # IAM roles & policies
│   │   └── security-groups/   # Security group definitions
│   └── environments/
│       ├── dev/               # Dev tfvars + backend
│       └── prod/              # Prod tfvars + backend
├── monitoring/
│   ├── prometheus/            # Prometheus config & rules
│   └── grafana/               # Grafana dashboards
├── logging/efk/               # EFK stack manifests
└── .github/workflows/         # CI/CD pipelines
```

## Quick Start

### 1. Prerequisites
```bash
aws configure  # Set up AWS credentials
terraform -version  # >= 1.5
helm version        # >= 3.12
kubectl version     # >= 1.28
```

### 2. Deploy Infrastructure
```bash
cd terraform/environments/dev
terraform init
terraform plan
terraform apply
```

### 3. Configure kubectl
```bash
aws eks update-kubeconfig --region ap-south-1 --name devops-portfolio-dev
```

### 4. Deploy App via Helm
```bash
helm upgrade --install devops-app ./helm/devops-app \
  -f helm/devops-app/environments/dev/values.yaml \
  --namespace dev --create-namespace
```

### 5. Install Monitoring
```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm upgrade --install kube-prometheus-stack prometheus-community/kube-prometheus-stack \
  -f monitoring/prometheus/values.yaml --namespace monitoring --create-namespace
```

### 6. Install EFK Logging
```bash
kubectl apply -f logging/efk/
```

## GitHub Actions Secrets Required
| Secret | Description |
|--------|-------------|
| `AWS_ACCESS_KEY_ID` | AWS access key |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key |
| `DOCKERHUB_USERNAME` | DockerHub username |
| `DOCKERHUB_TOKEN` | DockerHub access token |
| `SLACK_WEBHOOK_URL` | Slack incoming webhook URL |
| `KUBECONFIG_DEV` | base64-encoded kubeconfig for dev cluster |
| `KUBECONFIG_PROD` | base64-encoded kubeconfig for prod cluster |
