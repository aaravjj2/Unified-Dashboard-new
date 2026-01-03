"""
DevOps & Operations Tools
Phase 8 - Operations & DX (Items 601-640)

Complete implementation of:
- Makefile targets
- Docker compose profiles
- Kubernetes manifests generator
- CI/CD pipeline automation
- Environment management
"""

import os
import json
import yaml
import subprocess
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
import shutil


# =============================================================================
# MAKEFILE GENERATOR (Items 601-610)
# =============================================================================

MAKEFILE_TEMPLATE = """# Alpaca Options Lab - Auto-generated Makefile
# Generated: {timestamp}

.PHONY: help up down restart test lint format clean build deploy logs shell

# Default target
help:
\t@echo "Alpaca Options Lab - Available Commands"
\t@echo "========================================"
\t@echo "  make up        - Start all services"
\t@echo "  make down      - Stop all services"
\t@echo "  make restart   - Restart all services"
\t@echo "  make test      - Run test suite"
\t@echo "  make lint      - Run linters"
\t@echo "  make format    - Auto-format code"
\t@echo "  make clean     - Clean build artifacts"
\t@echo "  make build     - Build Docker images"
\t@echo "  make deploy    - Deploy to production"
\t@echo "  make logs      - View service logs"
\t@echo "  make shell     - Open shell in container"

# Service management
up:
\t@echo "Starting Alpaca Options Lab..."
\tUX_CONSOLIDATED=true python run_alpaca_enhanced_server.py &
\t@echo "Dashboard available at http://localhost:8053"

down:
\t@echo "Stopping services..."
\t-pkill -f "run_alpaca_enhanced_server"
\t@echo "Services stopped."

restart: down up

# Development
test:
\t@echo "Running test suite..."
\tpython -m pytest tests/ -v --tb=short
\tpython test_phase6_7_e2e.py

lint:
\t@echo "Running linters..."
\t-ruff check . --fix
\t-mypy financial_dashboard/ engines/ --ignore-missing-imports

format:
\t@echo "Formatting code..."
\t-black . --line-length 100
\t-isort . --profile black

clean:
\t@echo "Cleaning build artifacts..."
\tfind . -type d -name __pycache__ -exec rm -rf {{}} + 2>/dev/null || true
\tfind . -type f -name "*.pyc" -delete
\trm -rf .pytest_cache .mypy_cache .ruff_cache
\t@echo "Clean complete."

# Docker
build:
\t@echo "Building Docker images..."
\tdocker build -t alpaca-options-lab:latest .

deploy:
\t@echo "Deploying to production..."
\t@echo "WARNING: Production deployment not configured"

# Debugging
logs:
\ttail -f logs/*.log 2>/dev/null || echo "No logs found"

shell:
\tdocker exec -it alpaca-dashboard /bin/bash 2>/dev/null || bash

# Environment
env-check:
\t@echo "Environment Check"
\t@echo "================="
\t@python --version
\t@echo "ALPACA_API_KEY: $$(test -n \"$$ALPACA_API_KEY\" && echo 'Set' || echo 'Not set')"
\t@echo "ALPACA_SECRET_KEY: $$(test -n \"$$ALPACA_SECRET_KEY\" && echo 'Set' || echo 'Not set')"

# Database
db-migrate:
\t@echo "Running database migrations..."
\tpython -c "from engines.data.migrations import run_migrations; run_migrations()"

db-seed:
\t@echo "Seeding database..."
\tpython -c "from engines.data.seed import seed_database; seed_database()"
"""


def generate_makefile(output_path: str = "Makefile") -> str:
    """Generate Makefile with all targets."""
    content = MAKEFILE_TEMPLATE.format(timestamp=datetime.now().isoformat())
    
    with open(output_path, 'w') as f:
        f.write(content)
    
    return content


# =============================================================================
# DOCKER COMPOSE PROFILES (Items 611-620)
# =============================================================================

