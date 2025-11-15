# 🚀 AI Talent-Hiring Platform - Deployment Guide

## Production SaaS Deployment

This is a complete, professional SaaS platform ready for production deployment.

---

## 📋 **What's Included:**

### Backend Services:
- **FastAPI Application** - Main API server (Port 8000)
- **WebSocket Service** - Real-time updates (Port 8001)
- **Background Workers** - Async job processing
- **PostgreSQL** - Primary database (Port 5432)
- **Redis** - Caching & sessions (Port 6379)
- **Nginx** - Reverse proxy & load balancer (Ports 80/443)

### AI Features:
- 8 AI Agent Services (4,790 lines)
- Agent-to-Agent conversation orchestration
- 100 → TOP 3 matching algorithm
- Anti-hallucination validation
- Real-time learning engine
- Master AI monitoring

---

## 🖥️ **Option 1: Deploy on Your Mac (Local Development)**

### Prerequisites:
```bash
# Install Docker Desktop for Mac
# Download from: https://www.docker.com/products/docker-desktop

# Verify installation
docker --version
docker-compose --version
```

### Quick Start:
```bash
# 1. Navigate to project
cd /path/to/networking-ai

# 2. Set up environment variables
cp .env.example .env

# Edit .env and add your Anthropic API key:
# ANTHROPIC_API_KEY=your_api_key_here

# 3. Start the entire stack
docker-compose up -d

# 4. Check status
docker-compose ps

# 5. View logs
docker-compose logs -f app

# 6. Access the platform
open http://localhost
```

### Stopping:
```bash
docker-compose down
```

### Full rebuild:
```bash
docker-compose down -v  # Remove volumes
docker-compose build --no-cache
docker-compose up -d
```

---

## ☁️ **Option 2: Deploy to Cloud (Production)**

### A. **AWS Deployment** (Recommended)

#### Using AWS ECS (Elastic Container Service):

```bash
# 1. Install AWS CLI
brew install awscli
aws configure

# 2. Create ECR repository
aws ecr create-repository --repository-name networking-ai

# 3. Build and push image
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin YOUR_AWS_ACCOUNT.dkr.ecr.us-east-1.amazonaws.com

docker build -t networking-ai .
docker tag networking-ai:latest YOUR_AWS_ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/networking-ai:latest
docker push YOUR_AWS_ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/networking-ai:latest

# 4. Deploy to ECS (use AWS Console or CLI)
```

#### Using AWS Elastic Beanstalk:
```bash
# 1. Install EB CLI
pip install awsebcli

# 2. Initialize
eb init -p docker networking-ai

# 3. Create environment
eb create networking-ai-prod

# 4. Deploy
eb deploy

# 5. Open
eb open
```

### B. **DigitalOcean Deployment**

```bash
# 1. Install doctl
brew install doctl

# 2. Authenticate
doctl auth init

# 3. Create Kubernetes cluster
doctl kubernetes cluster create networking-ai-cluster --region nyc1 --node-pool "name=worker;size=s-2vcpu-4gb;count=3"

# 4. Deploy with docker-compose
# DigitalOcean App Platform supports docker-compose directly
```

### C. **Google Cloud Run**

```bash
# 1. Install gcloud CLI
brew install google-cloud-sdk

# 2. Authenticate
gcloud auth login
gcloud config set project YOUR_PROJECT_ID

# 3. Build and deploy
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/networking-ai
gcloud run deploy networking-ai --image gcr.io/YOUR_PROJECT_ID/networking-ai --platform managed --region us-central1 --allow-unauthenticated

# 4. Get URL
gcloud run services describe networking-ai --region us-central1 --format 'value(status.url)'
```

### D. **Heroku Deployment**

```bash
# 1. Install Heroku CLI
brew tap heroku/brew && brew install heroku

# 2. Login
heroku login

# 3. Create app
heroku create networking-ai-prod

# 4. Add PostgreSQL
heroku addons:create heroku-postgresql:standard-0

# 5. Add Redis
heroku addons:create heroku-redis:premium-0

# 6. Set environment variables
heroku config:set ANTHROPIC_API_KEY=your_key_here
heroku config:set SECRET_KEY=$(openssl rand -hex 32)

# 7. Deploy
git push heroku main

# 8. Open
heroku open
```

