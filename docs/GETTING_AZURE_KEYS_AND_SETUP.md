# How to get Azure keys, create a Service Principal, and configure local secrets

This document tells you exactly what to do on your side to enable the dashboard's Azure ML integration. It covers both simple endpoint+API-key flows (if you have an endpoint that accepts an API key) and the recommended Service Principal + workspace flow (recommended for CI / production).

Follow these steps in order. Commands assume you have the Azure CLI (`az`) installed locally and are running from the project root.

---

## 1) Decide your auth mode

- Quick / temporary: copy an `AZURE_ML_ENDPOINT_URL` and `AZURE_ML_API_KEY` into your local env. Use when you already have a deployed endpoint which accepts a key.
- Recommended / production: create a Service Principal and provide the following env vars to the app: `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`, `AZURE_ML_WORKSPACE_NAME`, `AZURE_ML_RESOURCE_GROUP`.

The project accepts both patterns. When SP creds are present the app uses `ClientSecretCredential`/`DefaultAzureCredential` paths to authenticate and call the Azure ML SDK. If you only provide `AZURE_ML_ENDPOINT_URL` + `AZURE_ML_API_KEY`, the app will use the simpler REST call template. `AZURE_ML_USE_MOCK=true` keeps the app in safe mock mode.

---

## 2) Quick: Find an existing endpoint (if you have one)

1. In the Azure Portal, open your Azure Machine Learning Workspace.
2. Go to `Endpoints` -> select the endpoint you want to use.
3. Copy the endpoint's scoring URI (this becomes `AZURE_ML_ENDPOINT_URL`).
4. If the endpoint uses key-based auth, copy the key (or create new keys) — this will be `AZURE_ML_API_KEY`.

Set locally (example):

```bash
export AZURE_ML_USE_MOCK=false
export AZURE_ML_ENDPOINT_URL="https://<region>.inference.azureml.net/score/<endpoint-name>"
export AZURE_ML_API_KEY="<paste-key-here>"
```

If the endpoint requires AAD bearer tokens (managed identity), do NOT set `AZURE_ML_API_KEY`; instead use a Service Principal as described below.

---

## 3) Recommended: create a Service Principal (minimal commands)

Use these steps to create a Service Principal, restrict it to the resource group (least privilege), and save the JSON output.

Replace the placeholders before running.

```bash
# login interactively if needed
az login

# set subscription (optional)
az account set --subscription "<YOUR_SUBSCRIPTION_ID_OR_NAME>"

# create a service principal scoped to the resource group (least privilege recommended)
SUBSCRIPTION_ID="<your-subscription-id>"
RESOURCE_GROUP="<your-ml-resource-group>"
SP_NAME="unified-dashboard-sp-$(date +%s)"

az ad sp create-for-rbac \
  --name "$SP_NAME" \
  --role "Contributor" \
  --scopes "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP" \
  --sdk-auth

# The JSON printed contains the clientId, clientSecret, tenantId and other fields.
# Save it securely. Example file (do NOT commit):
#   ./secrets/unified-dashboard-sp.json
```

Notes:
- `--sdk-auth` prints a JSON blob you can reuse in CI (GitHub Actions `AZURE_CREDENTIALS`).
- If you want narrower permissions, consider an Azure role scoped specifically to the Workspace (Portal shows available RBAC roles) or the built-in `Azure Machine Learning Data Scientist` / `Machine Learning Workspace Contributor` roles when available.

After creation, export the environment variables used by the dashboard:

```bash
export AZURE_CLIENT_ID="<clientId from SP json>"
export AZURE_CLIENT_SECRET="<clientSecret from SP json>"
export AZURE_TENANT_ID="<tenantId from SP json>"
export AZURE_SUBSCRIPTION_ID="$SUBSCRIPTION_ID"
export AZURE_ML_WORKSPACE_NAME="<your-ml-workspace-name>"
export AZURE_ML_RESOURCE_GROUP="$RESOURCE_GROUP"
export AZURE_ML_USE_MOCK=false
```

Store the secret values in a secure secrets manager (Doppler, Azure Key Vault, or your CI secret store). Do NOT commit them to Git.

---

## 4) Create / deploy an Azure ML online endpoint (brief)

If you don't have a deployed endpoint yet, you can create one via Azure ML Studio or the CLI / SDK. High-level steps:

1. Register your model with Azure ML (Azure ML Studio or az ml commands).
2. Create a deployment yaml or use the Python SDK to create an `OnlineEndpoint` and an `OnlineDeployment`.
3. Deploy and wait for the endpoint to become `Healthy`.

Example using the Azure ML CLI (note: requires `azure-cli-ml` extension):