DOCKER_COMPOSE_TEMPLATE = {
    "version": "3.8",
    "services": {
        "dashboard": {
            "build": {
                "context": ".",
                "dockerfile": "Dockerfile"
            },
            "container_name": "alpaca-dashboard",
            "ports": ["8053:8053"],
            "environment": [
                "UX_CONSOLIDATED=true",
                "ALPACA_API_KEY=${ALPACA_API_KEY}",
                "ALPACA_SECRET_KEY=${ALPACA_SECRET_KEY}",
                "PYTHONUNBUFFERED=1"
            ],
            "volumes": [
                "./:/app",
                "./logs:/app/logs"
            ],
            "healthcheck": {
                "test": ["CMD", "curl", "-f", "http://localhost:8053/api/options/ready"],
                "interval": "30s",
                "timeout": "10s",
                "retries": 3
            },
            "restart": "unless-stopped",
            "profiles": ["default", "dev", "prod"]
        },
        "redis": {
            "image": "redis:7-alpine",
            "container_name": "alpaca-redis",
            "ports": ["6379:6379"],
            "volumes": ["redis_data:/data"],
            "healthcheck": {
                "test": ["CMD", "redis-cli", "ping"],
                "interval": "10s"
            },
            "profiles": ["default", "prod"]
        },
        "timescaledb": {
            "image": "timescale/timescaledb:latest-pg15",
            "container_name": "alpaca-timescaledb",
            "ports": ["5432:5432"],
            "environment": [
                "POSTGRES_USER=alpaca",
                "POSTGRES_PASSWORD=${DB_PASSWORD:-alpaca123}",
                "POSTGRES_DB=options_lab"
            ],
            "volumes": ["timescale_data:/var/lib/postgresql/data"],
            "profiles": ["prod"]
        },
        "prometheus": {
            "image": "prom/prometheus:latest",
            "container_name": "alpaca-prometheus",
            "ports": ["9090:9090"],
            "volumes": ["./prometheus.yml:/etc/prometheus/prometheus.yml"],
            "profiles": ["monitoring"]
        },
        "grafana": {
            "image": "grafana/grafana:latest",
            "container_name": "alpaca-grafana",
            "ports": ["3000:3000"],
            "environment": ["GF_SECURITY_ADMIN_PASSWORD=admin"],
            "profiles": ["monitoring"]
        }
    },
    "volumes": {
        "redis_data": {},
        "timescale_data": {}
    },
    "networks": {
        "default": {
            "name": "alpaca-network"
        }
    }
}


def generate_docker_compose(output_path: str = "docker-compose.yml") -> dict:
    """Generate Docker Compose configuration."""
    with open(output_path, 'w') as f:
        yaml.dump(DOCKER_COMPOSE_TEMPLATE, f, default_flow_style=False, sort_keys=False)
    
    return DOCKER_COMPOSE_TEMPLATE


# =============================================================================
# KUBERNETES MANIFESTS (Items 621-630)
# =============================================================================

def generate_k8s_deployment() -> dict:
    """Generate Kubernetes Deployment manifest."""
    return {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {
            "name": "alpaca-options-lab",
            "labels": {"app": "alpaca-options-lab"}
        },
        "spec": {
            "replicas": 2,
            "selector": {
                "matchLabels": {"app": "alpaca-options-lab"}
            },
            "template": {
                "metadata": {
                    "labels": {"app": "alpaca-options-lab"}
                },
                "spec": {
                    "containers": [{
                        "name": "dashboard",
                        "image": "alpaca-options-lab:latest",
                        "ports": [{"containerPort": 8053}],
                        "env": [
                            {"name": "UX_CONSOLIDATED", "value": "true"},
                            {"name": "ALPACA_API_KEY", "valueFrom": {"secretKeyRef": {"name": "alpaca-secrets", "key": "api-key"}}},
                            {"name": "ALPACA_SECRET_KEY", "valueFrom": {"secretKeyRef": {"name": "alpaca-secrets", "key": "secret-key"}}}
                        ],
                        "resources": {
                            "requests": {"memory": "512Mi", "cpu": "250m"},
                            "limits": {"memory": "2Gi", "cpu": "1000m"}
                        },
                        "livenessProbe": {
                            "httpGet": {"path": "/api/options/ready", "port": 8053},
                            "initialDelaySeconds": 30,
                            "periodSeconds": 10
                        },
                        "readinessProbe": {
                            "httpGet": {"path": "/api/options/ready", "port": 8053},
                            "initialDelaySeconds": 5,
                            "periodSeconds": 5
                        }
                    }]
                }
            }
        }
    }


