#!/bin/bash
# ============================================
# AI Talent-Hiring Platform - Deployment Script
# ============================================

set -e  # Exit on error

echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║   🚀 AI Talent-Hiring Platform - Production Deployment       ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if Docker is installed
echo "📋 Step 1: Checking Docker installation..."
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker is not installed!${NC}"
    echo ""
    echo "Please install Docker Desktop for Mac:"
    echo "https://www.docker.com/products/docker-desktop"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ Docker Compose is not installed!${NC}"
    echo ""
    echo "Please install Docker Compose:"
    echo "https://docs.docker.com/compose/install/"
    exit 1
fi

echo -e "${GREEN}✓ Docker $(docker --version) installed${NC}"
echo -e "${GREEN}✓ Docker Compose $(docker-compose --version) installed${NC}"
echo ""

# Check if Docker daemon is running
echo "📋 Step 2: Checking Docker daemon..."
if ! docker info &> /dev/null; then
    echo -e "${RED}❌ Docker daemon is not running!${NC}"
    echo ""
    echo "Please start Docker Desktop and try again."
    exit 1
fi
echo -e "${GREEN}✓ Docker daemon is running${NC}"
echo ""

# Check for Anthropic API key
echo "📋 Step 3: Checking environment configuration..."
if [ -f .env ]; then
    ANTHROPIC_KEY=$(grep "^ANTHROPIC_API_KEY=" .env | cut -d'=' -f2)
    if [ "$ANTHROPIC_KEY" = "your_api_key_here" ] || [ -z "$ANTHROPIC_KEY" ]; then
        echo -e "${YELLOW}⚠️  ANTHROPIC_API_KEY is not set!${NC}"
        echo ""
        echo "Please set your Anthropic API key in the .env file:"
        echo "  1. Get your API key from: https://console.anthropic.com/"
        echo "  2. Edit .env file: nano .env"
        echo "  3. Replace 'your_api_key_here' with your actual API key"
        echo "  4. Save and run this script again"
        echo ""
        read -p "Do you want to continue without an API key? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    else
        echo -e "${GREEN}✓ Anthropic API key is configured${NC}"
    fi
else
    echo -e "${RED}❌ .env file not found!${NC}"
    exit 1
fi
echo ""

# Create necessary directories
echo "📋 Step 4: Creating necessary directories..."
mkdir -p data logs uploads logs/nginx
echo -e "${GREEN}✓ Directories created${NC}"
echo ""

# Stop any existing containers
echo "📋 Step 5: Stopping existing containers (if any)..."
docker-compose down &> /dev/null || true
echo -e "${GREEN}✓ Existing containers stopped${NC}"
echo ""

# Build and start services
echo "📋 Step 6: Building Docker images..."
echo -e "${BLUE}This may take a few minutes on first run...${NC}"
docker-compose build --no-cache

echo ""
echo "📋 Step 7: Starting all services..."
echo -e "${BLUE}Starting: PostgreSQL, Redis, FastAPI, WebSocket, Worker, Nginx${NC}"
docker-compose up -d

echo ""
echo "📋 Step 8: Waiting for services to be healthy..."
sleep 5

# Check service status
echo ""
echo "📊 Service Status:"
echo "═══════════════════════════════════════════════════════════════"
docker-compose ps
echo "═══════════════════════════════════════════════════════════════"

# Wait for health checks
echo ""
echo "⏳ Waiting for health checks to pass..."
RETRY_COUNT=0
MAX_RETRIES=30

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    HEALTHY=$(docker-compose ps | grep "healthy" | wc -l)
    if [ $HEALTHY -ge 3 ]; then
        break
    fi
    echo -n "."
    sleep 2
    RETRY_COUNT=$((RETRY_COUNT+1))
done
echo ""

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo -e "${YELLOW}⚠️  Some services may still be starting. Check logs with: docker-compose logs -f${NC}"
else
    echo -e "${GREEN}✓ All services are healthy${NC}"
fi

echo ""
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║                    🎉 DEPLOYMENT SUCCESSFUL! 🎉               ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""
echo "🌐 Your AI Talent-Hiring Platform is now running!"
echo ""
echo "📍 Access Points:"
echo "   • Web Application: http://localhost"
echo "   • API Server:      http://localhost:8000"
echo "   • API Docs:        http://localhost:8000/api/docs"
echo "   • WebSocket:       ws://localhost:8001"
echo "   • Health Check:    http://localhost/health"
echo ""
echo "📊 Useful Commands:"
echo "   • View logs:       docker-compose logs -f"
echo "   • View app logs:   docker-compose logs -f app"
echo "   • Stop services:   docker-compose down"
echo "   • Restart:         docker-compose restart"
echo "   • Status:          docker-compose ps"
echo ""
echo "🔍 Database Access:"
echo "   • PostgreSQL:      docker-compose exec postgres psql -U postgres -d networking_ai"
echo "   • Redis:           docker-compose exec redis redis-cli -a y54qiPogZGIVOhoKIb6yuw"
echo ""
echo "📚 Documentation:"
echo "   • See DEPLOYMENT.md for detailed deployment guide"
echo "   • See README.md for platform overview"
echo ""
echo -e "${GREEN}Happy Talent Matching! 🚀${NC}"
