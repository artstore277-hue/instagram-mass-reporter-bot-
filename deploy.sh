#!/bin/bash

# Instagram Mass Report Bot - Quick Deploy Script
# Usage: ./deploy.sh

set -e

echo "================================================"
echo "Instagram Mass Report Bot - Deployment Script"
echo "================================================"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker is not installed${NC}"
    echo "Install from: https://www.docker.com/products/docker-desktop"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ Docker Compose is not installed${NC}"
    echo "Install from: https://docs.docker.com/compose/install/"
    exit 1
fi

echo -e "${GREEN}✓ Docker found${NC}"
echo -e "${GREEN}✓ Docker Compose found${NC}"
echo ""

# Check if config files exist
if [ ! -f "config.yml" ]; then
    echo -e "${RED}❌ config.yml not found${NC}"
    exit 1
fi

if [ ! -f ".env" ]; then
    echo -e "${RED}❌ .env not found${NC}"
    exit 1
fi

echo -e "${GREEN}✓ config.yml found${NC}"
echo -e "${GREEN}✓ .env found${NC}"
echo ""

# Create required directories
echo "Creating directories..."
mkdir -p cookies chrome_extensions data logs
echo -e "${GREEN}✓ Directories created${NC}"
echo ""

# Build and start
echo "Building Docker image..."
docker compose build --no-cache
echo -e "${GREEN}✓ Build complete${NC}"
echo ""

echo "Starting bot..."
docker compose up -d
echo -e "${GREEN}✓ Bot started${NC}"
echo ""

# Wait for bot to start
echo "Waiting for bot to start (30 seconds)..."
sleep 30

# Show status
echo "Checking status..."
docker compose ps
echo ""

# Show logs
echo -e "${YELLOW}Bot logs:${NC}"
docker compose logs bot | tail -20
echo ""

echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}✓ Bot deployed successfully!${NC}"
echo -e "${GREEN}================================================${NC}"
echo ""
echo "Commands:"
echo "  - View logs: docker compose logs -f bot"
echo "  - Stop bot:  docker compose down"
echo "  - Restart:   docker compose restart bot"
echo ""
