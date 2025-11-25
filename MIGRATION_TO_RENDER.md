Unified Financial Dashboard — Migration to Render.com

This document is a step-by-step migration guide for deploying the Unified Financial Dashboard project to Render using a single Blueprint (`render.yaml`). It assumes you are an admin for the Render account and have the project code in a GitHub repository.

Important constraints and notes
- You must NOT modify any existing application code, Dockerfiles, or docker-compose.yml files in the repository for this migration. This guide is planning-only and describes Render configuration and operational steps.
- Replace placeholders such as <GITHUB_REPO> in the `render.yaml` blueprint with your repository slug (for example: your-org/unified-dashboard).
- Render does not provide privileged superuser access by default. Installing TimescaleDB extensions may require Render support or using a compatible managed Timescale provider. See the Timescale section below.

Pre-flight checklist
1. Confirm repository on GitHub contains both `platform-stack/` and `financial_dashboard/` directories and all Dockerfiles are present.
2. Identify secrets needed (API keys, Doppler token, AWS keys, any third-party tokens). Prepare a list.
3. Choose Render region and plan sizes for each service and database.
4. Decide artifact storage for Mlflow: use S3/GCS for production (recommended). Rendering ephemeral disk is not suitable for long-term artifacts.

Files included in this migration package
- `render.yaml` — Render Blueprint describing services and managed databases.

Quick mapping summary (compose -> Render)
- platform-stack/postgres_db -> Render Managed PostgreSQL (market_data)
- platform-stack/timescaledb -> Render Managed PostgreSQL (timeseries_data) + Timescale extension note
- dagster (platform-stack) -> Private Service on Render built from `platform-stack/dagster_project/Dockerfile`
- mlflow (platform-stack) -> Private Service on Render using official image, with a Render-managed DB for backend store
- financial_dashboard/dash_app -> Web Service on Render built from `financial_dashboard/Dockerfile`
- financial_dashboard/options_service -> Private Service built from `financial_dashboard/Dockerfile.options`
- financial_dashboard/chatbot_service -> Private Service built from `financial_dashboard/Dockerfile.chatbot`

Step-by-step migration guide
1) Create Managed Databases on Render
   a. In the Render dashboard, go to Databases -> New -> PostgreSQL.
   b. Create one database for market data (name it `market_data` or `market-data` — the blueprint uses `market_data` logical name). Choose the desired plan and region.
   c. Create one database for timeseries data (name `timeseries_data`). IMPORTANT: If you require TimescaleDB native extensions (hypertables, continuous aggregations), you will need to enable the timescaledb extension. Render-managed Postgres does not grant superuser by default. Options:
      - Request Render support to enable the extension for your database (support may enable an extension for you), OR
      - Use a managed Timescale provider (Timescale Cloud) and update connection strings accordingly, OR
      - Use a separate server where you can install TimescaleDB.
   d. Create one database for Dagster state (name `dagster`) and one for Mlflow (`mlflow`).
   e. Note the connection strings, hostnames, ports, usernames, and passwords provided by Render for each DB. You'll need them to populate env vars or secret envGroups.

2) Create Environment Group for secrets (optional but recommended)
   a. In Render, go to Account -> Environment Groups -> New Environment Group.
   b. Create a group (example: `doppler-secrets`) and add all secret keys you need (DOPPLER_TOKEN, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, any third-party API keys). Do NOT store secrets in the repo.
   c. In the Blueprint (`render.yaml`) reference the env group name. After creating the Blueprint, attach the group to services that require these secrets.

3) Prepare the Blueprint
   a. Open `render.yaml` in the repository root (the file created alongside this guide). Replace `<GITHUB_REPO>` with your GitHub repo (e.g. `my-org/unified-dashboard`).
   b. Review service `dockerfile_path` entries to ensure the Dockerfile path matches the repo layout (they currently point to `financial_dashboard/Dockerfile`, `Dockerfile.options`, etc.).
   c. Confirm start commands in the blueprint (if provided) are compatible with your containers. If your Dockerfiles include ENTRYPOINT/CMD, Render will use the container start command; you can leave `start_command` empty to let the image’s default start behavior run.

4) Create a Blueprint in Render and link to GitHub
   a. In the Render dashboard, go to Blueprints -> Create New Blueprint.
   b. Paste the updated `render.yaml` content or point Render to the repository containing it. You may also create the services manually via the UI and skip the blueprint.
   c. When creating, Render will ask to connect to the GitHub repository and request permission to access the repo. Grant access for the org/repo.
   d. Validate Render parsing of the YAML and fix any schema issues flagged by Render. (If Render reports fields not recognized, adjust to Render's expected schema — the provided blueprint uses common Render keys but may need small edits depending on Render's schema changes.)

