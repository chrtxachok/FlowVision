#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}=== Transport OCR System Health Check ===${NC}"
echo ""

# Function to check HTTP endpoint
check_http() {
    local url=$1
    local name=$2
    
    if curl -s -f -o /dev/null "$url"; then
        echo -e "${name}: ${GREEN}OK${NC}"
        return 0
    else
        echo -e "${name}: ${RED}FAILED${NC}"
        return 1
    fi
}

# Function to check Docker container
check_container() {
    local container=$1
    local name=$2
    
    if docker ps --filter "name=$container" --filter "status=running" | grep -q "$container"; then
        echo -e "${name}: ${GREEN}RUNNING${NC}"
        return 0
    else
        echo -e "${name}: ${RED}STOPPED${NC}"
        return 1
    fi
}

FAILED=0

# Check Docker containers
echo "Docker Containers:"
check_container "transport_ocr_postgres" "  PostgreSQL" || FAILED=1
check_container "transport_ocr_redis" "  Redis" || FAILED=1
check_container "transport_ocr_minio" "  MinIO" || FAILED=1
check_container "transport_ocr_ocr_service" "  OCR Service" || FAILED=1
check_container "transport_ocr_web_app" "  Web App" || FAILED=1
check_container "transport_ocr_nginx" "  Nginx" || FAILED=1

echo ""

# Check HTTP endpoints
echo "HTTP Endpoints:"
check_http "http://localhost:8001/admin" "  Django Admin" || FAILED=1
check_http "http://localhost:8000/health" "  OCR Service Health" || FAILED=1
check_http "http://localhost:9090" "  Prometheus" || FAILED=1
check_http "http://localhost:3000" "  Grafana" || FAILED=1
check_http "http://localhost:9000/minio/health/live" "  MinIO Health" || FAILED=1

echo ""

# Check MinIO buckets
echo "MinIO Buckets:"
if command -v mc &> /dev/null; then
    mc ls local/documents &> /dev/null && echo -e "  documents: ${GREEN}EXISTS${NC}" || echo -e "  documents: ${YELLOW}NOT CREATED${NC}"
else
    echo -e "  MinIO CLI not available (skipping bucket check)"
fi

echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}=== All Health Checks Passed ===${NC}"
    exit 0
else
    echo -e "${RED}=== Some Health Checks Failed ===${NC}"
    exit 1
fi
