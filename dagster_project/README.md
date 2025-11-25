# Dagster project — Local development README

Purpose
-------
This `dagster_project` provides a scaffolded Dagster repository and a small development container to build, run, and test the data ingestion pipelines for the Unified Financial Dashboard. The primary goal is to discover and ingest data files (CSV / Parquet), run cleaning/transformation logic, and persist results to the Postgres database used by the platform-stack.

Prerequisites
-------------
- The main `platform-stack` must be running and providing Postgres. Start it from the repo root (if using the supplied compose files):

```bash
# from repo root
cd platform-stack
docker-compose up -d
```

- Ensure Postgres is reachable from your Dagster container. Two common ways to connect:
  1. If `platform-stack` exposes Postgres on a host port (example mapping `5434:5432`), you can use `host.docker.internal` (Docker Desktop) or your host IP and the exposed port.
  2. If you run Dagster in the same Docker network as the platform-stack Compose project, use the Postgres service name (for example `postgres_db`) and internal port `5432`.

Building the Dagster image
--------------------------
Build the Dagster image using the included `docker-compose.yml` inside `dagster_project/`.

```bash
cd dagster_project
# Build the image referenced by docker-compose
docker-compose build
```

Running the Dagster UI (Dagit)
-------------------------------
Before starting the container, export the `DATABASE_URL` environment variable so the Dagster container can connect to Postgres. The `DATABASE_URL` format used by SQLAlchemy/psycopg2 is:

```
postgresql+psycopg2://<USER>:<PASSWORD>@<HOST>:<PORT>/<DATABASE>
```

Examples
- If `platform-stack` exposes Postgres on host port `5434` and you use Docker Desktop (macOS/Windows):

```bash
export DATABASE_URL="postgresql+psycopg2://postgres:mysecret@host.docker.internal:5434/market_data"
cd dagster_project
docker-compose up -d
```

- If you have configured both Compose projects to share a Docker network and the Postgres service name is `postgres_db` (internal port `5432`):

```bash
# Use the internal service hostname; this only works if the services share a Docker network
export DATABASE_URL="postgresql+psycopg2://postgres:mysecret@postgres_db:5432/market_data"
cd dagster_project
docker-compose up -d
```

Notes on finding the correct hostname
- `host.docker.internal` works on Docker Desktop (macOS/Windows). On Linux, that hostname may not be available — you can use the host IP or run both Compose projects on a shared Docker network and use the service name.
- To run both Compose projects on the same network without editing files: create an external network and then run each compose with `--project-name` and `--compatibility` flags, or add `networks` entries. (These are advanced steps — for simple local testing, `host.docker.internal` is usually easiest on Docker Desktop.)

Verify Dagit is running
-----------------------
After `docker-compose up -d` the Dagit UI should be available at:

```
http://localhost:3000
```

Check logs:

```bash
docker-compose logs -f dagster_dev
```

Running pipelines
-----------------
- Open Dagit at `http://localhost:3000`.
- You will see repository and job names (once assets/jobs are implemented). Use the Dagit UI to launch runs, inspect run logs, and schedule or backfill jobs.

Local (non-container) development option
---------------------------------------
If you prefer to run Dagit on your host (no Docker), create a virtual environment and install dependencies:

```bash
cd dagster_project
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# Ensure DATABASE_URL is exported in your shell, see examples above
dagit -f jobs/ingestion_job.py -h 0.0.0.0 -p 3000
```

Testing
-------
A simple smoke test exists at `dagster_project/tests/test_ingestion_smoke.py`. Run via pytest in the container or on your host environment.

Troubleshooting
---------------
- If `dagit` cannot connect to Postgres, verify `DATABASE_URL` and network reachability.
- If imports fail in the container, ensure the image was built after updating `requirements.txt` and that you restarted the container.

Security & next steps
---------------------
- The development Dockerfile and compose are intended for local development only. For production, switch to secure credentials, use dedicated secrets management, and configure Dagster run storage and event logs to a durable external service (Postgres or object store).
- Consider configuring Dagster run and event storage to use the same Postgres or a separate Postgres instance for reliability.

If you want, I can also add a short `Makefile` with `build`, `up`, `down`, and `logs` targets to simplify the workflow.
