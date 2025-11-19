#!/bin/bash
# Restart a specific service

SERVICE=$1

if [ -z "$SERVICE" ]; then
    echo "Usage: ./scripts/restart_service.sh <service_name>"
    echo "Available services: dash_app, options_service, chatbot_service"
    exit 1
fi

echo "======================================"
echo "Restarting service: $SERVICE"
echo "======================================"

docker-compose restart $SERVICE

echo "Waiting for service to be healthy..."
sleep 5

docker ps --filter "name=$SERVICE" --format "table {{.Names}}\t{{.Status}}"
