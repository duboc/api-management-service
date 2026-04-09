# API Gateway Manager

Web application for managing the full lifecycle of a Google Cloud API Gateway
that secures access to Vertex AI services through API key validation.

## Architecture

```mermaid
graph TB
    UI["Web UI<br/>(this app)<br/>localhost:8081"]

    UI -->|manages / deploys| GW
    UI -->|manages / deploys| PROXY
    UI -->|creates / restricts| KEYS

    subgraph GCP ["Google Cloud Platform"]
        subgraph AUTH_LAYER ["Authentication Layer"]
            KEYS["API Keys<br/>restricted to gateway<br/>managed service"]
            GW["API Gateway<br/>validates API keys"]
            GW_SA["api-gateway-sa<br/>roles/run.invoker"]
        end

        subgraph PROXY_LAYER ["Authorization Layer"]
            PROXY["Cloud Run Proxy<br/>path translation + auth"]
            PROXY_SA["vertex-proxy-sa<br/>roles/aiplatform.user"]
        end

        subgraph VERTEX_BOX ["Vertex AI API"]
            VERTEX["generateContent<br/>streamGenerateContent<br/>predict<br/>countTokens<br/>embedContent"]
        end

        KEYS -.->|"API key validates<br/>client identity"| GW
        GW -->|"x-google-backend<br/>(JWT from api-gateway-sa)"| PROXY
        GW_SA -.->|"invokes"| PROXY
        PROXY_SA -.->|"OAuth2 Bearer token"| VERTEX
        PROXY -->|"adds SA token<br/>translates /method to :method"| VERTEX
    end

    CLIENT["Client App"] -->|"API key in ?key= param<br/>No GCP credentials needed"| GW

    style UI fill:#4285F4,stroke:#1a73e8,color:#fff
    style CLIENT fill:#4285F4,stroke:#1a73e8,color:#fff
    style GW fill:#34A853,stroke:#1e8e3e,color:#fff
    style GW_SA fill:#34A853,stroke:#1e8e3e,color:#fff
    style PROXY fill:#FBBC04,stroke:#f9ab00,color:#333
    style PROXY_SA fill:#FBBC04,stroke:#f9ab00,color:#333
    style KEYS fill:#EA4335,stroke:#c5221f,color:#fff
    style VERTEX fill:#9334E6,stroke:#7627bb,color:#fff
    style GCP fill:#f8f9fa,stroke:#dadce0
    style AUTH_LAYER fill:#e8f5e9,stroke:#34A853
    style PROXY_LAYER fill:#fff8e1,stroke:#FBBC04
    style VERTEX_BOX fill:#f3e8fd,stroke:#9334E6
```

### Authentication & Authorization Flow

```mermaid
sequenceDiagram
    participant C as Client App
    participant GW as API Gateway
    participant P as Cloud Run Proxy<br/>(vertex-proxy-sa)
    participant V as Vertex AI

    Note over C: Only needs an API key<br/>No GCP credentials required

    C->>GW: POST /publishers/google/models/<br/>gemini-2.5-flash/generateContent<br/>?key=AIza...

    Note over GW: 1. Validate API key<br/>2. Check key is restricted<br/>to this gateway's<br/>managed service

    GW->>GW: API key valid?

    alt Invalid or unrestricted key
        GW-->>C: 403 Forbidden
    end

    Note over GW: 3. Attach JWT signed by<br/>api-gateway-sa<br/>(roles/run.invoker)

    GW->>P: Forward request + JWT<br/>(path appended to backend URL)

    Note over P: 4. Verify JWT from gateway<br/>5. Translate path:<br/>/model/generateContent<br/>to /model:generateContent<br/>6. Get OAuth2 token from<br/>vertex-proxy-sa<br/>(roles/aiplatform.user)

    P->>V: POST .../publishers/google/models/<br/>gemini-2.5-flash:generateContent<br/>Authorization: Bearer {SA OAuth2 token}

    V-->>P: JSON response (streamed)
    P-->>GW: Stream response back
    GW-->>C: JSON response
```

### Security Model

| Layer | Component | Credential | Purpose |
|---|---|---|---|
| **Client** | Your app | API key (`?key=AIza...`) | Identifies the client; no GCP access |
| **Gateway** | API Gateway | Validates API key | Ensures key is restricted to this gateway only |
| **Gateway -> Proxy** | `api-gateway-sa` | JWT (roles/run.invoker) | Authorizes gateway to invoke Cloud Run |
| **Proxy -> Vertex AI** | `vertex-proxy-sa` | OAuth2 token (roles/aiplatform.user) | Authorizes proxy to call Vertex AI |

> **The API key never reaches Vertex AI.** It is consumed by the API Gateway for client authentication. The Cloud Run proxy uses its own service account's OAuth2 token to authorize requests to Vertex AI.

### Key Design Decisions

