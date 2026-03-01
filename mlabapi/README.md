# mlabapi

Simple FastAPI wrapper around the `mlab-iqb` library that exposes IQB score
calculation over HTTP.

## Project Structure

```
mlabapi/
├── app.py              ← entry point, wires routers together
├── models/
│   └── schemas.py      ← Pydantic request/response schemas  (Model)
├── services/
│   └── iqb_service.py  ← business logic, wraps mlab-iqb     (Controller)
├── routes/
│   ├── health.py       ← GET /                               (View)
│   ├── config.py       ← GET /config                        (View)
│   └── score.py        ← POST /score  POST /score/mlab      (View)
├── Dockerfile
└── pyproject.toml
```

## Deploy to GCP (Cloud Run)

```bash
# Prerequisites: gcloud CLI installed and authenticated

# 1. Set your project
gcloud config set project YOUR_PROJECT_ID

# 2. Enable required APIs (one-time)
gcloud services enable run.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com

# 3. Create Artifact Registry repo (one-time)
gcloud artifacts repositories create m-lab \
  --repository-format=docker \
  --location=us-east1

# 4. Deploy (from repo root)
gcloud builds submit --config=mlabapi/cloudbuild.yaml \
  --substitutions=_PROJECT_ID=YOUR_PROJECT_ID
```

Cloud Run will give you a URL like `https://iqb-mlabapi-xxxx-ue.a.run.app`.

---

## Deploy to Azure (Container Apps)

```bash
# Prerequisites: az CLI installed and authenticated

# 1. Create a container registry (one-time)
az acr create --name yourregistry --resource-group iqb-rg \
  --sku Basic --admin-enabled true

# 2. Build and push image from repo root
az acr build --registry yourregistry \
  --image iqb-mlabapi:latest \
  --file mlabapi/Dockerfile .

# 3. Deploy via GitHub Actions
# → Edit .github/workflows/deploy-mlabapi-azure.yml (change env vars at top)
# → Add secrets to GitHub repo (AZURE_CREDENTIALS, REGISTRY_USERNAME, REGISTRY_PASSWORD)
# → Push to main branch — deployment runs automatically
```

Azure will give you a URL like `https://iqb-mlabapi.YOUR_ENV.eastus.azurecontainerapps.io`.

---

## Run locally (uv)

```bash
# From repo root
cd mlabapi
uv run uvicorn app:app --reload

# → http://localhost:8000
# → http://localhost:8000/docs  (Swagger UI)
```

## Run with Docker

> ⚠️ All Docker commands must be run from the **repository root**, not from `mlabapi/`.
> The image needs `library/` (local `mlab-iqb` source) which lives outside `mlabapi/`.

### Option A — docker compose (recommended)

```bash
# From repo root
docker compose up --build

# Stop
docker compose down
```

### Option B — plain docker build

```bash
# From repo root
cd iqb 
docker build -f mlabapi/Dockerfile -t mlabapi .
docker run --rm -p 8000:8000 mlabapi
```

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Health check |
| `GET` | `/config` | Full IQB configuration (use cases, weights, thresholds) |
| `POST` | `/score` | Calculate IQB score (all three datasets) |
| `POST` | `/score/mlab` | Calculate IQB score (M-Lab only, simpler body) |

## Example

```bash
curl -X POST http://localhost:8000/score/mlab \
  -H "Content-Type: application/json" \
  -d '{
    "download_throughput_mbps": 100,
    "upload_throughput_mbps": 50,
    "latency_ms": 20,
    "packet_loss": 0.001
  }'
```

```json
{"iqb_score": 0.95098}
```