5) Attach Databases and Env Groups to services
   a. For each created service, attach the correct managed database via the Render UI or ensure the blueprint referenced them correctly. Services that require DB access (dash_app, options_service, dagster, mlflow) must have connection strings set as environment variables.
   b. Use Render’s connection secret feature or envGroups to provide sensitive values to services. Example env vars to set for dash_app and options_service:
      - DATABASE_URL=postgres://<USER>:<PASSWORD>@<HOST>:<PORT>/market_data
      - TIMESCALE_DB_URL=postgres://<USER>:<PASSWORD>@<HOST>:<PORT>/timeseries_data
      - DB_HOST=<HOST>
   c. For Dagster and Mlflow, set the backend store URIs using the managed database connection strings.

6) Secrets management and environment variables
   a. Never commit secrets to Git. Use Render environment variables or env groups.
   b. In the Blueprint we included an `env_groups` entry named `doppler-secrets`. After Blueprint creation, add secret keys to that group via the dashboard and attach the group to services.
   c. For service-specific env vars (e.g., OPTIONS_API_URL, CHATBOT_API_URL), you can leave them in the blueprint as non-secret values.

7) TimescaleDB extension setup (if needed)
   a. If your app uses TimescaleDB-specific features, you must enable the timescaledb extension. Render-managed Postgres instances typically do not allow creating arbitrary extensions as a non-superuser.
   b. Contact Render support to request the timescaledb extension on your DB, or use a Timescale-managed instance and update `TIMESCALE_DB_URL` accordingly.
   c. Once the extension is available, run the SQL to enable it in your database (using psql or the Render console):
      - CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

8) Mlflow artifacts storage
   a. Do NOT rely on Render ephemeral disk for long-term artifact storage. Configure Mlflow to use S3/GCS as the artifact store.
   b. Create an S3 bucket (or GCS) and add the appropriate credentials to the env group (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_DEFAULT_REGION, and S3 bucket name). Update MLFLOW_ARTIFACTS_DESTINATION to the S3 path (e.g., s3://my-mlflow-bucket/artifacts).
   c. Set MLFLOW_BACKEND_STORE_URI to the `mlflow` database connection string provided by Render.

9) Deploy services and validate
   a. Trigger the first deploy from the Render dashboard or push to the linked branch (main) if auto-deploy is enabled.
   b. Watch build logs. Build failures usually indicate missing build context, incorrect Dockerfile path, or build-time secrets not provided.
   c. After services start, check health endpoints (dash app at /, dagster at its endpoint, mlflow /health) and logs for errors.

10) Database migrations and initialization
   a. If your app requires schema migrations (alembic, flyway, or custom scripts), run them against the managed DBs. You can run a one-off job on Render (or run containers locally pointed at the Render DB) to apply migrations.
   b. For Dagster and Mlflow, verify the databases have the expected tables and that the services can connect.

11) Networking and internal services
   a. Render private services can communicate with each other on internal hostnames you configure. Use the service names you defined (e.g., `options-service`) when constructing internal URLs.
   b. The Dash app should reference backend APIs using internal hostnames (HTTP) or environment variables (OPTIONS_API_URL, CHATBOT_API_URL).

12) Backups and monitoring
   a. Enable automated backups for Render-managed databases (Render provides snapshot/backup features on paid plans). Configure retention and test restores.
   b. Configure log routing (e.g., to Papertrail/LogDNA or other providers) if you need central logs.

13) DNS and custom domains (optional)
   a. Add custom domains for the public `dash-app` service via Render's Domains section.
   b. Create DNS records pointing to Render as instructed in the UI, enable TLS.

14) Rollout and rollback
   a. Perform canary or staged deployments by creating separate services or branches in Render.
   b. Rollback: redeploy the last working commit or disable auto-deploy and deploy a known-good tag.

15) Post-migration checklist
   - Confirm all services are running and healthy.
   - Confirm that Dash can reach options_service and chatbot_service internally.
   - Verify Dagster jobs, Mlflow server, and database connections.
   - Verify backups are scheduled and accessible.
   - Remove local dependencies on docker-compose for production; keep compose files for local dev only.

Example env var examples (fill with Render-provided values)
- DATABASE_URL=postgres://postgres:<PASSWORD>@<HOST>:5432/market_data
- TIMESCALE_DB_URL=postgres://postgres:<PASSWORD>@<HOST>:5432/timeseries_data
- DAGSTER_POSTGRES_PASSWORD=<dagster-db password from Render>
- MLFLOW_BACKEND_STORE_URI=postgresql://<USER>:<PASSWORD>@<HOST>:5432/mlflow

Troubleshooting tips
- Build fails: check Dockerfile paths, context, and build logs for missing files.
- DB connection refused: ensure the service has the correct host/port from Render, and that network access is allowed.
- Timescale features failing: check that the extension is installed.
- Mlflow artifact errors: confirm S3 credentials and bucket permissions.

If you want, I can:
- Refine `render.yaml` with exact start commands and more accurate environment variable names after you confirm the Dockerfile ENTRYPOINTs and any build/start scripts (e.g., `start_options_service.sh`).
- Generate an updated blueprint that uses Render's exact YAML schema if you tell me which Render region and the exact GitHub repo slug to use.

End of guide.