---

## 🔧 **Environment Variables**

Required `.env` file:

```bash
# API Keys
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Database
POSTGRES_DB=networking_ai
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_secure_password_here
DATABASE_URL=postgresql://postgres:password@postgres:5432/networking_ai

# Redis
REDIS_PASSWORD=your_redis_password_here
REDIS_URL=redis://:password@redis:6379/0

# Security
SECRET_KEY=your_secret_key_generate_with_openssl_rand
JWT_SECRET_KEY=your_jwt_secret_generate_with_openssl_rand

# Application
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=info
ALLOWED_ORIGINS=https://yourdomain.com

# Optional Features
ENABLE_WEBSOCKET=true
ENABLE_MASTER_AGENT=true
WORKERS=4
```

Generate secure keys:
```bash
openssl rand -hex 32  # For SECRET_KEY
openssl rand -hex 32  # For JWT_SECRET_KEY
```

---

## 📊 **Monitoring & Health Checks**

### Health Endpoints:
- **API Health**: `http://localhost:8000/api/health`
- **System Health**: `http://localhost/health`

### View Logs:
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f app
docker-compose logs -f postgres
docker-compose logs -f redis
```

### Database Access:
```bash
# Connect to PostgreSQL
docker-compose exec postgres psql -U postgres -d networking_ai

# Redis CLI
docker-compose exec redis redis-cli
```

---

## 🔒 **Security Checklist**

Before production deployment:

- [ ] Change all default passwords
- [ ] Set strong SECRET_KEY and JWT_SECRET_KEY
- [ ] Enable HTTPS (use Let's Encrypt)
- [ ] Configure firewall rules
- [ ] Set up backup strategy for PostgreSQL
- [ ] Enable database encryption at rest
- [ ] Configure rate limiting in Nginx
- [ ] Set up monitoring (Prometheus + Grafana)
- [ ] Enable audit logging
- [ ] Review CORS settings

---

## 📈 **Scaling**

### Horizontal Scaling:
```bash
# Scale app instances
docker-compose up -d --scale app=3 --scale websocket=2

# With Kubernetes
kubectl scale deployment networking-ai-app --replicas=5
```

### Database Scaling:
- Use PostgreSQL read replicas
- Enable connection pooling (PgBouncer)
- Configure Redis Cluster for high availability

---

## 🆘 **Troubleshooting**

### Check service status:
```bash
docker-compose ps
docker-compose logs app
```

### Restart services:
```bash
docker-compose restart app
```

### Database connection issues:
```bash
docker-compose exec app env | grep DATABASE_URL
docker-compose exec postgres pg_isready
```

### Clear and rebuild:
```bash
docker-compose down -v
docker system prune -a
docker-compose up --build
```

---

## 📚 **Additional Resources**

- API Documentation: `/api/docs` (Swagger UI)
- Alternative API Docs: `/api/redoc` (ReDoc)
- Health Check: `/api/health`
- Admin Panel: `/admin` (coming soon)

---

## 🎯 **What's Next?**

1. **Frontend Development**: Build React/Next.js frontend
2. **Payment Integration**: Add Stripe for subscriptions
3. **Email Service**: Integrate SendGrid/AWS SES
4. **Monitoring**: Set up Sentry for error tracking
5. **Analytics**: Add Mixpanel or Google Analytics
6. **CI/CD**: Set up GitHub Actions for automated deployment

---

## 📞 **Support**

For issues or questions:
- Check logs: `docker-compose logs -f`
- Review documentation in `/docs`
- API documentation at `/api/docs`

---

**Built with:**
- FastAPI (Python)
- PostgreSQL
- Redis
- Docker
- Nginx
- Anthropic Claude AI

**Version**: 0.5.0
**License**: MIT
