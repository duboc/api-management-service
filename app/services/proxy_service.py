import logging
import os
import shutil
import tempfile

from app.schemas.proxy import ProxyBuildFiles, ProxyDeployRequest, ProxyStatusResponse
from app.services.gcloud_runner import GcloudError, run_gcloud

logger = logging.getLogger(__name__)

PROXY_MAIN_PY = '''"""Vertex AI proxy for Cloud Run.

This proxy manages authentication and path translation.  It adds
the OAuth2 bearer token from the attached service account and
translates slash-based paths from API Gateway to Vertex AI's colon
method syntax.

API Gateway does not support partial-segment path parameters
(e.g. {model}:generateContent), so the gateway uses slashes:
  /publishers/google/models/{model}/generateContent

This proxy translates them to Vertex AI's colon format:
  /publishers/google/models/{model}:generateContent

The API Gateway in front handles API key validation.
"""
import logging
import os

import google.auth
import google.auth.transport.requests
import requests as http_requests
from flask import Flask, Response, jsonify, request

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

app = Flask(__name__)

PROJECT_ID = os.environ["GCP_PROJECT_ID"]
REGION = os.environ.get("VERTEX_AI_REGION", "us-central1")

VERTEX_BASE = (
    f"https://{REGION}-aiplatform.googleapis.com/v1/"
    f"projects/{PROJECT_ID}/locations/{REGION}"
)

# Vertex AI methods that use colon syntax (:method)
VERTEX_METHODS = {
    "generateContent", "streamGenerateContent", "countTokens",
    "embedContent", "predict", "rawPredict",
}

_credentials = None


def _get_access_token():
    """Get access token from the service account attached to Cloud Run."""
    global _credentials
    if _credentials is None:
        _credentials, _ = google.auth.default(
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
    _credentials.refresh(google.auth.transport.requests.Request())
    return _credentials.token


def _translate_path(path):
    """Translate slash-based gateway path to Vertex AI colon format.

    /publishers/google/models/gemini-3.0-flash-preview/generateContent
    -> /publishers/google/models/gemini-3.0-flash-preview:generateContent
    """
    parts = path.rsplit("/", 1)
    if len(parts) == 2 and parts[1] in VERTEX_METHODS:
        return f"{parts[0]}:{parts[1]}"
    return path


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy", "project": PROJECT_ID, "region": REGION}), 200


@app.route("/<path:path>", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
def proxy(path):
    """Forward request to Vertex AI with auth and path translation."""
    translated = _translate_path(path)
    vertex_url = f"{VERTEX_BASE}/{translated}"
    logger.info("%s %s -> %s", request.method, request.path, vertex_url)

    token = _get_access_token()

    # Forward headers, replacing auth and host
    fwd_headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": request.content_type or "application/json",
    }

    resp = http_requests.request(
        method=request.method,
        url=vertex_url,
        headers=fwd_headers,
        data=request.get_data(),
        timeout=300,
        stream=True,
    )

    # Stream the response back as-is
    excluded_headers = {"content-encoding", "transfer-encoding", "connection"}
    response_headers = {
        k: v for k, v in resp.headers.items() if k.lower() not in excluded_headers
    }

    return Response(
        resp.iter_content(chunk_size=4096),
        status=resp.status_code,
        headers=response_headers,
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
'''

PROXY_REQUIREMENTS_TXT = """flask>=3.0.0,<4.0.0
gunicorn>=21.2.0,<23.0.0
google-auth>=2.20.0,<3.0.0
requests>=2.31.0,<3.0.0
"""

PROXY_DOCKERFILE = """FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .

CMD exec gunicorn --bind :$PORT --workers 1 --threads 2 --timeout 120 main:app
"""


class ProxyService:
    def __init__(
        self, project_id: str, default_region: str = "us-central1"
    ) -> None:
        self._project_id = project_id
        self._default_region = default_region

    def generate_proxy_files(
        self, request: ProxyDeployRequest
    ) -> ProxyBuildFiles:
        return ProxyBuildFiles(
            main_py=PROXY_MAIN_PY.strip(),
            requirements_txt=PROXY_REQUIREMENTS_TXT.strip(),
            dockerfile=PROXY_DOCKERFILE.strip(),
        )

    async def deploy_proxy(
        self, request: ProxyDeployRequest
    ) -> ProxyStatusResponse:
        logger.info(
            "Deploying proxy service '%s' for endpoint '%s'",
            request.service_name,
            request.vertex_ai_endpoint_id,
        )

        build_dir = tempfile.mkdtemp(prefix="vertex_proxy_")
        try:
            with open(os.path.join(build_dir, "main.py"), "w") as f:
                f.write(PROXY_MAIN_PY)
            with open(
                os.path.join(build_dir, "requirements.txt"), "w"
            ) as f:
                f.write(PROXY_REQUIREMENTS_TXT)
            with open(os.path.join(build_dir, "Dockerfile"), "w") as f:
                f.write(PROXY_DOCKERFILE)

            deploy_args = [
                "run",
                "deploy",
                request.service_name,
                f"--source={build_dir}",
                f"--region={request.vertex_ai_region}",
                "--platform=managed",
                "--no-allow-unauthenticated",
                f"--set-env-vars=GCP_PROJECT_ID={self._project_id},"
                f"VERTEX_AI_REGION={request.vertex_ai_region}",
            ]

            if request.service_account_email:
                deploy_args.append(
                    f"--service-account={request.service_account_email}"
                )

            await run_gcloud(
                deploy_args,
                project=self._project_id,
                parse_json=False,
                timeout=600,
            )
        finally:
            shutil.rmtree(build_dir, ignore_errors=True)

        return await self.get_proxy_status(
            request.service_name, request.vertex_ai_region
        )

    async def get_proxy_status(
        self, service_name: str, region: str
    ) -> ProxyStatusResponse:
        if not service_name:
            return ProxyStatusResponse(deployed=False)

        try:
            data = await run_gcloud(
                [
                    "run",
                    "services",
                    "describe",
                    service_name,
                    f"--region={region}",
                    "--platform=managed",
                ],
                project=self._project_id,
            )
        except GcloudError:
            return ProxyStatusResponse(
                deployed=False, service_name=service_name
            )

        url = data.get("status", {}).get("url", "")
        containers = (
            data.get("spec", {})
            .get("template", {})
            .get("spec", {})
            .get("containers", [{}])
        )
        env_vars = {}
        if containers:
            for env in containers[0].get("env", []):
                env_vars[env.get("name", "")] = env.get("value", "")

        logs_url = (
            f"https://console.cloud.google.com/logs/query;"
            f"query=resource.type%3D%22cloud_run_revision%22%20"
            f"resource.labels.service_name%3D%22{service_name}%22"
            f"?project={self._project_id}"
        )

        return ProxyStatusResponse(
            deployed=True,
            service_name=service_name,
            url=url,
            region=region,
            vertex_ai_region=env_vars.get("VERTEX_AI_REGION", ""),
            logs_url=logs_url,
        )

    async def delete_proxy(
        self, service_name: str, region: str
    ) -> None:
        logger.info("Deleting proxy service: %s", service_name)
        await run_gcloud(
            [
                "run",
                "services",
                "delete",
                service_name,
                f"--region={region}",
                "--platform=managed",
            ],
            project=self._project_id,
            parse_json=False,
        )
