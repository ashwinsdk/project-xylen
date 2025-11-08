#!/bin/bash

# Project Xylen - Docker Management Script
# Quick commands for managing the trading system

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Functions
print_header() {
    echo -e "${GREEN}=================================="
    echo -e "$1"
    echo -e "==================================${NC}"
}

print_error() {
    echo -e "${RED}ERROR: $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}WARNING: $1${NC}"
}

# Check if .env exists
if [ ! -f ".env" ]; then
    print_warning ".env file not found. Creating from template..."
    cp .env.example .env
    print_warning "Please edit .env with your API credentials before starting!"
    exit 1
fi

# Parse command
case "$1" in
    start)
        print_header "Starting Project Xylen"
        docker-compose up -d
        echo ""
        echo -e "${GREEN}Services started!${NC}"
        echo "Coordinator:      http://localhost:9090/metrics"
        echo "Model Server 1:   http://localhost:8001/health"
        echo "Model Server 2:   http://localhost:8002/health"
        echo "Model Server 3:   http://localhost:8003/health"
        echo "Model Server 4:   http://localhost:8004/health"
        echo "Grafana:          http://localhost:3000"
        echo "WebSocket:        ws://localhost:8765"
        ;;
    
    stop)
        print_header "Stopping Project Xylen"
        docker-compose down
        echo -e "${GREEN}Services stopped!${NC}"
        ;;
    
    restart)
        print_header "Restarting Project Xylen"
        docker-compose restart
        echo -e "${GREEN}Services restarted!${NC}"
        ;;
    
    build)
        print_header "Building Docker Images"
        docker-compose build --no-cache
        echo -e "${GREEN}Build complete!${NC}"
        ;;
    
    logs)
        if [ -z "$2" ]; then
            docker-compose logs -f
        else
            docker-compose logs -f "$2"
        fi
        ;;
    
    status)
        print_header "Service Status"
        docker-compose ps
        ;;
    
    health)
        print_header "Health Check"
        echo "Coordinator:"
        curl -s http://localhost:9090/metrics | grep xylen | head -5 || echo "Not responding"
        echo ""
        echo "Model Server 1:"
        curl -s http://localhost:8001/health || echo "Not responding"
        echo ""
        echo "Model Server 2:"
        curl -s http://localhost:8002/health || echo "Not responding"
        echo ""
        echo "Model Server 3:"
        curl -s http://localhost:8003/health || echo "Not responding"
        echo ""
        echo "Model Server 4:"
        curl -s http://localhost:8004/health || echo "Not responding"
        ;;
    
    clean)
        print_header "Cleaning Up"
        print_warning "This will remove all containers, volumes, and images!"
        read -p "Are you sure? (y/N) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            docker-compose down -v
            docker system prune -f
            echo -e "${GREEN}Cleanup complete!${NC}"
        else
            echo "Cancelled."
        fi
        ;;
    
    *)
        echo "Project Xylen - Docker Management"
        echo ""
        echo "Usage: ./docker-manage.sh [command]"
        echo ""
        echo "Commands:"
        echo "  start      Start all services"
        echo "  stop       Stop all services"
        echo "  restart    Restart all services"
        echo "  build      Rebuild Docker images"
        echo "  logs       View logs (optionally specify service)"
        echo "  status     Show service status"
        echo "  health     Check health of all services"
        echo "  clean      Remove all containers and volumes"
        echo ""
        echo "Examples:"
        echo "  ./docker-manage.sh start"
        echo "  ./docker-manage.sh logs coordinator"
        echo "  ./docker-manage.sh health"
        ;;
esac
