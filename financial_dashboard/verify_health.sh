#!/bin/bash

# Phase 1: Health Verification Script
# Verifies all 10 services are healthy within 3 minutes

echo "=========================================="
echo "Phase 1: System Launch & Health Verification"
echo "=========================================="

TIMEOUT=180  # 3 minutes
INTERVAL=10  # Check every 10 seconds
ELAPSED=0

SERVICES=(
    "fin_dash_postgres"
    "fin_dash_market_trends"
    "fin_dash_market_forecast"
    "fin_dash_analysis"
    "fin_dash_portfolio"
    "fin_dash_research"
    "fin_dash_options"
    "fin_dash_chatbot"
    "fin_dash_gateway"
    "fin_dash_app"
)

echo ""
echo "Step 1: Verifying Docker container health status..."
echo "---------------------------------------------------"

while [ $ELAPSED -lt $TIMEOUT ]; do
    ALL_HEALTHY=true
    
    for SERVICE in "${SERVICES[@]}"; do
        STATUS=$(docker inspect --format='{{.State.Health.Status}}' "$SERVICE" 2>/dev/null || echo "no_health")
        
        # For services without healthcheck, check if running
        if [ "$STATUS" == "no_health" ]; then
            STATUS=$(docker inspect --format='{{.State.Status}}' "$SERVICE" 2>/dev/null || echo "not_found")
            if [ "$STATUS" != "running" ]; then
                ALL_HEALTHY=false
                echo "❌ $SERVICE: $STATUS"
            else
                echo "✅ $SERVICE: running (no healthcheck)"
            fi
        elif [ "$STATUS" != "healthy" ]; then
            ALL_HEALTHY=false
            echo "⏳ $SERVICE: $STATUS"
        else
            echo "✅ $SERVICE: $STATUS"
        fi
    done
    
    if [ "$ALL_HEALTHY" = true ]; then
        echo ""
        echo "✅ All services are healthy!"
        break
    fi
    
    ELAPSED=$((ELAPSED + INTERVAL))
    if [ $ELAPSED -lt $TIMEOUT ]; then
        echo ""
        echo "Waiting ${INTERVAL}s... (${ELAPSED}s/${TIMEOUT}s elapsed)"
        echo ""
        sleep $INTERVAL
    fi
done

if [ "$ALL_HEALTHY" != true ]; then
    echo ""
    echo "❌ FAILED: Not all services became healthy within ${TIMEOUT}s"
    echo "Checking logs for failed services..."
    docker-compose ps
    exit 1
fi

echo ""
echo "Step 2: Verifying HTTP health endpoints..."
echo "-------------------------------------------"

HEALTH_ENDPOINTS=(
    "http://localhost:8050/health|Market Trends"
    "http://localhost:8051/health|Market Forecast"
    "http://localhost:8054/health|Analysis Hub"
    "http://localhost:8056/health|Portfolio"
    "http://localhost:8058/health|Research Lab"
    "http://localhost:8060/health|Options Service"
    "http://localhost:8062/health|Chatbot"
    "http://localhost:8049/health|API Gateway"
)

ALL_ENDPOINTS_OK=true

for ENDPOINT in "${HEALTH_ENDPOINTS[@]}"; do
    URL=$(echo "$ENDPOINT" | cut -d'|' -f1)
    NAME=$(echo "$ENDPOINT" | cut -d'|' -f2)
    
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "$URL" 2>/dev/null || echo "000")
    
    if [ "$HTTP_CODE" == "200" ]; then
        echo "✅ $NAME: HTTP $HTTP_CODE"
    else
        echo "❌ $NAME: HTTP $HTTP_CODE (expected 200)"
        ALL_ENDPOINTS_OK=false
    fi
done

if [ "$ALL_ENDPOINTS_OK" != true ]; then
    echo ""
    echo "❌ FAILED: Not all health endpoints returned 200 OK"
    exit 1
fi

echo ""
echo "=========================================="
echo "✅ Phase 1 Complete: All services healthy!"
echo "=========================================="
echo ""

exit 0
