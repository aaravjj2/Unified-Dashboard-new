# Backtester Service Dockerfile
# Based on optimized fin-dash-base:latest multi-stage build
FROM fin-dash-base:latest

# Set working directory
WORKDIR /app

# ============================================================================
# Install backtester-specific dependencies
# ============================================================================
RUN --mount=type=cache,id=pycache,target=/root/.cache/pip \
    pip install --no-cache-dir \
    pandas>=1.3.0 \
    numpy>=1.20.0 \
    mlflow>=2.0.0 \
    pytest>=7.0.0 \
    pytest-asyncio>=0.21.0

# ============================================================================
# Copy backtester service code
# Note: Copying the entire services/backtester_service directory
# ============================================================================
COPY services/backtester_service /app/backtester_service

# Copy strategy registry and dependencies from financial_dashboard
COPY financial_dashboard/services/options_service/strategies /app/financial_dashboard/services/options_service/strategies
COPY financial_dashboard/services/__init__.py /app/financial_dashboard/services/__init__.py
COPY financial_dashboard/__init__.py /app/financial_dashboard/__init__.py

# Copy utils directory needed by strategies
COPY financial_dashboard/utils /app/financial_dashboard/utils

# Copy tests for in-container testing
COPY tests /app/tests

# Create results directory for backtest outputs
RUN mkdir -p /app/backtester_service/results

# Set Python path to include both app root and backtester_service
ENV PYTHONPATH=/app:/app/backtester_service
ENV PORT=8081

# Expose backtester API port
EXPOSE 8081

# Health check endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8081/health || exit 1

# Run the FastAPI application using uvicorn
# Using the app:app pattern from backtester_service/app.py
CMD ["python3", "-m", "uvicorn", "backtester_service.app:app", "--host", "0.0.0.0", "--port", "8081"]
