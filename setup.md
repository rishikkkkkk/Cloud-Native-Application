# End-to-End DevOps Pipeline on AWS EKS — Setup Guide

![AWS](https://img.shields.io/badge/AWS-EKS%20%7C%20EC2%20%7C%20IAM-FF9900?style=for-the-badge&logo=amazonaws&logoColor=white)
![Terraform](https://img.shields.io/badge/Terraform-IaC-7B42BC?style=for-the-badge&logo=terraform&logoColor=white)
![Kubernetes](https://img.shields.io/badge/Kubernetes-v1.32-326CE5?style=for-the-badge&logo=kubernetes&logoColor=white)
![Helm](https://img.shields.io/badge/Helm-v3.12+-0F1689?style=for-the-badge&logo=helm&logoColor=white)
![GitHub Actions](https://img.shields.io/badge/GitHub_Actions-CI%2FCD-2088FF?style=for-the-badge&logo=githubactions&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Containers-2496ED?style=for-the-badge&logo=docker&logoColor=white)

---

# End-to-End DevOps Pipeline on AWS EKS

This guide walks you through deploying the complete DevOps platform from scratch on your own AWS account.

By the end of this guide you'll have:

- AWS infrastructure provisioned using Terraform
- Amazon EKS Kubernetes cluster
- FastAPI application deployed using Helm
- Docker images hosted on DockerHub
- CI/CD with GitHub Actions
- Prometheus + Grafana monitoring
- EFK centralized logging
- Slack deployment notifications

---

# Architecture

```text
                        GitHub
                           │
                           │ Push
                           ▼
                  GitHub Actions CI/CD
                           │
      ┌────────────────────┼─────────────────────┐
      │                    │                     │
      ▼                    ▼                     ▼
 Docker Build        Terraform Apply      Slack Notification
      │
      ▼
 DockerHub Registry
      │
      ▼
 Amazon EKS Cluster
      │
      ▼
 Helm Upgrade --install
      │
      ▼
 FastAPI Application
      │
 ┌────┴─────────────┐
 │                  │
 ▼                  ▼
Prometheus      Fluentd
 │                  │
 ▼                  ▼
Grafana      Elasticsearch
                  │
                  ▼
               Kibana
```

---

# Prerequisites

Install the following tools before starting.

| Tool | Minimum Version |
|-------|-----------------|
| Terraform | >= 1.5 |
| kubectl | >= 1.28 |
| Helm | >= 3.12 |
| AWS CLI | Version 2 |
| Docker | Latest |
| Git | Latest |

---

## Verify Installation

Terraform

```bash
terraform version
```

kubectl

```bash
kubectl version --client
```

Helm

```bash
helm version
```

AWS CLI

```bash
aws --version
```

Docker

```bash
docker --version
```

Git

```bash
git --version
```

---

# AWS Account Setup

## 1. Create an AWS Account

If you don't already have one, create an AWS account.

Once your account is ready:

- Enable MFA on the root account.
- Never use the root account for deployments.
- Create a dedicated IAM user for Terraform and GitHub Actions.

---

## 2. Create an IAM User

Navigate to:

```
AWS Console
→ IAM
→ Users
→ Create User
```

Example:

```
Username:
terraform-admin
```

Enable:

- Programmatic Access

---

## 3. Attach Permissions

For learning purposes you can attach:

```
AdministratorAccess
```

For production deployments, use least-privilege policies instead.

The IAM user must be able to manage:

- EKS
- EC2
- VPC
- IAM
- Route53 (optional)
- CloudWatch
- Elastic Load Balancer
- Auto Scaling
- Security Groups
- S3
- DynamoDB

---

## 4. Generate Access Keys

Open the IAM user.

Navigate to

```
Security Credentials
```

Create an Access Key.

Save:

```
AWS_ACCESS_KEY_ID

AWS_SECRET_ACCESS_KEY
```

You'll need these later for:

- Local Terraform
- GitHub Actions Secrets

---

# Billing Alert (Highly Recommended)

Although this is a portfolio project, AWS resources can incur charges.

Create a billing alarm before provisioning infrastructure.

Suggested monthly budget:

```
$25
```

Enable notifications through Amazon SNS so you receive an email if your estimated charges exceed the budget.

---

# Clone the Repository

Fork this repository into your own GitHub account.

Then clone it.

```bash
git clone https://github.com/<your-username>/devops-portfolio.git

cd devops-portfolio
```

Verify the repository structure.

```text
devops-portfolio/
│
├── app/
├── helm/
├── terraform/
├── monitoring/
├── logging/
├── .github/
├── Makefile
└── README.md
```

---

# Configure Git

```bash
git config --global user.name "Your Name"

git config --global user.email "you@example.com"
```

---

# Create a Working Branch

Never work directly on `main`.

Create a development branch.

```bash
git checkout -b develop
```

Future workflow:

```
develop
    │
    ▼

GitHub Actions

    │
    ▼

Development Environment

-----------------------------

main

    │
    ▼

GitHub Actions

    │
    ▼

Production Environment
```

---

# Configure DockerHub

Create a DockerHub account if you don't already have one.

Create a public repository.

Example:

```
username/devops-app
```

This repository will store the Docker images built by GitHub Actions.

You'll configure the DockerHub credentials later as GitHub repository secrets.

---

# Project Environments

This project deploys two independent environments.

| Environment | Namespace | Node Type | Capacity Type |
|-------------|-----------|-----------|---------------|
| Development | dev | t3.medium | SPOT |
| Production | prod | t3.large | ON_DEMAND |

Development is intended for feature testing, while Production hosts the stable application.

---

---

# Configure AWS Credentials

Before provisioning infrastructure, configure the AWS CLI with the IAM user's access keys.

Run:

```bash
aws configure
```

You'll be prompted to enter:

```text
AWS Access Key ID [None]: <YOUR_ACCESS_KEY_ID>
AWS Secret Access Key [None]: <YOUR_SECRET_ACCESS_KEY>
Default region name [None]: ap-south-1
Default output format [None]: json
```

Verify the configuration:

```bash
aws sts get-caller-identity
```

Expected output:

```json
{
  "UserId": "AIDXXXXXXXXXXXX",
  "Account": "123456789012",
  "Arn": "arn:aws:iam::123456789012:user/terraform-admin"
}
```

If this command succeeds, your local machine is authenticated with AWS.

---

# Configure Terraform Remote State

Terraform state should **never** be stored locally for collaborative or production environments.

This project uses:

| Resource | Purpose |
|----------|---------|
| Amazon S3 | Store Terraform state |
| DynamoDB | State locking |

---

## Step 1 — Create an S3 Bucket

Choose a globally unique bucket name.

Example:

```text
rishit-devops-terraform-state
```

Create the bucket:

```bash
aws s3api create-bucket \
  --bucket rishit-devops-terraform-state \
  --region ap-south-1 \
  --create-bucket-configuration LocationConstraint=ap-south-1
```

Enable versioning:

```bash
aws s3api put-bucket-versioning \
  --bucket rishit-devops-terraform-state \
  --versioning-configuration Status=Enabled
```

Enable server-side encryption:

```bash
aws s3api put-bucket-encryption \
  --bucket rishit-devops-terraform-state \
  --server-side-encryption-configuration \
'{
  "Rules":[{
    "ApplyServerSideEncryptionByDefault":{
      "SSEAlgorithm":"AES256"
    }
  }]
}'
```

---

## Step 2 — Create DynamoDB Lock Table

Terraform uses DynamoDB to prevent multiple users from modifying infrastructure simultaneously.

Create the table:

```bash
aws dynamodb create-table \
    --table-name terraform-locks \
    --attribute-definitions AttributeName=LockID,AttributeType=S \
    --key-schema AttributeName=LockID,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST \
    --region ap-south-1
```

Verify:

```bash
aws dynamodb list-tables
```

Expected:

```text
terraform-locks
```

---

# Configure Terraform Backend

Navigate to the environment folder.

Development:

```bash
cd terraform/environments/dev
```

Production:

```bash
cd terraform/environments/prod
```

Update the backend configuration.

Example:

```hcl
terraform {
  backend "s3" {
    bucket         = "rishit-devops-terraform-state"
    key            = "dev/terraform.tfstate"
    region         = "ap-south-1"
    dynamodb_table = "terraform-locks"
    encrypt        = true
  }
}
```

Initialize Terraform:

```bash
terraform init
```

You should see:

```text
Terraform has been successfully initialized!
```

---

# Update Placeholder Values

Before deploying, replace all placeholder values throughout the project.

Search for:

```text
<your-dockerhub-username>
<your-aws-account-id>
<bucket-name>
<slack-webhook>
```

Update the following files if applicable:

| File | Update |
|------|--------|
| terraform.tfvars | Bucket names, region, cluster name |
| backend.tf | S3 bucket & DynamoDB table |
| GitHub Actions | DockerHub image name |
| Helm values | Image repository |
| Makefile | Cluster/environment variables |

Example Helm values:

```yaml
image:
  repository: your-dockerhub-username/devops-app
  tag: latest
```

Example GitHub Actions environment variable:

```yaml
IMAGE_NAME: your-dockerhub-username/devops-app
```

---

# GitHub Repository Secrets

The CI/CD pipeline uses GitHub Actions secrets for authentication.

Navigate to:

```text
Repository

↓

Settings

↓

Secrets and Variables

↓

Actions

↓

New Repository Secret
```

Create the following secrets:

| Secret | Description |
|---------|-------------|
| AWS_ACCESS_KEY_ID | IAM User Access Key |
| AWS_SECRET_ACCESS_KEY | IAM User Secret Key |
| DOCKERHUB_USERNAME | DockerHub username |
| DOCKERHUB_TOKEN | DockerHub access token |
| SLACK_WEBHOOK_URL | Slack Incoming Webhook |

Example:

```text
AWS_ACCESS_KEY_ID=AKIAXXXXXXXXXXXXX

AWS_SECRET_ACCESS_KEY=xxxxxxxxxxxxxxxxxxxxxxxx

DOCKERHUB_USERNAME=mydockerhub

DOCKERHUB_TOKEN=dckr_pat_xxxxxxxxxxxxx

SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
```

> **Note:** This project dynamically generates the Kubernetes configuration during the CI/CD pipeline using:

```bash
aws eks update-kubeconfig
```

Because of this, **no static `KUBECONFIG` secret is required**.

---

# Generate a DockerHub Access Token

Instead of using your DockerHub password, create a Personal Access Token.

1. Log in to DockerHub.
2. Go to **Account Settings** → **Personal Access Tokens**.
3. Click **Generate New Token**.
4. Give it a name such as:

```text
github-actions
```

5. Copy the generated token and save it as the `DOCKERHUB_TOKEN` GitHub secret.

This token will be used by GitHub Actions to authenticate and push container images securely.

---

# Validate Your Configuration

Before creating infrastructure, verify that everything is configured correctly.

### AWS CLI

```bash
aws sts get-caller-identity
```

### Terraform

```bash
terraform init
terraform validate
```

### Docker

```bash
docker login
```

### Kubernetes (will work after cluster creation)

```bash
kubectl version --client
```

If all commands complete successfully, you're ready to provision the AWS infrastructure.

---

---

# Deploy the Development Infrastructure

With the prerequisites complete, you can now provision the AWS infrastructure for the development environment.

Navigate to the Terraform development environment:

```bash
cd terraform/environments/dev
```

Initialize Terraform (if not already initialized):

```bash
terraform init
```

Validate the configuration:

```bash
terraform validate
```

Preview the infrastructure changes:

```bash
terraform plan
```

If the plan looks correct, apply the infrastructure:

```bash
terraform apply
```

When prompted:

```text
Do you want to perform these actions?
```

Enter:

```text
yes
```

Terraform will provision resources including:

- VPC
- Public and Private Subnets
- Internet Gateway
- NAT Gateway
- Route Tables
- Security Groups
- IAM Roles
- EKS Cluster
- Managed Node Group

This process typically takes **15–25 minutes**, depending on AWS provisioning times.

---

# Verify Terraform Outputs

Once provisioning is complete, Terraform will display outputs similar to:

```text
cluster_name = devops-eks-dev

cluster_endpoint = https://XXXXXXXX.gr7.ap-south-1.eks.amazonaws.com

cluster_security_group = sg-xxxxxxxx

vpc_id = vpc-xxxxxxxx
```

You can retrieve the outputs again at any time:

```bash
terraform output
```

---

# Configure kubectl

Generate a kubeconfig file for your newly created EKS cluster.

```bash
aws eks update-kubeconfig \
    --region ap-south-1 \
    --name devops-eks-dev
```

Expected output:

```text
Added new context arn:aws:eks:ap-south-1:xxxxxxxxxxxx:cluster/devops-eks-dev
```

> **Note:** The GitHub Actions workflow performs this step automatically during deployments, so no static kubeconfig file or GitHub secret is required.

---

# Verify Cluster Connectivity

Check the current Kubernetes context:

```bash
kubectl config current-context
```

List cluster nodes:

```bash
kubectl get nodes
```

Expected output:

```text
NAME                                           STATUS   ROLES    AGE
ip-10-0-1-25.ap-south-1.compute.internal        Ready    <none>
ip-10-0-2-37.ap-south-1.compute.internal        Ready    <none>
```

Verify system pods:

```bash
kubectl get pods -A
```

You should see pods from namespaces such as:

```text
kube-system
aws-node
coredns
kube-proxy
```

---

# Create the Development Namespace

```bash
kubectl create namespace dev
```

Verify:

```bash
kubectl get namespaces
```

Expected:

```text
default
kube-system
dev
```

---

# Build the Docker Image (Optional)

If you want to test the application locally before using GitHub Actions:

Navigate to the application directory:

```bash
cd app
```

Build the image:

```bash
docker build -t your-dockerhub-username/devops-app:latest .
```

Run the container:

```bash
docker run -p 8000:8000 your-dockerhub-username/devops-app:latest
```

Open your browser:

```text
http://localhost:8000/docs
```

You should see the FastAPI Swagger UI.

Stop the container after testing.

---

# Push the Image to DockerHub (Manual)

Authenticate with DockerHub:

```bash
docker login
```

Push the image:

```bash
docker push your-dockerhub-username/devops-app:latest
```

> **Note:** In normal day-to-day development, GitHub Actions automatically builds and pushes the Docker image. Manual pushes are only required for local testing.

---

# Deploy the Application with Helm

Navigate to the Helm chart:

```bash
cd helm/devops-app
```

Deploy the application to the development namespace:

```bash
helm upgrade \
    --install devops-app . \
    -f environments/dev/values.yaml \
    --namespace dev \
    --create-namespace
```

Expected output:

```text
Release "devops-app" has been upgraded.

STATUS: deployed
```

---

# Verify the Helm Release

List installed releases:

```bash
helm list -n dev
```

Example:

```text
NAME         NAMESPACE   STATUS
devops-app   dev         deployed
```

Check the pods:

```bash
kubectl get pods -n dev
```

Expected:

```text
NAME                                  READY   STATUS
devops-app-7d84d95c67-kq2ht           1/1     Running
```

Check the deployment:

```bash
kubectl get deployments -n dev
```

Check the service:

```bash
kubectl get svc -n dev
```

---

# Verify the Application

If using a LoadBalancer service:

```bash
kubectl get svc -n dev
```

Wait until an external IP or hostname is assigned.

Example:

```text
EXTERNAL-IP

a1b2c3d4e5f6.ap-south-1.elb.amazonaws.com
```

Open:

```text
http://<EXTERNAL-IP>/docs
```

or

```text
http://<LOADBALANCER-HOSTNAME>/docs
```

If using a ClusterIP service, port-forward locally:

```bash
kubectl port-forward svc/devops-app 8000:80 -n dev
```

Then open:

```text
http://localhost:8000/docs
```

---

# Health Checks

Verify the application's health endpoint:

```bash
curl http://localhost:8000/health
```

Example response:

```json
{
  "status": "healthy"
}
```

Readiness endpoint:

```bash
curl http://localhost:8000/ready
```

Metrics endpoint (used by Prometheus):

```bash
curl http://localhost:8000/metrics
```

---

# Verify Kubernetes Resources

Check all resources in the development namespace:

```bash
kubectl get all -n dev
```

Example:

```text
deployment.apps/devops-app

replicaset.apps/devops-app

pod/devops-app-xxxx

service/devops-app
```

Describe the deployment:

```bash
kubectl describe deployment devops-app -n dev
```

Inspect pod logs:

```bash
kubectl logs deployment/devops-app -n dev
```

If your deployment includes an HPA (Horizontal Pod Autoscaler), verify it:

```bash
kubectl get hpa -n dev
```

---

# Smoke Test Checklist

Before proceeding to monitoring and logging, confirm the following:

- ✅ Terraform completed successfully
- ✅ EKS cluster is running
- ✅ Worker nodes are in the `Ready` state
- ✅ `kubectl` connects to the cluster
- ✅ Helm release is deployed
- ✅ FastAPI pods are `Running`
- ✅ `/health` endpoint responds successfully
- ✅ `/metrics` endpoint is accessible
- ✅ Application logs are visible with `kubectl logs`

Once all checks pass, your application is successfully deployed and ready for observability.

---

---

# Install Monitoring (Prometheus + Grafana)

This project uses the **kube-prometheus-stack** Helm chart to provide:

- Prometheus
- Grafana
- Alertmanager
- Node Exporter
- kube-state-metrics

These components provide cluster health, application metrics, alerting, and visualization.

---

## Add the Prometheus Community Repository

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts

helm repo update
```

---

## Create the Monitoring Namespace

```bash
kubectl create namespace monitoring
```

---

## Install kube-prometheus-stack

```bash
helm upgrade \
    --install kube-prometheus-stack \
    prometheus-community/kube-prometheus-stack \
    --namespace monitoring \
    -f monitoring/prometheus/values.yaml
```

Verify the installation:

```bash
kubectl get pods -n monitoring
```

You should see components such as:

```text
prometheus

grafana

alertmanager

node-exporter

kube-state-metrics
```

---

# Verify Prometheus

Port-forward Prometheus:

```bash
kubectl port-forward svc/kube-prometheus-stack-prometheus 9090:9090 -n monitoring
```

Open:

```text
http://localhost:9090
```

Search for the following targets:

```text
up

kube_pod_info

container_cpu_usage_seconds_total
```

Ensure all targets report a status of **UP**.

---

# Access Grafana

Retrieve the Grafana admin password:

```bash
kubectl get secret \
kube-prometheus-stack-grafana \
-n monitoring \
-o jsonpath="{.data.admin-password}" | base64 --decode
```

Port-forward Grafana:

```bash
kubectl port-forward svc/kube-prometheus-stack-grafana \
3000:80 \
-n monitoring
```

Open:

```text
http://localhost:3000
```

Default credentials:

```text
Username:
admin

Password:
<decoded-password>
```

---

# Import Grafana Dashboards

The repository includes pre-configured dashboards located in:

```text
monitoring/grafana/
```

Import them from:

```
Grafana

↓

Dashboards

↓

Import

↓

Upload JSON
```

Example dashboards include:

- Kubernetes Cluster Overview
- Node Metrics
- Pod Resource Usage
- FastAPI Application Metrics
- HTTP Request Rate
- CPU Usage
- Memory Usage

---

# Install the EFK Logging Stack

This project uses:

| Component | Purpose |
|----------|---------|
| Elasticsearch | Store logs |
| Fluentd | Collect logs from Kubernetes nodes |
| Kibana | Search and visualize logs |

---

## Create the Logging Namespace

```bash
kubectl create namespace logging
```

---

## Deploy Elasticsearch

```bash
kubectl apply -f logging/efk/elasticsearch.yaml
```

Verify:

```bash
kubectl get pods -n logging
```

---

## Deploy Fluentd

```bash
kubectl apply -f logging/efk/fluentd.yaml
```

Fluentd runs as a DaemonSet, meaning one pod is scheduled on every worker node to collect container logs.

Verify:

```bash
kubectl get daemonsets -n logging
```

---

## Deploy Kibana

```bash
kubectl apply -f logging/efk/kibana.yaml
```

Verify:

```bash
kubectl get svc -n logging
```

---

# Access Kibana

Port-forward Kibana:

```bash
kubectl port-forward svc/kibana 5601:5601 -n logging
```

Open:

```text
http://localhost:5601
```

Create an index pattern for your logs if prompted.

Typical index:

```text
logstash-*
```

or

```text
fluentd-*
```

depending on your Fluentd configuration.

---

# Verify Log Collection

Generate application traffic:

```bash
curl http://localhost:8000/health
```

View the application logs:

```bash
kubectl logs deployment/devops-app -n dev
```

In Kibana:

1. Open **Discover**
2. Select the Fluentd index
3. Search for:

```text
kubernetes.namespace_name : "dev"
```

or

```text
kubernetes.container_name : "devops-app"
```

You should see logs from the FastAPI application.

---

# Validate the Complete Platform

At this stage, verify the following:

| Component | Status |
|----------|--------|
| Terraform | ✅ |
| VPC | ✅ |
| EKS Cluster | ✅ |
| Worker Nodes | ✅ |
| FastAPI Application | ✅ |
| Helm Release | ✅ |
| DockerHub Image | ✅ |
| Prometheus | ✅ |
| Grafana | ✅ |
| Elasticsearch | ✅ |
| Fluentd | ✅ |
| Kibana | ✅ |

---

# Cost Warning

> **⚠️ Running this project continuously will incur AWS charges.**

Approximate monthly costs (subject to AWS pricing changes):

| Resource | Estimated Cost |
|----------|----------------|
| EKS Control Plane | **~$0.10/hour (~$72/month)** |
| NAT Gateway | **~$32/month + data processing** |
| t3.medium (Dev SPOT Nodes) | Lower cost, varies by Spot pricing |
| t3.large (Prod ON_DEMAND Nodes) | Higher cost than t3.medium, billed hourly |
| Elastic Load Balancer | Additional hourly and data transfer charges |
| EBS Volumes | Based on allocated storage |
| CloudWatch Logs | Based on ingestion and retention |

> **Recommendation:** Destroy the infrastructure when not actively using it to avoid unnecessary charges.

---

# Destroy the Application

Remove the Helm release:

```bash
helm uninstall devops-app -n dev
```

Delete the development namespace:

```bash
kubectl delete namespace dev
```

---

# Destroy Monitoring

```bash
helm uninstall kube-prometheus-stack -n monitoring

kubectl delete namespace monitoring
```

---

# Destroy the EFK Stack

```bash
kubectl delete -f logging/efk/
```

Delete the logging namespace:

```bash
kubectl delete namespace logging
```

---

# Destroy AWS Infrastructure

Navigate to the Terraform environment:

```bash
cd terraform/environments/dev
```

Preview the destroy plan:

```bash
terraform plan -destroy
```

Destroy the infrastructure:

```bash
terraform destroy
```

Confirm:

```text
yes
```

Terraform will remove:

- EKS Cluster
- Node Groups
- VPC
- NAT Gateway
- Internet Gateway
- IAM Resources
- Security Groups
- Route Tables
- Subnets

> **Note:** The remote state S3 bucket and DynamoDB lock table are intentionally left intact. Delete them manually only if you no longer need Terraform state.

---

# Verify Cleanup

Ensure no EKS clusters remain:

```bash
aws eks list-clusters
```

List remaining EC2 instances:

```bash
aws ec2 describe-instances
```

List Load Balancers:

```bash
aws elbv2 describe-load-balancers
```

Verify no NAT Gateways remain:

```bash
aws ec2 describe-nat-gateways
```

Review your AWS Billing Dashboard to confirm that billable resources have been removed.

---
