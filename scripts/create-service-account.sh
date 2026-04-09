#!/usr/bin/env bash
# Create service accounts with IAM roles for the API Gateway + Cloud Run proxy.
#
# Creates two service accounts:
#   1. gateway-sa  -- used by API Gateway to invoke Cloud Run
#   2. proxy-sa    -- used by Cloud Run to call Vertex AI
#
# Usage: ./scripts/create-service-account.sh [PROJECT_ID]
set -euo pipefail

PROJECT_ID="${1:-${GCP_PROJECT_ID:-}}"

if [[ -z "$PROJECT_ID" ]]; then
    echo "Usage: $0 <PROJECT_ID>"
    exit 1
fi

echo "Project: $PROJECT_ID"
echo ""

# --- 1. Gateway Service Account ---
GW_SA_NAME="api-gateway-sa"
GW_SA_EMAIL="${GW_SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

echo "=== Gateway Service Account ==="
if gcloud iam service-accounts describe "$GW_SA_EMAIL" --project="$PROJECT_ID" &>/dev/null; then
    echo "  Already exists: $GW_SA_EMAIL"
else
    echo "  Creating $GW_SA_NAME ..."
    gcloud iam service-accounts create "$GW_SA_NAME" \
        --display-name="API Gateway Service Account" \
        --description="Used by API Gateway backend auth to invoke Cloud Run" \
        --project="$PROJECT_ID"
    echo "  Created: $GW_SA_EMAIL"
fi

# Gateway SA needs permission to invoke Cloud Run services
echo "  Granting roles/run.invoker ..."
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:$GW_SA_EMAIL" \
    --role="roles/run.invoker" \
    --condition=None \
    --quiet 2>/dev/null
echo "  Done."
echo ""

# --- 2. Proxy Service Account ---
PROXY_SA_NAME="vertex-proxy-sa"
PROXY_SA_EMAIL="${PROXY_SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

echo "=== Proxy Service Account ==="
if gcloud iam service-accounts describe "$PROXY_SA_EMAIL" --project="$PROJECT_ID" &>/dev/null; then
    echo "  Already exists: $PROXY_SA_EMAIL"
else
    echo "  Creating $PROXY_SA_NAME ..."
    gcloud iam service-accounts create "$PROXY_SA_NAME" \
        --display-name="Vertex AI Proxy Service Account" \
        --description="Used by Cloud Run proxy to call Vertex AI APIs" \
        --project="$PROJECT_ID"
    echo "  Created: $PROXY_SA_EMAIL"
fi

# Proxy SA needs Vertex AI user role for predictions + generative AI
echo "  Granting roles/aiplatform.user ..."
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:$PROXY_SA_EMAIL" \
    --role="roles/aiplatform.user" \
    --condition=None \
    --quiet 2>/dev/null

echo "  Done."
echo ""

echo "=== Summary ==="
echo "  Gateway SA (for API Gateway backend auth):"
echo "    $GW_SA_EMAIL"
echo ""
echo "  Proxy SA (for Cloud Run -> Vertex AI):"
echo "    $PROXY_SA_EMAIL"
echo ""
echo "Use these in your .env:"
echo "  PROXY_SERVICE_ACCOUNT=$PROXY_SA_EMAIL"
echo ""
echo "Use the Gateway SA email when creating API configs:"
echo "  Backend auth service account: $GW_SA_EMAIL"
