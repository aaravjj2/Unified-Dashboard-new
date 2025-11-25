RENDER Environment Group: Secrets to add

Below is a consolidated list of environment variables and secrets referenced across the repository. Create an Environment Group in Render (example name: doppler-secrets) and add these keys with their values. Attach the env group to services that need them (dash-app, options-service, chatbot-service, mlflow, dagster as applicable).

- Notes:
  - Do NOT store real secret values in the repo. Use Render's UI to add secrets.
  - Some variables have multiple legacy names supported by the code; add both if you rely on either.

Secrets list (grouped):

Dash / Frontend
- FINNHUB_API_KEY
- FINNHUB2_API_KEY
- POLYGON_API_KEY
- APCA_API_KEY_ID (or APCA_API_KEY)
- APCA_API_SECRET_KEY (or APCA_API_SECRET)
- ALPACA_API_KEY
- ALPACA_API_SECRET
- LAMBDATEST_USERNAME
- LAMBDATEST_ACCESS_KEY

Options / Backend
- FINNHUB_API_KEY
- FINNHUB2_API_KEY
- POLYGON_API_KEY
- APCA_API_KEY_ID
- APCA_API_SECRET_KEY
- ALPACA_API_KEY
- ALPACA_API_SECRET

Chatbot / AI
- GEMINI_API_KEY (or GEMINI_TOKEN)  # placeholder name; repo references to Gemini integration exist
- OPENAI_API_KEY (if applicable)
- OTHER_AI_KEY

Mlflow / Storage
- AWS_ACCESS_KEY_ID
- AWS_SECRET_ACCESS_KEY
- AWS_DEFAULT_REGION
- MLFLOW_ARTIFACTS_DESTINATION (S3 bucket path, e.g. s3://my-mlflow-bucket/artifacts)

Databases / Infrastructure
- DOPPLER_TOKEN (if using Doppler)
- DATABASE_URL (if overriding)
- TIMESCALE_DB_URL (if overriding)

Other third-party keys used in code
- FINNHUB_API_KEY_1
- FINNHUB_API_KEY_2
- FINNHUB_API_KEY_3
- POLYGON_API_KEY
- STRIPE_API_KEY (if used)
- SENDGRID_API_KEY (if used)

How to use:
1. Go to Render dashboard -> Environment Groups -> Create new group (e.g. doppler-secrets).
2. Add each key above with its secret value.
3. Attach the group to each service that needs it.

If you want, I can also produce a YAML snippet to inject these environment variables into the Render blueprint as `env_groups` references (but Render's schema validation may require minor adjustments in the UI).