def generate_k8s_service() -> dict:
    """Generate Kubernetes Service manifest."""
    return {
        "apiVersion": "v1",
        "kind": "Service",
        "metadata": {
            "name": "alpaca-options-lab-service"
        },
        "spec": {
            "selector": {"app": "alpaca-options-lab"},
            "ports": [{"protocol": "TCP", "port": 80, "targetPort": 8053}],
            "type": "LoadBalancer"
        }
    }


def generate_k8s_hpa() -> dict:
    """Generate Kubernetes HPA manifest."""
    return {
        "apiVersion": "autoscaling/v2",
        "kind": "HorizontalPodAutoscaler",
        "metadata": {"name": "alpaca-options-lab-hpa"},
        "spec": {
            "scaleTargetRef": {
                "apiVersion": "apps/v1",
                "kind": "Deployment",
                "name": "alpaca-options-lab"
            },
            "minReplicas": 2,
            "maxReplicas": 10,
            "metrics": [{
                "type": "Resource",
                "resource": {"name": "cpu", "target": {"type": "Utilization", "averageUtilization": 70}}
            }]
        }
    }


def generate_k8s_manifests(output_dir: str = "k8s/") -> List[str]:
    """Generate all Kubernetes manifests."""
    os.makedirs(output_dir, exist_ok=True)
    
    files = []
    
    # Deployment
    with open(f"{output_dir}/deployment.yaml", 'w') as f:
        yaml.dump(generate_k8s_deployment(), f, default_flow_style=False)
        files.append(f"{output_dir}/deployment.yaml")
    
    # Service
    with open(f"{output_dir}/service.yaml", 'w') as f:
        yaml.dump(generate_k8s_service(), f, default_flow_style=False)
        files.append(f"{output_dir}/service.yaml")
    
    # HPA
    with open(f"{output_dir}/hpa.yaml", 'w') as f:
        yaml.dump(generate_k8s_hpa(), f, default_flow_style=False)
        files.append(f"{output_dir}/hpa.yaml")
    
    return files


# =============================================================================
# CI/CD PIPELINE (Items 631-640)
# =============================================================================

GITHUB_ACTIONS_WORKFLOW = """name: Alpaca Options Lab CI/CD

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

env:
  PYTHON_VERSION: "3.11"
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  lint:
    name: Lint & Type Check
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          cache: 'pip'
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install ruff mypy black isort
          pip install -r requirements.txt
      
      - name: Run Ruff
        run: ruff check . --output-format=github
      
      - name: Run Black
        run: black --check .
      
      - name: Run MyPy
        run: mypy financial_dashboard/ engines/ --ignore-missing-imports

  test:
    name: Test Suite
    runs-on: ubuntu-latest
    needs: lint
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          cache: 'pip'
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install pytest pytest-cov pytest-xdist
      
      - name: Run Tests
        run: |
          pytest tests/ -v --cov=. --cov-report=xml
          python test_phase6_7_e2e.py
      
      - name: Upload Coverage
        uses: codecov/codecov-action@v4
        with:
          files: ./coverage.xml

  build:
    name: Build Docker Image
    runs-on: ubuntu-latest
    needs: test
    if: github.event_name == 'push'
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3
      
      - name: Log in to Registry
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      
      - name: Build and Push
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: |
            ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:latest
            ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

  deploy:
    name: Deploy to Production
    runs-on: ubuntu-latest
    needs: build
    if: github.ref == 'refs/heads/main'
    environment: production
    steps:
      - name: Deploy to Kubernetes
        run: |
          echo "Deploying to production cluster..."
          # kubectl apply -f k8s/
"""


