#!/usr/bin/env bash
# Enable all GCP APIs required by the API Gateway Manager.
# Usage: ./scripts/enable-gcp-apis.sh [PROJECT_ID]
set -euo pipefail

PROJECT_ID="${1:-${GCP_PROJECT_ID:-}}"

if [[ -z "$PROJECT_ID" ]]; then
    echo "Usage: $0 <PROJECT_ID>"
    echo "  or set GCP_PROJECT_ID env var"
    exit 1
fi

APIS=(
    # Vertex AI (predictions, generative AI)
    aiplatform.googleapis.com
    # API Gateway (key validation, routing)
    apigateway.googleapis.com
    # Required by API Gateway for managed services
    servicemanagement.googleapis.com
    servicecontrol.googleapis.com
    # Cloud Run (proxy hosting)
    run.googleapis.com
    # Container Registry / Artifact Registry (Cloud Run source deploys)
    artifactregistry.googleapis.com
    cloudbuild.googleapis.com
    # API Keys management
    apikeys.googleapis.com
    # IAM (service account creation)
    iam.googleapis.com
)

echo "Enabling ${#APIS[@]} APIs for project: $PROJECT_ID"
echo "---"

for api in "${APIS[@]}"; do
    echo -n "  $api ... "
    if gcloud services enable "$api" --project="$PROJECT_ID" 2>/dev/null; then
        echo "OK"
    else
        echo "FAILED (may need billing enabled or permissions)"
    fi
done

echo ""
echo "Done. Verify with:"
echo "  gcloud services list --enabled --project=$PROJECT_ID --filter='config.name:($( IFS=\  ; echo "${APIS[*]}" ))'"
