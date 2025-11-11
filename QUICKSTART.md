# 🚀 Quick Start Guide - AI Talent-Hiring Platform

Get your AI Talent-Hiring SaaS platform running in **3 simple steps**!

---

## Prerequisites

✅ **Mac with Docker Desktop** - [Download here](https://www.docker.com/products/docker-desktop)

---

## Step 1: Get Your Anthropic API Key

1. Go to https://console.anthropic.com/
2. Sign up or log in
3. Navigate to API Keys section
4. Create a new API key
5. Copy the key (starts with `sk-ant-...`)

---

## Step 2: Configure Your API Key

Open the `.env` file in the project directory and replace `your_api_key_here` with your actual API key:

```bash
# Option 1: Use nano editor
nano .env

# Option 2: Use your favorite editor
open -a TextEdit .env

# Option 3: Use command line
sed -i '' 's/your_api_key_here/sk-ant-YOUR-ACTUAL-KEY-HERE/' .env
```

Find this line:
```
ANTHROPIC_API_KEY=your_api_key_here
```

Replace with:
```
ANTHROPIC_API_KEY=sk-ant-YOUR-ACTUAL-KEY-HERE
```

Save the file.

---

## Step 3: Deploy the Platform

Run the deployment script:

```bash
cd /path/to/networking-ai
./deploy.sh
```

That's it! 🎉

---

## Access Your Platform

Once deployment completes, access your platform at:

- **Web Application**: http://localhost
- **API Documentation**: http://localhost:8000/api/docs
- **Health Check**: http://localhost/health

---

## What's Running?

Your complete SaaS stack includes:

- 🚀 **FastAPI Backend** - Main API server (Port 8000)
- 🔌 **WebSocket Service** - Real-time updates (Port 8001)
- ⚙️ **Background Workers** - Async job processing
- 🗄️ **PostgreSQL Database** - Primary data store (Port 5432)
- ⚡ **Redis Cache** - Fast caching & sessions (Port 6379)
- 🌐 **Nginx Reverse Proxy** - Web server (Port 80)

---

## Platform Features

✨ **8 AI Agent Services** - Specialized agents for different tasks
🤖 **Agent-to-Agent Conversations** - Autonomous agent collaboration
🎯 **100 → TOP 3 Matching** - Intelligent candidate filtering
🛡️ **Anti-Hallucination System** - 4-layer protection
📚 **RAG System** - ChromaDB knowledge management
🔒 **Enterprise Security** - Encryption, JWT, secure passwords

---

## Common Commands

```bash
# View all logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f app
docker-compose logs -f postgres
docker-compose logs -f redis

# Check service status
docker-compose ps

# Stop all services
docker-compose down

# Restart services
docker-compose restart

# Rebuild and restart
docker-compose down
docker-compose up --build -d

# Access PostgreSQL
docker-compose exec postgres psql -U postgres -d networking_ai

# Access Redis
docker-compose exec redis redis-cli
```

---

## Troubleshooting

### Docker not found
- Install Docker Desktop: https://www.docker.com/products/docker-desktop
- Make sure Docker Desktop is running (look for whale icon in menu bar)

### Services not starting
```bash
# Check logs
docker-compose logs -f app

# Rebuild from scratch
docker-compose down -v
docker-compose build --no-cache
docker-compose up -d
```

### Port already in use
```bash
# Find what's using the port
lsof -i :8000
lsof -i :80

# Stop the conflicting process or change ports in .env
```

### API key issues
- Make sure you've set `ANTHROPIC_API_KEY` in `.env`
- Verify the key is valid at https://console.anthropic.com/
- Check for any extra spaces or quotes around the key

---

## Next Steps

1. **Test the Platform**
   - Open http://localhost in your browser
   - Create a test account
   - Try the matching algorithm

2. **Explore the API**
   - Visit http://localhost:8000/api/docs
   - Try out the interactive API documentation

3. **Monitor Performance**
   - Check logs: `docker-compose logs -f`
   - Monitor health: http://localhost/health

4. **Deploy to Production**
   - See DEPLOYMENT.md for cloud deployment options
   - Configure custom domain
   - Set up SSL certificates

---

## Need Help?

- 📖 **Full Documentation**: See DEPLOYMENT.md
- 🐛 **Check Logs**: `docker-compose logs -f`
- 💬 **API Docs**: http://localhost:8000/api/docs
- 🔍 **Health Status**: http://localhost/health

---

**Built with ❤️ using:**
- FastAPI (Python)
- PostgreSQL
- Redis
- Docker
- Anthropic Claude AI

**Version**: 1.0.0
**License**: MIT

---

## Platform Statistics

- **Lines of Code**: 129,566
- **Files**: 331
- **AI Agents**: 8 specialized services
- **Matching Algorithm**: 100 → TOP 3
- **Security Layers**: 4-layer anti-hallucination
- **Database**: PostgreSQL 16
- **Cache**: Redis 7

🎯 **Ready for Production Deployment!**
