#!/usr/bin/env bash
# End-to-end deployment: APIs, service accounts, Cloud Run proxy,
# API Gateway, and API key -- all in one script.
#
# Usage: ./scripts/deploy.sh [PROJECT_ID]
#
# After this script completes, run `python run.py` and the web UI
# will show all components deployed and ready.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

PROJECT_ID="${1:-${GCP_PROJECT_ID:-mestrealvaro}}"
REGION="${GCP_REGION:-us-central1}"
API_ID="${GATEWAY_API_ID:-vertex-api}"
CONFIG_ID="vertex-config-$(date +%Y%m%d-%H%M%S)"
GATEWAY_ID="${API_ID}-gw"
PROXY_SERVICE_NAME="vertex-ai-proxy"
GW_SA_NAME="api-gateway-sa"
PROXY_SA_NAME="vertex-proxy-sa"
KEY_DISPLAY_NAME="default-key"

GW_SA_EMAIL="${GW_SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
PROXY_SA_EMAIL="${PROXY_SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

echo "============================================"
echo "  API Gateway Manager - Full Deployment"
echo "============================================"
echo ""
echo "  Project:  $PROJECT_ID"
echo "  Region:   $REGION"
echo "  API:      $API_ID"
echo "  Gateway:  $GATEWAY_ID"
echo "  Proxy:    $PROXY_SERVICE_NAME"
echo ""

# ---- Step 1: Enable APIs ----
echo "--- Step 1/8: Enabling GCP APIs ---"
APIS=(
    aiplatform.googleapis.com
    apigateway.googleapis.com
    servicemanagement.googleapis.com
    servicecontrol.googleapis.com
    run.googleapis.com
    artifactregistry.googleapis.com
    cloudbuild.googleapis.com
    apikeys.googleapis.com
    iam.googleapis.com
)
for api in "${APIS[@]}"; do
    echo -n "  $api ... "
    gcloud services enable "$api" --project="$PROJECT_ID" 2>/dev/null && echo "OK" || echo "SKIP"
done
echo ""

# ---- Step 2: Create Service Accounts ----
echo "--- Step 2/8: Creating service accounts ---"

# Gateway SA (invokes Cloud Run)
if gcloud iam service-accounts describe "$GW_SA_EMAIL" --project="$PROJECT_ID" &>/dev/null; then
    echo "  Gateway SA exists: $GW_SA_EMAIL"
else
    echo "  Creating $GW_SA_NAME ..."
    gcloud iam service-accounts create "$GW_SA_NAME" \
        --display-name="API Gateway Service Account" \
        --project="$PROJECT_ID" --quiet
fi
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:$GW_SA_EMAIL" \
    --role="roles/run.invoker" \
    --condition=None --quiet &>/dev/null
echo "  Gateway SA: $GW_SA_EMAIL (roles/run.invoker)"

# Proxy SA (calls Vertex AI)
if gcloud iam service-accounts describe "$PROXY_SA_EMAIL" --project="$PROJECT_ID" &>/dev/null; then
    echo "  Proxy SA exists: $PROXY_SA_EMAIL"
else
    echo "  Creating $PROXY_SA_NAME ..."
    gcloud iam service-accounts create "$PROXY_SA_NAME" \
        --display-name="Vertex AI Proxy Service Account" \
        --project="$PROJECT_ID" --quiet
fi
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:$PROXY_SA_EMAIL" \
    --role="roles/aiplatform.user" \
    --condition=None --quiet &>/dev/null
echo "  Proxy SA:   $PROXY_SA_EMAIL (roles/aiplatform.user)"

# Cloud Build needs storage, artifact registry, and logging access for gcloud run deploy --source
PROJECT_NUM=$(gcloud projects describe "$PROJECT_ID" --format="value(projectNumber)")
for sa in "${PROJECT_NUM}-compute@developer.gserviceaccount.com" "${PROJECT_NUM}@cloudbuild.gserviceaccount.com"; do
    for role in roles/storage.admin roles/artifactregistry.writer roles/logging.logWriter; do
        gcloud projects add-iam-policy-binding "$PROJECT_ID" \
            --member="serviceAccount:$sa" \
            --role="$role" \
            --condition=None --quiet &>/dev/null
    done
