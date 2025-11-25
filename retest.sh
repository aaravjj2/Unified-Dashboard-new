#!/bin/bash

# --- 1. Restore Azure Resource and Deployment Variables ---
export ENDPOINT_NAME="portfolio-prediction-v1"
export RG="unified-dashboard-rg"
export WS="unified-dashboard-ml"
export DEPLOYMENT_NAME="blue"

# --- 2. Restore Dynamic Endpoint Keys ---
echo "Retrieving latest endpoint credentials..."
export PRIMARY_KEY=$(az ml online-endpoint get-credentials --name $ENDPOINT_NAME --resource-group $RG --workspace-name $WS --query "primaryKey" -o tsv)
export SCORING_URI=$(az ml online-endpoint show --name $ENDPOINT_NAME --resource-group $RG --workspace-name $WS --query "scoring_uri" -o tsv)

# --- 3. Run Final Successful Test (8 Features) ---
export SAMPLE_INPUT_8_FEATURES="{\"inputs\": [[1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0]]}"

echo "---------------------------------------------------------"
echo "Running Final Test against: $SCORING_URI"
echo "---------------------------------------------------------"

# Use -k to bypass the SSL certificate timeout (common in local/WSL setups)
curl -k -X POST \
  -H "Authorization: Bearer $PRIMARY_KEY" \
  -H "Content-Type: application/json" \
  -d "$SAMPLE_INPUT_8_FEATURES" \
  "$SCORING_URI"

echo ""
echo "---------------------------------------------------------"
echo "Test finished."