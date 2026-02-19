#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Transport OCR System Deployment ===${NC}"

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Docker is not installed. Please install Docker first.${NC}"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}Docker Compose is not installed. Please install Docker Compose first.${NC}"
    exit 1
fi

# Set environment variables
export COMPOSE_PROJECT_NAME=transport_ocr

# Parse arguments
GPU_MODE=false
SKIP_BUILD=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --gpu)
            GPU_MODE=true
            shift
            ;;
        --skip-build)
            SKIP_BUILD=true
            shift
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --gpu         Enable GPU support"
            echo "  --skip-build  Skip building Docker images"
            echo "  --help        Show this help message"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# Navigate to infrastructure directory
cd "$(dirname "$0")/../infrastructure"

# Create necessary directories
echo -e "${YELLOW}Creating necessary directories...${NC}"
mkdir -p ../logs
mkdir -p ../media

# Copy environment file if not exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}Creating .env file from example...${NC}"
    cp ../.env.example .env
fi

# Build Docker images
if [ "$SKIP_BUILD" = false ]; then
    echo -e "${YELLOW}Building Docker images...${NC}"
    docker-compose build
fi

# Start services
echo -e "${YELLOW}Starting services...${NC}"
if [ "$GPU_MODE" = true ]; then
    echo -e "${YELLOW}Starting with GPU support...${NC}"
    docker-compose -f docker-compose.yml -f docker-compose.gpu.yml up -d
else
    docker-compose up -d
fi

# Wait for services to be ready
echo -e "${YELLOW}Waiting for services to be ready...${NC}"
sleep 10

# Check service health
echo -e "${YELLOW}Checking service health...${NC}"

# Check PostgreSQL
echo -n "PostgreSQL: "
if docker-compose exec -T postgres pg_isready -U postgres &> /dev/null; then
    echo -e "${GREEN}OK${NC}"
else
    echo -e "${RED}FAILED${NC}"
fi

# Check Redis
echo -n "Redis: "
if docker-compose exec -T redis redis-cli ping &> /dev/null; then
    echo -e "${GREEN}OK${NC}"
else
    echo -e "${RED}FAILED${NC}"
fi

# Check MinIO
echo -n "MinIO: "
if curl -s http://localhost:9000/minio/health/live &> /dev/null; then
    echo -e "${GREEN}OK${NC}"
else
    echo -e "${RED}FAILED${NC}"
fi

# Show service status
echo ""
echo -e "${GREEN}=== Deployment Complete ===${NC}"
echo ""
echo "Services:"
echo "  - Web App:        http://localhost:8001"
echo "  - OCR Service:    http://localhost:8000"
echo "  - Nginx:          http://localhost"
echo "  - MinIO Console:  http://localhost:9001"
echo "  - Prometheus:     http://localhost:9090"
echo "  - Grafana:        http://localhost:3000"
echo ""
echo "To view logs: docker-compose logs -f [service_name]"
echo "To stop: docker-compose down"
