FROM python:3.10-slim

WORKDIR /opt/dagster/app

# Install dependencies
RUN pip install --no-cache-dir \
    dagster \
    dagster-webserver \
    dagster-postgres \
    pandas \
    psycopg2-binary \
    sqlalchemy

# Create dagster home directory
RUN mkdir -p /opt/dagster/dagster_home

ENV DAGSTER_HOME=/opt/dagster/dagster_home

# Copy pipeline code
COPY . .

# Copy configuration files to DAGSTER_HOME
RUN cp workspace.yaml /opt/dagster/dagster_home/ && \
    cp dagster.yaml /opt/dagster/dagster_home/

EXPOSE 3000

CMD ["dagster", "dev", "-h", "0.0.0.0", "-p", "3000", "-m", "data_pipeline"]