done
echo "  Cloud Build permissions: OK"
echo ""

# ---- Step 3: Deploy Cloud Run Proxy ----
echo "--- Step 3/8: Deploying Cloud Run proxy ---"

BUILD_DIR=$(mktemp -d)
trap "rm -rf $BUILD_DIR" EXIT

# Write proxy source files
python3 -c "
from app.services.proxy_service import PROXY_MAIN_PY, PROXY_REQUIREMENTS_TXT, PROXY_DOCKERFILE
import os, sys
build_dir = sys.argv[1]
with open(os.path.join(build_dir, 'main.py'), 'w') as f:
    f.write(PROXY_MAIN_PY)
with open(os.path.join(build_dir, 'requirements.txt'), 'w') as f:
    f.write(PROXY_REQUIREMENTS_TXT)
with open(os.path.join(build_dir, 'Dockerfile'), 'w') as f:
    f.write(PROXY_DOCKERFILE)
print('  Proxy source files written to', build_dir)
" "$BUILD_DIR"

echo "  Deploying $PROXY_SERVICE_NAME to Cloud Run (this may take 2-5 minutes) ..."
gcloud run deploy "$PROXY_SERVICE_NAME" \
    --source="$BUILD_DIR" \
    --region="$REGION" \
    --platform=managed \
    --no-allow-unauthenticated \
    --service-account="$PROXY_SA_EMAIL" \
    --set-env-vars="GCP_PROJECT_ID=${PROJECT_ID},VERTEX_AI_REGION=${REGION}" \
    --project="$PROJECT_ID" \
    --quiet

PROXY_URL=$(gcloud run services describe "$PROXY_SERVICE_NAME" \
    --region="$REGION" \
    --platform=managed \
    --project="$PROJECT_ID" \
    --format="value(status.url)")

echo "  Proxy deployed: $PROXY_URL"
echo ""

# ---- Step 4: Create API Gateway API ----
echo "--- Step 4/8: Creating API Gateway API ---"

if gcloud api-gateway apis describe "$API_ID" --project="$PROJECT_ID" &>/dev/null 2>&1; then
    echo "  API already exists: $API_ID"
else
    echo "  Creating API: $API_ID ..."
    gcloud api-gateway apis create "$API_ID" \
        --project="$PROJECT_ID" --quiet
    echo "  API created: $API_ID"
fi
echo ""

# ---- Step 5: Generate OpenAPI spec ----
echo "--- Step 5/8: Generating OpenAPI spec ---"

SPEC_FILE=$(mktemp /tmp/openapi-XXXXXX.yaml)

python3 -c "
from app.services.gateway_service import GatewayService
svc = GatewayService('$PROJECT_ID')
spec = svc._generate_openapi_spec('$PROXY_URL')
with open('$SPEC_FILE', 'w') as f:
    f.write(spec)
print('  OpenAPI spec written to $SPEC_FILE')
"
echo ""

# ---- Step 6: Create API Config ----
echo "--- Step 6/8: Creating API config (this may take 3-5 minutes) ---"
echo "  Config ID: $CONFIG_ID"
echo "  Backend auth SA: $GW_SA_EMAIL"

gcloud api-gateway api-configs create "$CONFIG_ID" \
    --api="$API_ID" \
    --openapi-spec="$SPEC_FILE" \
    --backend-auth-service-account="$GW_SA_EMAIL" \
    --project="$PROJECT_ID" \
    --quiet

rm -f "$SPEC_FILE"
echo "  API config created: $CONFIG_ID"
echo ""

# ---- Step 7: Deploy Gateway ----
echo "--- Step 7/8: Deploying API Gateway (this may take 3-5 minutes) ---"

