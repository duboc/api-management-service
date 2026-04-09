import logging
import os
import tempfile

import yaml

from app.schemas.gateway import (
    ApiConfigCreateRequest,
    ApiConfigResponse,
    GatewayApiResponse,
    GatewayCreateRequest,
    GatewayDashboardResponse,
    GatewayResponse,
)
from app.services.gcloud_runner import run_gcloud

logger = logging.getLogger(__name__)

SUPPORTED_GATEWAY_REGIONS = [
    "asia-northeast1",
    "australia-southeast1",
    "europe-west1",
    "europe-west2",
    "us-east1",
    "us-east4",
    "us-central1",
    "us-west2",
    "us-west3",
    "us-west4",
]


class GatewayService:
    def __init__(self, project_id: str) -> None:
        self._project_id = project_id

    # --- API ---

    async def create_api(self, api_id: str) -> GatewayApiResponse:
        logger.info("Creating API: %s", api_id)
        await run_gcloud(
            ["api-gateway", "apis", "create", api_id],
            project=self._project_id,
            parse_json=False,
        )
        return await self.get_api(api_id)

    async def get_api(self, api_id: str) -> GatewayApiResponse:
        logger.info("Describing API: %s", api_id)
        data = await run_gcloud(
            ["api-gateway", "apis", "describe", api_id],
            project=self._project_id,
        )
        return GatewayApiResponse(
            name=data.get("name", api_id),
            display_name=data.get("displayName", ""),
            state=data.get("state", ""),
            managed_service=data.get("managedService", ""),
            create_time=data.get("createTime"),
        )

    async def delete_api(self, api_id: str) -> None:
        logger.info("Deleting API: %s", api_id)
        await run_gcloud(
            ["api-gateway", "apis", "delete", api_id],
            project=self._project_id,
            parse_json=False,
        )

    async def list_apis(self) -> list[GatewayApiResponse]:
        data = await run_gcloud(
            ["api-gateway", "apis", "list"],
            project=self._project_id,
        )
        if not data:
            return []
        return [
            GatewayApiResponse(
                name=item.get("name", ""),
                display_name=item.get("displayName", ""),
                state=item.get("state", ""),
                managed_service=item.get("managedService", ""),
                create_time=item.get("createTime"),
            )
            for item in data
        ]

    # --- API Config ---

    def _generate_openapi_spec(self, backend_url: str) -> str:
        """Generate OpenAPI 2.0 spec for API Gateway.

        The Cloud Run proxy is transparent -- it forwards any path to
        Vertex AI and only adds the OAuth2 bearer token.  The gateway
        validates the API key and routes to the proxy.

        Uses path_translation: APPEND_PATH_TO_ADDRESS so the gateway
        appends the matched path to the backend URL automatically.

        Paths defined here are the routes exposed through the gateway.
        Vertex AI Discovery Document methods supported:
          - publishers/google/models/{model}:generateContent
          - publishers/google/models/{model}:streamGenerateContent
          - publishers/google/models/{model}:countTokens
          - endpoints/{endpoint}:predict
          - endpoints/{endpoint}:generateContent
        """
        backend = {
            "address": backend_url,
            "jwt_audience": backend_url,
            "path_translation": "APPEND_PATH_TO_ADDRESS",
        }

        body_param = {
            "name": "body",
            "in": "body",
            "required": True,
            "schema": {"type": "object"},
        }

        def _post_op(op_id, summary, secured=True):
            op = {
                "summary": summary,
                "operationId": op_id,
                "x-google-backend": backend,
                "parameters": [body_param],
                "responses": {"200": {"description": "OK"}},
            }
            if not secured:
                op["security"] = []
            return op

        spec = {
            "swagger": "2.0",
            "info": {
                "title": "Vertex AI Proxy API",
                "version": "1.0.0",
                "description": (
                    "API Gateway for Vertex AI. Validates API keys "
                    "and forwards to a transparent Cloud Run proxy."
                ),
            },
            "schemes": ["https"],
            "produces": ["application/json"],
            "securityDefinitions": {
                "api_key": {
                    "type": "apiKey",
                    "name": "key",
                    "in": "query",
                }
            },
            "security": [{"api_key": []}],
            "paths": {
                # --- Generative AI (publisher models) ---
                "/publishers/google/models/{model}:generateContent": {
                    "post": _post_op(
                        "generateContent",
                        "Generate content with a Gemini model",
                    ),
                },
                "/publishers/google/models/{model}:streamGenerateContent": {
                    "post": _post_op(
                        "streamGenerateContent",
                        "Stream generated content from a Gemini model",
                    ),
                },
                "/publishers/google/models/{model}:countTokens": {
                    "post": _post_op(
                        "countTokens",
                        "Count tokens for input content",
                    ),
                },
                "/publishers/google/models/{model}:embedContent": {
                    "post": _post_op(
                        "embedContent",
                        "Generate embeddings for input content",
                    ),
                },
                # --- Custom endpoints ---
                "/endpoints/{endpoint}:predict": {
                    "post": _post_op(
                        "predict",
                        "Online prediction on a deployed model",
                    ),
                },
                "/endpoints/{endpoint}:generateContent": {
                    "post": _post_op(
                        "endpointGenerateContent",
                        "Generate content on a tuned endpoint",
                    ),
                },
                "/endpoints/{endpoint}:rawPredict": {
                    "post": _post_op(
                        "rawPredict",
                        "Raw prediction with arbitrary payload",
                    ),
                },
                # --- Health ---
                "/health": {
                    "get": {
                        "summary": "Health check",
                        "operationId": "healthCheck",
                        "x-google-backend": backend,
                        "security": [],
                        "responses": {"200": {"description": "OK"}},
                    }
                },
            },
        }
        return yaml.dump(spec, default_flow_style=False)

    async def create_api_config(
        self, api_id: str, request: ApiConfigCreateRequest
    ) -> ApiConfigResponse:
        logger.info(
            "Creating API config: %s for API: %s",
            request.config_id,
            api_id,
        )
        spec_content = self._generate_openapi_spec(request.backend_url)

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write(spec_content)
            spec_path = f.name

        try:
            await run_gcloud(
                [
                    "api-gateway",
                    "api-configs",
                    "create",
                    request.config_id,
                    f"--api={api_id}",
                    f"--openapi-spec={spec_path}",
                    f"--backend-auth-service-account={request.service_account_email}",
                ],
                project=self._project_id,
                parse_json=False,
                timeout=600,
            )
        finally:
            os.unlink(spec_path)

        return await self.get_api_config(api_id, request.config_id)

    async def get_api_config(
        self, api_id: str, config_id: str
    ) -> ApiConfigResponse:
        data = await run_gcloud(
            [
                "api-gateway",
                "api-configs",
                "describe",
                config_id,
                f"--api={api_id}",
            ],
            project=self._project_id,
        )
        return ApiConfigResponse(
            name=data.get("name", config_id),
            state=data.get("state", ""),
            service_rollout_state=data.get("serviceRollout", {}).get(
                "state"
            ),
            create_time=data.get("createTime"),
        )

    async def list_api_configs(
        self, api_id: str
    ) -> list[ApiConfigResponse]:
        data = await run_gcloud(
            [
                "api-gateway",
                "api-configs",
                "list",
                f"--api={api_id}",
            ],
            project=self._project_id,
        )
        if not data:
            return []
        return [
            ApiConfigResponse(
                name=item.get("name", ""),
                state=item.get("state", ""),
                create_time=item.get("createTime"),
            )
            for item in data
        ]

    async def delete_api_config(
        self, api_id: str, config_id: str
    ) -> None:
        logger.info("Deleting API config: %s", config_id)
        await run_gcloud(
            [
                "api-gateway",
                "api-configs",
                "delete",
                config_id,
                f"--api={api_id}",
            ],
            project=self._project_id,
            parse_json=False,
        )

    # --- Gateway ---

    async def create_gateway(
        self, api_id: str, request: GatewayCreateRequest
    ) -> GatewayResponse:
        logger.info("Creating gateway: %s", request.gateway_id)
        if request.location not in SUPPORTED_GATEWAY_REGIONS:
            raise ValueError(
                f"Unsupported region: {request.location}. "
                f"Supported: {SUPPORTED_GATEWAY_REGIONS}"
            )
        await run_gcloud(
            [
                "api-gateway",
                "gateways",
                "create",
                request.gateway_id,
                f"--api={api_id}",
                f"--api-config={request.api_config_id}",
                f"--location={request.location}",
            ],
            project=self._project_id,
            parse_json=False,
            timeout=600,
        )
        return await self.get_gateway(request.gateway_id, request.location)

    async def get_gateway(
        self, gateway_id: str, location: str
    ) -> GatewayResponse:
        data = await run_gcloud(
            [
                "api-gateway",
                "gateways",
                "describe",
                gateway_id,
                f"--location={location}",
            ],
            project=self._project_id,
        )
        return GatewayResponse(
            name=data.get("name", gateway_id),
            api_config=data.get("apiConfig", ""),
            state=data.get("state", ""),
            default_hostname=data.get("defaultHostname", ""),
            create_time=data.get("createTime"),
            update_time=data.get("updateTime"),
        )

    async def update_gateway(
        self,
        gateway_id: str,
        api_id: str,
        new_config_id: str,
        location: str,
    ) -> GatewayResponse:
        logger.info(
            "Updating gateway %s to config %s", gateway_id, new_config_id
        )
        await run_gcloud(
            [
                "api-gateway",
                "gateways",
                "update",
                gateway_id,
                f"--api={api_id}",
                f"--api-config={new_config_id}",
                f"--location={location}",
            ],
            project=self._project_id,
            parse_json=False,
            timeout=600,
        )
        return await self.get_gateway(gateway_id, location)

    async def delete_gateway(
        self, gateway_id: str, location: str
    ) -> None:
        logger.info("Deleting gateway: %s", gateway_id)
        await run_gcloud(
            [
                "api-gateway",
                "gateways",
                "delete",
                gateway_id,
                f"--location={location}",
            ],
            project=self._project_id,
            parse_json=False,
        )

    # --- Dashboard ---

    async def get_dashboard(
        self, api_id: str, gateway_id: str, location: str
    ) -> GatewayDashboardResponse:
        dashboard = GatewayDashboardResponse()

        try:
            api_info = await self.get_api(api_id)
            dashboard.api_exists = True
            dashboard.api_name = api_info.name
            dashboard.managed_service = api_info.managed_service
        except Exception:
            logger.info("API %s not found", api_id)

        if dashboard.api_exists:
            try:
                gw = await self.get_gateway(gateway_id, location)
                dashboard.gateway_exists = True
                dashboard.gateway_url = f"https://{gw.default_hostname}"
                dashboard.gateway_state = gw.state
                dashboard.active_config = gw.api_config
            except Exception:
                logger.info("Gateway %s not found", gateway_id)

            try:
                dashboard.configs = await self.list_api_configs(api_id)
            except Exception:
                logger.info("Could not list configs for %s", api_id)

        return dashboard