```bash
az extension add -n ml -y
az ml online-endpoint create --name my-endpoint -w $AZURE_ML_WORKSPACE_NAME -g $AZURE_ML_RESOURCE_GROUP
# then create deployment from YAML
az ml online-deployment create -f deployment.yml -n blue -e my-endpoint -w $AZURE_ML_WORKSPACE_NAME -g $AZURE_ML_RESOURCE_GROUP
az ml online-endpoint invoke --name my-endpoint -w $AZURE_ML_WORKSPACE_NAME -g $AZURE_ML_RESOURCE_GROUP --request-file ./sample_request.json
```

If you prefer using the Python SDK, instantiate an MLClient with `ClientSecretCredential` and use the `OnlineEndpoint`/`OnlineDeployment` helpers. See Azure docs for full examples.

After deployment, copy the endpoint scoring URI to `AZURE_ML_ENDPOINT_URL`. If the endpoint exposes keys, capture them as `AZURE_ML_API_KEY` (or configure AAD auth and keep keys empty so the app uses SP creds).

---

## 5) Local configuration: how to set these values for the dashboard

Preferred local options:

- Use a local `.env` file included in your environment loader (do NOT commit to Git). Example `.env` lines:

```text
AZURE_ML_USE_MOCK=false
AZURE_CLIENT_ID=...
AZURE_CLIENT_SECRET=...
AZURE_TENANT_ID=...
AZURE_SUBSCRIPTION_ID=...
AZURE_ML_WORKSPACE_NAME=...
AZURE_ML_RESOURCE_GROUP=...
# or
AZURE_ML_ENDPOINT_URL=https://...
AZURE_ML_API_KEY=...
```

- Or export to current shell before running the dashboard (temporary):

```bash
export AZURE_ML_USE_MOCK=false
export AZURE_CLIENT_ID="..."
export AZURE_CLIENT_SECRET="..."
# etc
python financial_dashboard/app.py
```

---

## 6) How to test the endpoint locally (two options)

Option A — If you have `AZURE_ML_ENDPOINT_URL` + `AZURE_ML_API_KEY` (simple REST):

```bash
# small example curl (adjust JSON to your model input schema)
curl -s -X POST "$AZURE_ML_ENDPOINT_URL" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $AZURE_ML_API_KEY" \
  -d '{"inputs": [[1,2,3]]}' | jq
```

Option B — If you use Service Principal and AAD auth (recommended): use the app's Python helper or the Azure SDK to call the endpoint. Minimal snippet (Python) using `requests` with a token:

```python
import os
import requests
from azure.identity import ClientSecretCredential

tenant = os.environ['AZURE_TENANT_ID']
client_id = os.environ['AZURE_CLIENT_ID']
client_secret = os.environ['AZURE_CLIENT_SECRET']
scope = os.environ.get('AZURE_ML_SCOPE', 'https://management.azure.com/.default')

cred = ClientSecretCredential(tenant, client_id, client_secret)
token = cred.get_token(scope)
headers = {'Authorization': 'Bearer ' + token.token, 'Content-Type': 'application/json'}
resp = requests.post(os.environ['AZURE_ML_ENDPOINT_URL'], headers=headers, json={"inputs": [[1,2,3]]})
print(resp.status_code, resp.text)
```

If you get a successful prediction, your credentials + endpoint are correct and the dashboard can call the endpoint.

---

## 7) Security recommendations

- Never commit secrets to Git. Add `.env` to `.gitignore`.
- Use a secret store for CI (Azure Key Vault, Doppler, GitHub Secrets) and inject secrets into CI runtime.
- Prefer Service Principal + RBAC over long-lived API keys. Use short-lived credentials or rotate SP secrets periodically.
- If using keys, rotate them and store them in a secret manager.

---

## 8) How to share minimally if you want me to run the deployment (securely)

Options:

- Best: create short-lived Service Principal credentials with minimal scope (resource-group access) and provide the `sdk-auth` JSON via a secure channel (not in Git). Then I can run deployment steps and delete the SP after.
- Alternative: run the local validator and share the resulting artifact (logs/screenshots) rather than sharing credentials.

When sharing credentials, prefer sending them into a CI run (GitHub Actions secret or Azure DevOps variable group) and grant me access to that run instead of handing raw secrets.

---

## 9) Quick checklist (copy/paste)

1. az login
2. az account set --subscription <id>
3. (Recommended) az ad sp create-for-rbac --name "unified-dashboard-sp" --role Contributor --scopes /subscriptions/<sub>/resourceGroups/<rg> --sdk-auth
4. Save SP JSON securely and set `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`
5. Deploy model / endpoint (or get existing endpoint URL + key). Set `AZURE_ML_ENDPOINT_URL` and `AZURE_ML_API_KEY` if using key-based.
6. Export env vars locally (or use .env / Doppler / Azure Key Vault)
7. Run the local validator (`python phase4_integration_diagnostic.py`) and a single Playwright smoke test

---

If you'd like, I can now:

- create the `scripts/validate_local_readiness.py` file and run it here, or
- run the local validator/diagnostic steps now (import checks, py_compile, and the diagnostic script) and report the results.

Pick one and I'll proceed.
