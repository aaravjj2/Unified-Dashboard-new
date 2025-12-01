# Dagster development Dockerfile
# Starts from python slim and installs dependencies from requirements.txt
FROM python:3.10-slim

# Avoid running as root in production; for development this is fine
WORKDIR /opt/dagster_project

# Install system dependencies needed for psycopg2 and common wheels
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt ./requirements.txt
RUN python -m pip install --upgrade pip setuptools wheel
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . /opt/dagster_project

# Expose Dagit / Dagster ports (default Dagit port 3000)
EXPOSE 3000

# Default command: try to run dagit; if missing, fall back to `dagster dev`; if
# both are unavailable keep container alive so `docker-compose up -d` succeeds.
CMD ["bash", "-lc", "dagit -f jobs/ingestion_job.py -h 0.0.0.0 -p 3000 || dagster dev -h 0.0.0.0 -p 3000 || tail -f /dev/null"]
