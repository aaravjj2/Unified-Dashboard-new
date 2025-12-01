# syntax=docker/dockerfile:1.4
# Main Dashboard Dockerfile - uses shared base image
FROM fin-dash-base:latest

# Set working directory
WORKDIR /app

# ============================================================================
# OPTIMIZATION: Copy requirements FIRST for better layer caching
# Requirements rarely change, so this layer is cached across rebuilds
# ============================================================================
COPY financial_dashboard/requirements.txt .

# Install dashboard-specific dependencies
RUN --mount=type=cache,id=pycache,target=/root/.cache/pip \
    pip install --no-cache-dir -r requirements.txt

# Install Gunicorn for production WSGI server
RUN pip install gunicorn

# Install Playwright for testing (early installation for caching)
RUN pip install pytest pytest-playwright pytest-asyncio

# Install Playwright browser dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libnss3 \
    libnspr4 \
    libdbus-1-3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libatspi2.0-0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpango-1.0-0 \
    libcairo2 \
    && rm -rf /var/lib/apt/lists/*

RUN playwright install chromium

# ============================================================================
# OPTIMIZATION: Copy application code LAST
# Code changes frequently, so this layer is placed after stable dependencies
# ============================================================================
# Copy the financial_dashboard module directory to preserve package structure
COPY financial_dashboard ./financial_dashboard
# Copy tests directory for browser E2E tests
COPY tests ./tests
# Copy project metadata for package installation if needed
COPY pyproject.toml setup.py ./

# Create necessary directories
RUN mkdir -p logs cache output test-artifacts
# Copy any packaged cache files into top-level /app/cache so modules expecting /app/cache find them
RUN if [ -d financial_dashboard/cache ]; then cp -a financial_dashboard/cache/. cache/ || true; fi

# Install the package into the image so `financial_dashboard` imports resolve
RUN pip install -e .

# Set PYTHONPATH to ensure module imports work
ENV PYTHONPATH="/app:${PYTHONPATH}"

# Expose port
EXPOSE 8050

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8050/ || exit 1

# Run the application using Gunicorn (production-ready WSGI server)
# Using app:server instead of index.py to avoid NameError
# Single worker to prevent memory issues, increased timeout for long-running requests
CMD ["python", "financial_dashboard/index_full.py"]
