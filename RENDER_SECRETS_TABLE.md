# Render Environment Group — Secrets Table

Create an Environment Group in Render (suggested name: `doppler-secrets`) and add the following keys and values. Attach the group to services that require them (dash-app, options-service, chatbot-service, mlflow, dagster).

| Variable name | Service(s) | Notes |
|---|---:|---|
| DOPPLER_TOKEN | any | If you use Doppler to manage secrets locally. |
| LAMBDATEST_USERNAME | dash, tests | LambdaTest credentials for cloud browser tests |
| LAMBDATEST_ACCESS_KEY | dash, tests | LambdaTest secret key |
| GEMINI_API_KEY | chatbot | If you integrate Gemini/Vertex-like AI API |
| OPENAI_API_KEY | chatbot | Alternative AI provider key (if used) |
| APCA_API_KEY_ID | dash, backends | Alpaca trading API key (legacy name APCA_API_KEY) |
| APCA_API_SECRET_KEY | dash, backends | Alpaca trading API secret (legacy name APCA_API_SECRET) |
| ALPACA_API_KEY | dash, backends | Alternate Alpaca env name |
| ALPACA_API_SECRET | dash, backends | Alternate Alpaca secret name |
| FINNHUB_API_KEY | dash, options, news | Finnhub primary API key |
| FINNHUB2_API_KEY | dash, options, news | Secondary Finnhub key for rotation |
| FINNHUB_API_KEY_1 | news | alternate key naming used in code |
| FINNHUB_API_KEY_2 | news | alternate key naming used in code |
| FINNHUB_API_KEY_3 | news | alternate key naming used in code |
| POLYGON_API_KEY | dash, options | Polygon.io API key |
| POLYGON_API_KEY_ALT | dash | Alternate naming in a few scripts (add if used) |
| AWS_ACCESS_KEY_ID | mlflow | Required if using S3 for mlflow artifacts |
| AWS_SECRET_ACCESS_KEY | mlflow | Required if using S3 for mlflow artifacts |
| AWS_DEFAULT_REGION | mlflow | AWS region for S3 bucket |
| MLFLOW_ARTIFACTS_DESTINATION | mlflow | S3 path, e.g. s3://my-mlflow-bucket/artifacts |
| DATABASE_URL | any | Optional override connection string |
| TIMESCALE_DB_URL | any | Optional timescale specific connection string |
| STRIPE_API_KEY | optional | If Stripe is used anywhere in the app |
| SENDGRID_API_KEY | optional | If SendGrid is used for email |

Notes:
- Add both legacy and preferred names where the code supports multiple fallback names (e.g., APCA_* and ALPACA_*). 
- Do NOT commit secrets to the repo. Use Render's Environment Group UI to add secret values.
- For Mlflow artifacts, prefer an S3 or GCS bucket and set `MLFLOW_ARTIFACTS_DESTINATION` accordingly.
