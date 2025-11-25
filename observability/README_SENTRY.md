Sentry integration (Python + Docker)

Overview

This project includes a centralized Sentry initializer at `observability/sentry_config.py` which:

- Reads `SENTRY_DSN` from the environment to enable error and performance monitoring.
- Adds Flask and Logging integrations by default.
- Optionally adds Starlette integration (for FastAPI) if available.
- Uses `SENTRY_RELEASE` or `GIT_COMMIT` environment variables when present to set release information.

How to enable Sentry (local / Docker)

1. Obtain a Sentry DSN for your project.

2. Provide the DSN to the runtime via environment variable (preferred) or in `keys.env` mounted to `/app/config/keys.env`.

   Example `keys.env` entry:

   SENTRY_DSN=https://<public_key>@sentry.io/<project_id>
   SENTRY_RELEASE=1.2.3

3. Docker runtime behavior:

   - If `SENTRY_RELEASE` is not set, the container startup attempts to derive a short git commit via `git rev-parse --short HEAD` and exports it as `SENTRY_RELEASE`.
   - The application will log whether Sentry is configured on startup.

Notes and best practices

- Keep `SENTRY_DSN` secret. Use your orchestration platform (Kubernetes secrets, Docker secrets, or CI/CD secrets) to inject it at runtime.
- Control ingestion and sampling with these environment variables:
  - `SENTRY_TRACES_SAMPLE_RATE` (default 0.1)
  - `SENTRY_PROFILES_SAMPLE_RATE` (default 0.1)
- If you want release tracking to be populated automatically during your CI/CD pipeline, set `SENTRY_RELEASE` to your pipeline build id or git SHA there.

Quick checklist to verify

- Build the production image: `docker build --target production -t unified-dashboard:latest .`
- Run with DSN: `docker run -e SENTRY_DSN="<dsn>" -p 8050:8050 unified-dashboard:latest`
- Check container logs for `Sentry: configured` and `Sentry initialized successfully` messages.

If you need assistance wiring Sentry releases or uploading source maps, ask and I can add a CI step or show an example `sentry-cli` usage.
