#!/bin/bash
# Get logs from a specific service

SERVICE=$1

if [ -z "$SERVICE" ]; then
    echo "Usage: ./scripts/get_logs.sh <service_name>"
    echo "Available services: dash_app, options_service, chatbot_service, postgres_db, timescaledb"
    exit 1
fi

echo "======================================"
echo "Fetching logs for: $SERVICE"
echo "======================================"

docker-compose logs --tail=100 $SERVICE
