#!/usr/bin/env bash
# Deploy the expense agent to Cloud Run.
# Required env vars: PROJECT_ID, MONGO_URI, GOOGLE_API_KEY
# Optional: REGION (default: us-central1), SERVICE_NAME (default: expense-agent)
set -euo pipefail

PROJECT_ID="${PROJECT_ID:?Set PROJECT_ID}"
REGION="${REGION:-us-central1}"
SERVICE_NAME="${SERVICE_NAME:-expense-agent}"
REPO="${REPO:-cloud-run-source-deploy}"
MONGO_DB_NAME="${MONGO_DB_NAME:-expense_agent_db}"
MDB_MCP_URL="${MDB_MCP_URL:?Set MDB_MCP_URL (URL del servicio expense-mcp en Cloud Run, ej: https://expense-mcp-xxx.run.app/mcp)}"

COMMIT_SHA="$(git rev-parse HEAD 2>/dev/null || echo 'latest')"
IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/${SERVICE_NAME}:${COMMIT_SHA}"

echo "==> Deploying ${SERVICE_NAME} to ${REGION} (project: ${PROJECT_ID})"

# 1. Ensure Artifact Registry repo exists
gcloud artifacts repositories describe "${REPO}" \
  --location="${REGION}" --project="${PROJECT_ID}" &>/dev/null || \
gcloud artifacts repositories create "${REPO}" \
  --repository-format=docker \
  --location="${REGION}" \
  --project="${PROJECT_ID}"

# 2. Store secrets before build (Cloud Run deploy will reference them)
_upsert_secret() {
  local name="$1" value="$2"
  if gcloud secrets describe "${name}" --project="${PROJECT_ID}" &>/dev/null; then
    echo "${value}" | gcloud secrets versions add "${name}" \
      --data-file=- --project="${PROJECT_ID}"
  else
    echo "${value}" | gcloud secrets create "${name}" \
      --data-file=- --project="${PROJECT_ID}"
  fi
}

echo "==> Upserting secrets..."
_upsert_secret "MONGO_URI" "${MONGO_URI:?Set MONGO_URI}"
_upsert_secret "GOOGLE_API_KEY" "${GOOGLE_API_KEY:?Set GOOGLE_API_KEY}"

# 3. Build and push image via Cloud Build
echo "==> Building image..."
gcloud builds submit \
  --config cloudbuild.yaml \
  --project="${PROJECT_ID}" \
  --substitutions="COMMIT_SHA=${COMMIT_SHA},_REGION=${REGION},_SERVICE_NAME=${SERVICE_NAME},_REPO=${REPO}"

# 4. Deploy to Cloud Run from local gcloud
echo "==> Deploying to Cloud Run..."
gcloud run deploy "${SERVICE_NAME}" \
  --image="${IMAGE}" \
  --region="${REGION}" \
  --project="${PROJECT_ID}" \
  --platform=managed \
  --allow-unauthenticated \
  --min-instances=1 \
  --memory=1Gi \
  --cpu=1 \
  --timeout=300 \
  --set-secrets="MONGO_URI=MONGO_URI:latest,GOOGLE_API_KEY=GOOGLE_API_KEY:latest" \
  --set-env-vars="MONGO_DB_NAME=${MONGO_DB_NAME},MDB_MCP_URL=${MDB_MCP_URL}"

echo ""
echo "==> Done. Service URL:"
gcloud run services describe "${SERVICE_NAME}" \
  --region="${REGION}" --project="${PROJECT_ID}" \
  --format="value(status.url)"