if gcloud api-gateway gateways describe "$GATEWAY_ID" --location="$REGION" --project="$PROJECT_ID" &>/dev/null 2>&1; then
    echo "  Gateway exists, updating config ..."
    gcloud api-gateway gateways update "$GATEWAY_ID" \
        --api="$API_ID" \
        --api-config="$CONFIG_ID" \
        --location="$REGION" \
        --project="$PROJECT_ID" \
        --quiet
else
    echo "  Creating gateway: $GATEWAY_ID ..."
    gcloud api-gateway gateways create "$GATEWAY_ID" \
        --api="$API_ID" \
        --api-config="$CONFIG_ID" \
        --location="$REGION" \
        --project="$PROJECT_ID" \
        --quiet
fi

GATEWAY_URL=$(gcloud api-gateway gateways describe "$GATEWAY_ID" \
    --location="$REGION" \
    --project="$PROJECT_ID" \
    --format="value(defaultHostname)")

echo "  Gateway deployed: https://$GATEWAY_URL"
echo ""

# ---- Step 8: Create API Key ----
echo "--- Step 8/8: Creating API key ---"

MANAGED_SERVICE=$(gcloud api-gateway apis describe "$API_ID" \
    --project="$PROJECT_ID" \
    --format="value(managedService)")

echo "  Managed service: $MANAGED_SERVICE"

API_KEY_RESPONSE=$(python3 -c "
from google.cloud import api_keys_v2
from google.cloud.api_keys_v2 import types

client = api_keys_v2.ApiKeysClient()
parent = 'projects/$PROJECT_ID/locations/global'

key = types.Key(
    display_name='$KEY_DISPLAY_NAME',
    restrictions=types.Restrictions(
        api_targets=[types.ApiTarget(service='$MANAGED_SERVICE')]
    ) if '$MANAGED_SERVICE' else None,
)

op = client.create_key(parent=parent, key=key)
created = op.result()
key_string = client.get_key_string(name=created.name).key_string

print(f'KEY_UID={created.uid}')
print(f'KEY_STRING={key_string}')
print(f'KEY_NAME={created.name}')
")

eval "$API_KEY_RESPONSE"
echo "  API key created: $KEY_UID"
echo ""

# ---- Write .env ----
echo "--- Writing .env ---"

cat > "$PROJECT_DIR/.env" << EOF
# === API Gateway Manager Configuration ===
# Generated by scripts/deploy.sh on $(date -u +%Y-%m-%dT%H:%M:%SZ)

# GCP Project
GCP_PROJECT_ID=$PROJECT_ID
GCP_REGION=$REGION

# App Server
HOST=0.0.0.0
PORT=8081
LOG_LEVEL=INFO

# API Gateway
GATEWAY_API_ID=$API_ID
GATEWAY_REGION=$REGION

# Cloud Run Proxy
PROXY_SERVICE_NAME=$PROXY_SERVICE_NAME
PROXY_SERVICE_ACCOUNT=$PROXY_SA_EMAIL

# Vertex AI
VERTEX_AI_ENDPOINT_ID=
VERTEX_AI_REGION=$REGION
VERTEX_AI_MODEL=gemini-3.0-flash-preview
EOF

echo "  .env written"
echo ""

# ---- Summary ----
echo "============================================"
echo "  Deployment Complete"
echo "============================================"
echo ""
echo "  Gateway URL:  https://$GATEWAY_URL"
echo "  Proxy URL:    $PROXY_URL"
echo "  API Key:      $KEY_STRING"
echo "  API Key UID:  $KEY_UID"
echo ""
echo "  Start the app:"
echo "    python run.py"
echo "    open http://localhost:8081"
echo ""
echo "  Test with curl:"
echo ""
echo "    curl -X POST \"https://$GATEWAY_URL/publishers/google/models/gemini-3.0-flash-preview:generateContent?key=$KEY_STRING\" \\"
echo "      -H \"Content-Type: application/json\" \\"
echo "      -d '{"
echo "        \"contents\": [{"
echo "          \"role\": \"user\","
echo "          \"parts\": [{\"text\": \"Say hello in one word.\"}]"
echo "        }]"
echo "      }'"
echo ""
echo "============================================"
