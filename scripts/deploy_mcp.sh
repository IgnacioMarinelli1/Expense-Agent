#!/usr/bin/env bash
# Deploy the MongoDB MCP server as a standalone Cloud Run service.
# Required env vars: PROJECT_ID
# Optional: REGION (default: southamerica-east1), SERVICE_NAME (default: expense-mcp)
set -euo pipefail

PROJECT_ID="${PROJECT_ID:?Set PROJECT_ID}"
REGION="${REGION:-southamerica-east1}"
SERVICE_NAME="${SERVICE_NAME:-expense-mcp}"
REPO="${REPO:-cloud-run-source-deploy}"

COMMIT_SHA="$(git rev-parse HEAD 2>/dev/null || echo 'latest')"
IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/${SERVICE_NAME}:${COMMIT_SHA}"

echo "==> Deploying ${SERVICE_NAME} to ${REGION} (project: ${PROJECT_ID})"

# Build and push via Cloud Build
gcloud builds submit \
  --config cloudbuild-mcp.yaml \
  --project="${PROJECT_ID}" \
  --substitutions="COMMIT_SHA=${COMMIT_SHA},_REGION=${REGION},_SERVICE_NAME=${SERVICE_NAME},_REPO=${REPO}"

# Deploy to Cloud Run — MONGO_URI secret must already exist
echo "==> Deploying to Cloud Run..."
gcloud run deploy "${SERVICE_NAME}" \
  --image="${IMAGE}" \
  --region="${REGION}" \
  --project="${PROJECT_ID}" \
  --platform=managed \
  --allow-unauthenticated \
  --ingress=internal \
  --min-instances=1 \
  --memory=1Gi \
  --cpu=1 \
  --timeout=60 \
  --set-secrets="MDB_MCP_CONNECTION_STRING=MONGO_URI:latest"

echo ""
echo "==> MCP service URL:"
gcloud run services describe "${SERVICE_NAME}" \
  --region="${REGION}" --project="${PROJECT_ID}" \
  --format="value(status.url)"
echo ""
echo "==> Set in .env and deploy_agent.sh:"
echo "    MDB_MCP_URL=\$(gcloud run services describe ${SERVICE_NAME} --region=${REGION} --project=${PROJECT_ID} --format='value(status.url)')/mcp"