- **Path-translating proxy**: The Cloud Run service translates slash-based
  gateway paths to Vertex AI's colon method syntax (e.g. `/model/generateContent`
  → `/model:generateContent`) and adds the OAuth2 bearer token. API Gateway
  doesn't support partial-segment path parameters like `{model}:method`.
- **API Gateway validates keys**: Uses OpenAPI 2.0 spec with `securityDefinitions`
  for API key auth and `x-google-backend` with `path_translation: APPEND_PATH_TO_ADDRESS`.
- **Model-agnostic**: The proxy forwards any model path -- Gemini, Imagen, embeddings,
  custom endpoints. No proxy changes needed for new models.
- **gcloud CLI via async subprocess**: Gateway and Cloud Run operations use
  `asyncio.create_subprocess_exec` for reliable deployment management.
- **google-cloud-api-keys client library**: API key CRUD uses the Python client
  directly (sync).

## Vertex AI Methods Exposed

Derived from the [Vertex AI Discovery Document](https://aiplatform.googleapis.com/$discovery/rest?version=v1):

| Gateway Path | Vertex AI Method | Auth |
|---|---|---|
| `/publishers/google/models/{model}/generateContent` | Generate content (Gemini) | API key |
| `/publishers/google/models/{model}/streamGenerateContent` | Streaming generation | API key |
| `/publishers/google/models/{model}/countTokens` | Count tokens | API key |
| `/publishers/google/models/{model}/embedContent` | Generate embeddings | API key |
| `/endpoints/{endpoint}/predict` | Online prediction (custom model) | API key |
| `/endpoints/{endpoint}/generateContent` | Generate content (tuned endpoint) | API key |
| `/endpoints/{endpoint}/rawPredict` | Raw prediction | API key |
| `/health` | Proxy health check | API key |

> **Note:** Gateway paths use slashes (`/generateContent`) instead of Vertex AI's colon syntax (`:generateContent`). The Cloud Run proxy translates them automatically.

## Prerequisites

- Python 3.11+
- [Google Cloud SDK](https://cloud.google.com/sdk/docs/install) (`gcloud` CLI)
- A GCP project with billing enabled
- Authenticated: `gcloud auth login && gcloud auth application-default login`

## Quick Start

### One-command deploy (recommended)

Deploys everything end-to-end: APIs, service accounts, Cloud Run proxy,
API Gateway, and creates an API key.

```bash
cd api-management-service
pip install -r requirements.txt
./scripts/deploy.sh mestrealvaro
python run.py
```

Open [http://localhost:8081](http://localhost:8081) -- all components will be deployed and visible.

### Step-by-step setup

If you prefer to set up each component individually:

```bash
# 1. Run setup (checks prereqs, generates .env, installs deps)
./scripts/setup.sh

# 2. Enable required GCP APIs
./scripts/enable-gcp-apis.sh <PROJECT_ID>

# 3. Create service accounts with proper IAM roles
./scripts/create-service-account.sh <PROJECT_ID>

# 4. Start the app and use the web UI to deploy each component
python run.py
```

Open [http://localhost:8081](http://localhost:8081)

## Setup Scripts

| Script | What it does |
|---|---|
| `scripts/deploy.sh` | **Full end-to-end deploy**: enable APIs, create SAs, deploy proxy, create gateway, create API key, write `.env` |
| `scripts/setup.sh` | Check prereqs, detect GCP config, generate `.env`, install Python deps |
| `scripts/enable-gcp-apis.sh` | Enable aiplatform, apigateway, run, apikeys, and supporting APIs |
| `scripts/create-service-account.sh` | Create `api-gateway-sa` (Cloud Run invoker) and `vertex-proxy-sa` (Vertex AI user) |

## Configuration

All settings are in `.env` (see `.env.example`):

```
GCP_PROJECT_ID=mestrealvaro         # GCP project
GCP_REGION=us-central1              # Default region
GATEWAY_API_ID=                     # Set after creating API via UI
PROXY_SERVICE_NAME=vertex-ai-proxy  # Cloud Run service name
PROXY_SERVICE_ACCOUNT=              # SA with roles/aiplatform.user
VERTEX_AI_REGION=us-central1        # Vertex AI region
VERTEX_AI_MODEL=gemini-2.5-flash    # Default Gemini model
```

## Project Structure

```
api-management-service/
+-- app/
|   +-- config.py                # Settings from .env
|   +-- main.py                  # FastAPI app, lifespan, exception handlers
|   +-- routers/
|   |   +-- dashboard.py         # GET /api/dashboard
|   |   +-- gateway.py           # /api/gateway/* (APIs, configs, gateways)
|   |   +-- proxy.py             # /api/proxy/* (status, preview, deploy)
|   |   +-- api_keys.py          # /api/keys/* (list, create, delete)
|   +-- schemas/
|   |   +-- dashboard.py         # OverallDashboardResponse
|   |   +-- gateway.py           # Gateway API/Config/Gateway models
|   |   +-- proxy.py             # ProxyDeployRequest, ProxyStatusResponse
|   |   +-- api_keys.py          # KeyCreateRequest, KeyResponse
|   +-- services/
|   |   +-- gcloud_runner.py     # Async subprocess wrapper for gcloud CLI
|   |   +-- gateway_service.py   # API Gateway CRUD + OpenAPI spec generation
|   |   +-- proxy_service.py     # Proxy code generation + Cloud Run deploy
|   |   +-- api_keys_service.py  # API key management via client library
|   +-- static/
|       +-- index.html           # Single-page UI
|       +-- css/app.css
|       +-- js/
|           +-- api.js           # ApiClient (gateway, proxy, keys)
|           +-- components.js    # UI rendering functions
|           +-- app.js           # Event handlers and data loading
+-- scripts/
|   +-- setup.sh
|   +-- enable-gcp-apis.sh
|   +-- create-service-account.sh
+-- tests/                       # 84 tests
|   +-- conftest.py
|   +-- test_gcloud_runner.py
|   +-- test_gateway_service.py
|   +-- test_proxy_service.py
|   +-- test_api_keys_service.py
|   +-- test_gateway_routes.py
|   +-- test_proxy_routes.py
|   +-- test_api_keys_routes.py
|   +-- test_dashboard_routes.py
+-- requirements.txt
+-- pyproject.toml
+-- run.py
+-- .env.example
```

## API Endpoints

### Dashboard
- `GET /api/dashboard` -- Aggregated status of gateway, proxy, and keys

### Gateway (`/api/gateway`)
- `POST /apis?api_id=...` -- Create API
- `GET /apis` -- List APIs
- `GET /apis/{api_id}` -- Get API details
- `DELETE /apis/{api_id}` -- Delete API
- `POST /apis/{api_id}/configs` -- Create API config (generates OpenAPI spec)
- `GET /apis/{api_id}/configs` -- List configs
- `DELETE /apis/{api_id}/configs/{config_id}` -- Delete config
- `POST /gateways` -- Deploy gateway
- `GET /gateways/{gateway_id}` -- Get gateway status
- `PATCH /gateways/{gateway_id}` -- Update gateway config
- `DELETE /gateways/{gateway_id}` -- Delete gateway
- `GET /dashboard` -- Gateway-specific dashboard

### Proxy (`/api/proxy`)
- `GET /status` -- Cloud Run service status
- `POST /preview` -- Preview generated proxy code
- `POST /deploy` -- Deploy transparent proxy to Cloud Run
- `DELETE /` -- Delete proxy service

### API Keys (`/api/keys`)
- `GET /` -- List keys
- `POST /` -- Create key (optionally restricted to gateway)
- `GET /{key_id}/key-string` -- Reveal key string
- `DELETE /{key_id}` -- Delete key

## Running Tests

```bash
python -m pytest tests/ -v
```

## Example: Calling Gemini through the Gateway

After deploying the gateway and creating an API key:

```bash
# Generate content with Gemini
curl -X POST "https://YOUR-GATEWAY.uc.gateway.dev/publishers/google/models/gemini-2.5-flash/generateContent?key=YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "contents": [{
      "role": "user",
      "parts": [{"text": "Explain API Gateway in one sentence."}]
    }]
  }'

# Count tokens
curl -X POST "https://YOUR-GATEWAY.uc.gateway.dev/publishers/google/models/gemini-2.5-flash/countTokens?key=YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "contents": [{
      "role": "user",
      "parts": [{"text": "Hello world"}]
    }]
  }'

# Custom endpoint prediction
curl -X POST "https://YOUR-GATEWAY.uc.gateway.dev/endpoints/1234567890/predict?key=YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "instances": [{"input": "data"}]
  }'
```

## GCP APIs Required

Enabled by `scripts/enable-gcp-apis.sh`:

- `aiplatform.googleapis.com` -- Vertex AI
- `apigateway.googleapis.com` -- API Gateway
- `servicemanagement.googleapis.com` -- Required by API Gateway
- `servicecontrol.googleapis.com` -- Required by API Gateway
- `run.googleapis.com` -- Cloud Run
- `artifactregistry.googleapis.com` -- Container images
- `cloudbuild.googleapis.com` -- Source deploys
- `apikeys.googleapis.com` -- API key management
- `iam.googleapis.com` -- Service account creation

## IAM Roles

Created by `scripts/create-service-account.sh`:

| Service Account | Role | Purpose |
|---|---|---|
| `api-gateway-sa` | `roles/run.invoker` | API Gateway backend auth to invoke Cloud Run |
| `vertex-proxy-sa` | `roles/aiplatform.user` | Cloud Run proxy to call Vertex AI APIs |
