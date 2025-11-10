# Networking AI Platform - Deployment Runbook

**Version:** 1.0
**Last Updated:** 2025-11-09
**Maintained By:** DevOps Team

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Infrastructure Setup](#infrastructure-setup)
3. [Docker Deployment](#docker-deployment)
4. [Kubernetes Deployment](#kubernetes-deployment)
5. [Monitoring Setup](#monitoring-setup)
6. [Security Configuration](#security-configuration)
7. [Operational Procedures](#operational-procedures)
8. [Troubleshooting](#troubleshooting)
9. [Rollback Procedures](#rollback-procedures)
10. [Disaster Recovery](#disaster-recovery)

---

## Prerequisites

### Required Tools

```bash
# Check versions
docker --version          # >= 24.0
docker-compose --version  # >= 2.20
kubectl version          # >= 1.28
helm version             # >= 3.12
```

### Required Access

- [ ] Kubernetes cluster access (kubeconfig file)
- [ ] Container registry access (Docker Hub, GCR, ECR)
- [ ] Cloud provider CLI (AWS CLI, gcloud, az)
- [ ] Secrets management access (Vault, AWS Secrets Manager)
- [ ] DNS management access
- [ ] Anthropic API key

### Required Knowledge

- Docker and containerization
- Kubernetes fundamentals
- Networking and load balancing
- PostgreSQL and Redis administration
- Security best practices

---

## Infrastructure Setup

### 1. Kubernetes Cluster Setup

#### Option A: Managed Kubernetes (Recommended)

**AWS EKS:**
```bash
# Create EKS cluster
eksctl create cluster \
  --name networking-ai-prod \
  --region us-east-1 \
  --nodegroup-name standard-workers \
  --node-type t3.xlarge \
  --nodes 3 \
  --nodes-min 3 \
  --nodes-max 10 \
  --managed

# Configure kubectl
aws eks update-kubeconfig --name networking-ai-prod --region us-east-1
```

**GKE:**
```bash
# Create GKE cluster
gcloud container clusters create networking-ai-prod \
  --num-nodes 3 \
  --machine-type n1-standard-4 \
  --region us-central1 \
  --enable-autoscaling \
  --min-nodes 3 \
  --max-nodes 10

# Get credentials
gcloud container clusters get-credentials networking-ai-prod --region us-central1
```

**Azure AKS:**
```bash
# Create AKS cluster
az aks create \
  --resource-group networking-ai-rg \
  --name networking-ai-prod \
  --node-count 3 \
  --node-vm-size Standard_D4s_v3 \
  --enable-cluster-autoscaler \
  --min-count 3 \
  --max-count 10

# Get credentials
az aks get-credentials --resource-group networking-ai-rg --name networking-ai-prod
```

#### Option B: Self-Hosted Kubernetes

Follow your organization's Kubernetes cluster provisioning guide.

### 2. Install Required Operators

#### Nginx Ingress Controller

```bash
# Add Helm repo
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo update

# Install Nginx Ingress
helm install nginx-ingress ingress-nginx/ingress-nginx \
  --namespace ingress-nginx \
  --create-namespace \
  --set controller.replicaCount=2 \
  --set controller.resources.requests.cpu=250m \
  --set controller.resources.requests.memory=512Mi
```

#### cert-manager (for SSL/TLS)

```bash
# Add Helm repo
helm repo add jetstack https://charts.jetstack.io
helm repo update

# Install cert-manager
helm install cert-manager jetstack/cert-manager \
  --namespace cert-manager \
  --create-namespace \
  --version v1.13.0 \
  --set installCRDs=true
```

#### Prometheus Operator (for monitoring)

```bash
# Add Helm repo
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

# Install kube-prometheus-stack
helm install prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace \
  --set prometheus.prometheusSpec.retention=30d \
  --set prometheus.prometheusSpec.storageSpec.volumeClaimTemplate.spec.resources.requests.storage=50Gi
```

### 3. DNS Configuration

```bash
# Get LoadBalancer IP/hostname
kubectl get svc -n ingress-nginx nginx-ingress-controller

# Configure DNS records:
# A    networking-ai.com          -> LoadBalancer IP
# A    api.networking-ai.com      -> LoadBalancer IP
# A    ws.networking-ai.com       -> LoadBalancer IP
# A    www.networking-ai.com      -> LoadBalancer IP
# CNAME *.networking-ai.com       -> networking-ai.com
```

---

## Docker Deployment

### Local Development

```bash
# 1. Clone repository
git clone https://github.com/yourusername/networking-ai.git
cd networking-ai

# 2. Create .env file
cp .env.example .env
# Edit .env and fill in values

# 3. Build and start services
docker-compose up -d --build

# 4. Check logs
docker-compose logs -f

# 5. Verify health
curl http://localhost:8000/health
curl http://localhost:8001/health
```

### Production Docker Compose

```bash
# 1. Create production environment file
cp .env.production.example .env.production
# Edit .env.production with actual values

# 2. Deploy production stack
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# 3. Run database migrations
docker-compose exec app alembic upgrade head

# 4. Verify deployment
docker-compose ps
docker-compose logs -f app
```

---

## Kubernetes Deployment

### Pre-Deployment Checklist

- [ ] Kubernetes cluster ready and accessible
- [ ] kubectl configured with correct context
- [ ] All required operators installed (Nginx, cert-manager, Prometheus)
- [ ] DNS records configured
- [ ] Secrets prepared (see below)
- [ ] Docker image built and pushed to registry
- [ ] Backup of current production (if updating)

### 1. Prepare Secrets

```bash
# Generate secure secrets
export POSTGRES_PASSWORD=$(openssl rand -hex 32)
export REDIS_PASSWORD=$(openssl rand -hex 32)
export SECRET_KEY=$(openssl rand -hex 32)
export JWT_SECRET_KEY=$(openssl rand -hex 32)

# Create secrets in Kubernetes
kubectl create namespace networking-ai

kubectl create secret generic networking-ai-secrets \
  --from-literal=POSTGRES_USER=postgres \
  --from-literal=POSTGRES_PASSWORD=$POSTGRES_PASSWORD \
  --from-literal=REDIS_PASSWORD=$REDIS_PASSWORD \
  --from-literal=ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY \
  --from-literal=SECRET_KEY=$SECRET_KEY \
  --from-literal=JWT_SECRET_KEY=$JWT_SECRET_KEY \
  --namespace networking-ai
```

### 2. Deploy Database Layer

```bash
# Deploy PostgreSQL StatefulSet
kubectl apply -f k8s/base/postgres-statefulset.yaml

# Wait for PostgreSQL to be ready
kubectl wait --for=condition=ready pod -l app=postgres -n networking-ai --timeout=5m

# Verify PostgreSQL
kubectl exec -it postgres-0 -n networking-ai -- psql -U postgres -c "SELECT version();"

# Deploy Redis StatefulSet
kubectl apply -f k8s/base/redis-statefulset.yaml

# Wait for Redis to be ready
kubectl wait --for=condition=ready pod -l app=redis -n networking-ai --timeout=5m

# Verify Redis
kubectl exec -it redis-0 -n networking-ai -- redis-cli ping
```

### 3. Run Database Migrations

```bash
# Create a migration job
cat <<EOF | kubectl apply -f -
apiVersion: batch/v1
kind: Job
metadata:
  name: db-migration
  namespace: networking-ai
spec:
  template:
    spec:
      containers:
      - name: migration
        image: networking-ai:latest
        command: ["alembic", "upgrade", "head"]
        envFrom:
        - configMapRef:
            name: networking-ai-config
        - secretRef:
            name: networking-ai-secrets
      restartPolicy: Never
  backoffLimit: 3
EOF

# Wait for migration to complete
kubectl wait --for=condition=complete --timeout=5m job/db-migration -n networking-ai

# Check migration logs
kubectl logs job/db-migration -n networking-ai
```

### 4. Deploy Application Layer

```bash
# Deploy ConfigMap
kubectl apply -f k8s/base/configmap.yaml

# Deploy FastAPI application
kubectl apply -f k8s/base/app-deployment.yaml

# Deploy WebSocket service
kubectl apply -f k8s/base/websocket-deployment.yaml

# Deploy Horizontal Pod Autoscalers
kubectl apply -f k8s/base/hpa.yaml

# Wait for deployments
kubectl wait --for=condition=available --timeout=5m deployment/fastapi -n networking-ai
kubectl wait --for=condition=available --timeout=5m deployment/websocket -n networking-ai

# Verify pods
kubectl get pods -n networking-ai
```

### 5. Configure Networking & Ingress

```bash
# Apply network policies
kubectl apply -f k8s/security/network-policies.yaml

# Create Let's Encrypt ClusterIssuer
cat <<EOF | kubectl apply -f -
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: admin@networking-ai.com
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
    - http01:
        ingress:
          class: nginx
EOF

# Deploy Ingress
kubectl apply -f k8s/base/ingress.yaml

# Wait for certificate
kubectl wait --for=condition=ready certificate/networking-ai-tls -n networking-ai --timeout=5m

# Verify certificate
kubectl describe certificate networking-ai-tls -n networking-ai
```

### 6. Deploy Monitoring

```bash
# Deploy ServiceMonitors
kubectl apply -f k8s/monitoring/servicemonitor.yaml

# Deploy Prometheus Rules
kubectl apply -f k8s/monitoring/prometheus-rules.yaml

# Access Grafana
kubectl port-forward -n monitoring svc/prometheus-grafana 3000:80
# Open http://localhost:3000 (default: admin/prom-operator)
```

### 7. Verification

```bash
# Check all pods
kubectl get pods -n networking-ai

# Check services
kubectl get svc -n networking-ai

# Check ingress
kubectl get ingress -n networking-ai

# Test health endpoints
curl https://api.networking-ai.com/health
curl https://ws.networking-ai.com/health

# Check logs
kubectl logs -l app=fastapi -n networking-ai --tail=100
kubectl logs -l app=websocket -n networking-ai --tail=100

# Check metrics
kubectl port-forward -n networking-ai svc/fastapi-service 9090:9090
curl http://localhost:9090/metrics
```

---

## Monitoring Setup

### Grafana Dashboards

#### 1. Import Pre-built Dashboards

```bash
# Port-forward to Grafana
kubectl port-forward -n monitoring svc/prometheus-grafana 3000:80

# Open browser: http://localhost:3000
# Login: admin / prom-operator (or check secret)

# Import dashboards:
# - Dashboard ID 1860: Node Exporter Full
# - Dashboard ID 6417: Kubernetes Cluster Monitoring
# - Dashboard ID 7362: PostgreSQL Database
# - Dashboard ID 11835: Redis Dashboard
```

#### 2. Custom Application Dashboard

Create dashboard with panels for:
- Request rate (RPS)
- Error rate (%)
- Response time (P50, P95, P99)
- WebSocket connections
- Database connection pool usage
- Redis memory usage
- Platform health score
- Pod CPU/Memory usage

### Alerting

#### Configure Alert Channels

```bash
# Add Slack webhook (example)
kubectl edit -n monitoring configmap/prometheus-grafana

# Add notification channel configuration
# See Grafana documentation for specific provider setup
```

#### Test Alerts

```bash
# Trigger test alert
kubectl run alert-test --image=busybox -n networking-ai \
  --restart=Never \
  --command -- sh -c "while true; do echo alert; done"

# Check alert manager
kubectl port-forward -n monitoring svc/prometheus-operated 9093:9093
# Open: http://localhost:9093
```

---

## Security Configuration

### RBAC

```bash
# Create service account with limited permissions
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: ServiceAccount
metadata:
  name: networking-ai-sa
  namespace: networking-ai
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: networking-ai-role
  namespace: networking-ai
rules:
- apiGroups: [""]
  resources: ["pods", "services"]
  verbs: ["get", "list", "watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: networking-ai-rolebinding
  namespace: networking-ai
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: networking-ai-role
subjects:
- kind: ServiceAccount
  name: networking-ai-sa
  namespace: networking-ai
EOF
```

### Pod Security Standards

```bash
# Apply pod security standards
kubectl label namespace networking-ai \
  pod-security.kubernetes.io/enforce=restricted \
  pod-security.kubernetes.io/audit=restricted \
  pod-security.kubernetes.io/warn=restricted
```

### Secrets Encryption at Rest

Enable encryption at rest for secrets (cluster-level configuration).

**AWS EKS:**
```bash
# Enable secrets encryption
aws eks associate-encryption-config \
  --cluster-name networking-ai-prod \
  --encryption-config '[{"resources":["secrets"],"provider":{"keyArn":"<KMS_KEY_ARN>"}}]'
```

---

## Operational Procedures

### Scaling

#### Manual Scaling

```bash
# Scale FastAPI deployment
kubectl scale deployment/fastapi --replicas=5 -n networking-ai

# Scale WebSocket deployment
kubectl scale deployment/websocket --replicas=4 -n networking-ai
```

#### HPA Configuration

HPA is already configured in `k8s/base/hpa.yaml`. Monitor with:

```bash
kubectl get hpa -n networking-ai
kubectl describe hpa fastapi-hpa -n networking-ai
```

### Rolling Updates

```bash
# Update image
kubectl set image deployment/fastapi \
  fastapi=networking-ai:v1.2.0 \
  -n networking-ai

# Watch rollout
kubectl rollout status deployment/fastapi -n networking-ai

# Check rollout history
kubectl rollout history deployment/fastapi -n networking-ai
```

### Database Maintenance

#### Backup

```bash
# Create backup
kubectl exec -it postgres-0 -n networking-ai -- \
  pg_dump -U postgres networking_ai | \
  gzip > backup-$(date +%Y%m%d-%H%M%S).sql.gz

# Upload to S3 (example)
aws s3 cp backup-*.sql.gz s3://networking-ai-backups/
```

#### Restore

```bash
# Download backup
aws s3 cp s3://networking-ai-backups/backup-20250109-120000.sql.gz .

# Restore database
gunzip backup-20250109-120000.sql.gz
kubectl exec -i postgres-0 -n networking-ai -- \
  psql -U postgres networking_ai < backup-20250109-120000.sql
```

### Log Management

#### View Logs

```bash
# Application logs
kubectl logs -l app=fastapi -n networking-ai --tail=100 -f

# WebSocket logs
kubectl logs -l app=websocket -n networking-ai --tail=100 -f

# All pods in namespace
kubectl logs -n networking-ai --all-containers=true --tail=100 -f
```

#### Export Logs

```bash
# Export logs from last hour
kubectl logs -l app=fastapi -n networking-ai \
  --since=1h > fastapi-logs-$(date +%Y%m%d-%H%M%S).log
```

---

## Troubleshooting

### Common Issues

#### 1. Pods Not Starting

```bash
# Check pod status
kubectl get pods -n networking-ai

# Describe pod for events
kubectl describe pod <pod-name> -n networking-ai

# Check logs
kubectl logs <pod-name> -n networking-ai

# Common causes:
# - Image pull errors: Check registry access
# - Resource limits: Check node resources
# - Config errors: Verify ConfigMap and Secrets
```

#### 2. Database Connection Issues

```bash
# Check PostgreSQL pod
kubectl get pod -l app=postgres -n networking-ai

# Test connection from app pod
kubectl exec -it <fastapi-pod> -n networking-ai -- \
  psql -h postgres-service -U postgres -d networking_ai

# Check network policy
kubectl describe networkpolicy -n networking-ai
```

#### 3. High Latency

```bash
# Check resource usage
kubectl top pods -n networking-ai

# Check HPA status
kubectl get hpa -n networking-ai

# Check database performance
kubectl exec -it postgres-0 -n networking-ai -- \
  psql -U postgres -c "SELECT * FROM pg_stat_activity;"

# Check Redis performance
kubectl exec -it redis-0 -n networking-ai -- \
  redis-cli info stats
```

#### 4. Certificate Issues

```bash
# Check certificate status
kubectl describe certificate networking-ai-tls -n networking-ai

# Check cert-manager logs
kubectl logs -n cert-manager deployment/cert-manager

# Check challenge
kubectl get challenges -n networking-ai

# Manually trigger renewal
kubectl delete secret networking-ai-tls -n networking-ai
# cert-manager will recreate it
```

### Debug Commands

```bash
# Run debug pod
kubectl run debug --image=nicolaka/netshoot -it --rm -n networking-ai -- /bin/bash

# Check DNS resolution
nslookup postgres-service.networking-ai.svc.cluster.local

# Check network connectivity
curl http://fastapi-service:8000/health
nc -zv postgres-service 5432

# Check TLS
openssl s_client -connect networking-ai.com:443 -servername networking-ai.com
```

---

## Rollback Procedures

### Rollback Deployment

```bash
# View rollout history
kubectl rollout history deployment/fastapi -n networking-ai

# Rollback to previous version
kubectl rollout undo deployment/fastapi -n networking-ai

# Rollback to specific revision
kubectl rollout undo deployment/fastapi --to-revision=3 -n networking-ai

# Verify rollback
kubectl rollout status deployment/fastapi -n networking-ai
```

### Emergency Rollback (Production)

```bash
# 1. Stop new deployments
kubectl scale deployment/fastapi-green --replicas=0 -n networking-ai

# 2. Switch traffic back to blue
kubectl patch service fastapi-service -n networking-ai \
  -p '{"spec":{"selector":{"version":"blue"}}}'

# 3. Scale up blue if needed
kubectl scale deployment/fastapi --replicas=3 -n networking-ai

# 4. Verify health
curl https://api.networking-ai.com/health

# 5. Investigate issue
kubectl logs -l app=fastapi,version=green -n networking-ai
```

---

## Disaster Recovery

### Backup Strategy

#### Automated Backups

```bash
# Create CronJob for automated backups
cat <<EOF | kubectl apply -f -
apiVersion: batch/v1
kind: CronJob
metadata:
  name: postgres-backup
  namespace: networking-ai
spec:
  schedule: "0 2 * * *"  # Daily at 2 AM
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: backup
            image: postgres:16-alpine
            command:
            - /bin/sh
            - -c
            - |
              pg_dump -h postgres-service -U postgres networking_ai | \
              gzip > /backup/backup-\$(date +%Y%m%d-%H%M%S).sql.gz
              # Upload to S3/GCS/Azure Blob
            envFrom:
            - secretRef:
                name: networking-ai-secrets
            volumeMounts:
            - name: backup
              mountPath: /backup
          volumes:
          - name: backup
            persistentVolumeClaim:
              claimName: backup-pvc
          restartPolicy: OnFailure
EOF
```

### Recovery Procedures

#### Full Cluster Recovery

1. **Provision new cluster** (see Infrastructure Setup)
2. **Install operators** (Nginx, cert-manager, Prometheus)
3. **Restore secrets** from backup or secrets manager
4. **Deploy database layer** and restore data
5. **Deploy application layer**
6. **Verify health** and switch DNS

#### Data Recovery

```bash
# 1. Stop application pods
kubectl scale deployment/fastapi --replicas=0 -n networking-ai
kubectl scale deployment/websocket --replicas=0 -n networking-ai

# 2. Restore database
# (See Database Maintenance - Restore section)

# 3. Restart application pods
kubectl scale deployment/fastapi --replicas=3 -n networking-ai
kubectl scale deployment/websocket --replicas=2 -n networking-ai

# 4. Verify data integrity
kubectl exec -it <fastapi-pod> -n networking-ai -- \
  python -m networking_ai.scripts.verify_data
```

---

## Maintenance Windows

### Scheduled Maintenance

1. **Announce maintenance** (24-48 hours notice)
2. **Scale down traffic** (if possible)
3. **Perform maintenance**
4. **Run smoke tests**
5. **Scale up and monitor**
6. **Announce completion**

### Zero-Downtime Updates

Use blue-green or canary deployment strategies (see CI/CD pipeline in `.github/workflows/deploy.yml`).

---

## Contact & Escalation

- **DevOps Team:** devops@networking-ai.com
- **On-Call:** [PagerDuty link]
- **Incident Response:** [Incident management tool]
- **Documentation:** https://docs.networking-ai.com

---

## Appendix

### Useful Commands Cheat Sheet

```bash
# Namespace shortcuts
alias kn='kubectl -n networking-ai'

# Common commands
kn get pods
kn logs -f <pod-name>
kn describe pod <pod-name>
kn exec -it <pod-name> -- /bin/bash
kn port-forward svc/fastapi-service 8000:8000
kn top pods
kn get events --sort-by='.lastTimestamp'

# Quick health check
kn get pods | grep -v Running
curl -f https://api.networking-ai.com/health || echo "FAIL"

# Resource usage
kn top pods --sort-by=memory
kn top pods --sort-by=cpu
```

### Links & Resources

- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [Docker Documentation](https://docs.docker.com/)
- [Nginx Ingress Controller](https://kubernetes.github.io/ingress-nginx/)
- [cert-manager](https://cert-manager.io/docs/)
- [Prometheus Operator](https://prometheus-operator.dev/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Redis Documentation](https://redis.io/documentation)

---

**End of Runbook**