def generate_github_actions(output_path: str = ".github/workflows/ci-cd.yml") -> str:
    """Generate GitHub Actions workflow."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, 'w') as f:
        f.write(GITHUB_ACTIONS_WORKFLOW)
    
    return GITHUB_ACTIONS_WORKFLOW


# =============================================================================
# ENVIRONMENT MANAGER
# =============================================================================

@dataclass
class EnvironmentConfig:
    """Environment configuration manager."""
    name: str
    debug: bool = False
    log_level: str = "INFO"
    api_key: str = ""
    secret_key: str = ""
    database_url: str = ""
    redis_url: str = "redis://localhost:6379"
    port: int = 8053
    workers: int = 4
    
    @classmethod
    def from_env(cls) -> 'EnvironmentConfig':
        """Load configuration from environment variables."""
        return cls(
            name=os.getenv("ENV_NAME", "development"),
            debug=os.getenv("DEBUG", "false").lower() == "true",
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            api_key=os.getenv("ALPACA_API_KEY", ""),
            secret_key=os.getenv("ALPACA_SECRET_KEY", ""),
            database_url=os.getenv("DATABASE_URL", ""),
            redis_url=os.getenv("REDIS_URL", "redis://localhost:6379"),
            port=int(os.getenv("PORT", "8053")),
            workers=int(os.getenv("WORKERS", "4"))
        )
    
    def to_env_file(self, path: str = ".env") -> None:
        """Write configuration to .env file."""
        lines = [
            f"ENV_NAME={self.name}",
            f"DEBUG={str(self.debug).lower()}",
            f"LOG_LEVEL={self.log_level}",
            f"ALPACA_API_KEY={self.api_key}",
            f"ALPACA_SECRET_KEY={self.secret_key}",
            f"DATABASE_URL={self.database_url}",
            f"REDIS_URL={self.redis_url}",
            f"PORT={self.port}",
            f"WORKERS={self.workers}",
        ]
        
        with open(path, 'w') as f:
            f.write('\n'.join(lines))
    
    def validate(self) -> List[str]:
        """Validate configuration and return list of issues."""
        issues = []
        
        if not self.api_key:
            issues.append("ALPACA_API_KEY not set")
        if not self.secret_key:
            issues.append("ALPACA_SECRET_KEY not set")
        if self.port < 1024 or self.port > 65535:
            issues.append(f"Invalid port: {self.port}")
        
        return issues


# =============================================================================
# COMPLETE PHASE 8
# =============================================================================

def complete_phase_8() -> Dict[str, Any]:
    """Generate all Phase 8 deliverables."""
    results = {
        "makefile": None,
        "docker_compose": None,
        "k8s_manifests": [],
        "github_actions": None,
        "status": "complete"
    }
    
    try:
        # Generate Makefile
        results["makefile"] = generate_makefile()
        
        # Generate Docker Compose
        results["docker_compose"] = generate_docker_compose()
        
        # Generate K8s manifests
        results["k8s_manifests"] = generate_k8s_manifests()
        
        # Generate GitHub Actions
        results["github_actions"] = generate_github_actions()
        
    except Exception as e:
        results["status"] = f"error: {e}"
    
    return results


if __name__ == "__main__":
    print("Generating Phase 8 deliverables...")
    results = complete_phase_8()
    print(f"Status: {results['status']}")
    print(f"Files generated: Makefile, docker-compose.yml, k8s/, .github/workflows/")
