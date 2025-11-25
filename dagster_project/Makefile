# Makefile for local Dagster development (dagster_project)
# Usage notes:
# - Set DATABASE_URL before running `make up` or export it in your shell:
#     export DATABASE_URL=postgresql://user:pass@host:5432/dbname
# - On Docker Desktop for Linux/WSL, you may need to use host.docker.internal or a docker network
#   for the DATABASE_URL host so the container can reach the database running on the host.
# - All commands assume you're running them from the `dagster_project` directory or that
#   the `docker-compose.yml` file is available in this directory.

COMPOSE := docker-compose
SERVICE := dagster_dev

.PHONY: build up down logs test help

help:
	@echo "Makefile targets for dagster_project"
	@echo
	@echo "  build   - Build the Dagster docker image (docker-compose build)"
	@echo "  up      - Start the Dagster container in detached mode (docker-compose up -d)"
	@echo "            Ensure DATABASE_URL is set before running this target."
	@echo "  down    - Stop and remove the Dagster container and its volumes (docker-compose down -v)"
	@echo "  logs    - Tail the logs of the running Dagster container (docker-compose logs -f dagster_dev)"
	@echo "  test    - Run pytest inside the running Dagster container (docker-compose exec dagster_dev pytest tests/)"

build:
	@echo "Building dagster image..."
	$(COMPOSE) build

up:
	@echo "Starting dagster container in detached mode..."
	@echo "Make sure DATABASE_URL is set (export DATABASE_URL=... ) before running this."
	$(COMPOSE) up -d

down:
	@echo "Stopping and removing dagster containers and volumes..."
	$(COMPOSE) down -v

logs:
	@echo "Tailing logs for $(SERVICE)..."
	$(COMPOSE) logs -f $(SERVICE)

test:
	@echo "Running pytest inside $(SERVICE)..."
	$(COMPOSE) exec $(SERVICE) pytest tests/
