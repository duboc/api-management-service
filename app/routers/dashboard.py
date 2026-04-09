import logging

from fastapi import APIRouter, Depends, Request

from app.config import settings
from app.schemas.dashboard import OverallDashboardResponse
from app.services.api_keys_service import ApiKeysService
from app.services.gateway_service import GatewayService
from app.services.proxy_service import ProxyService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["dashboard"])


def get_gateway_service(request: Request) -> GatewayService:
    return request.app.state.gateway_service


def get_proxy_service(request: Request) -> ProxyService:
    return request.app.state.proxy_service


def get_api_keys_service(request: Request) -> ApiKeysService:
    return request.app.state.api_keys_service


@router.get("/dashboard", response_model=OverallDashboardResponse)
async def get_overall_dashboard(
    gw_service: GatewayService = Depends(get_gateway_service),
    proxy_service: ProxyService = Depends(get_proxy_service),
    keys_service: ApiKeysService = Depends(get_api_keys_service),
) -> OverallDashboardResponse:
    project = settings.gcp_project_id
    region = settings.gateway_region

    dashboard = OverallDashboardResponse(
        gcp_project_id=project,
        gateway_console_url=(
            f"https://console.cloud.google.com/api-gateway"
            f"?project={project}"
        ),
        cloud_run_console_url=(
            f"https://console.cloud.google.com/run"
            f"?project={project}"
        ),
        vertex_ai_console_url=(
            f"https://console.cloud.google.com/vertex-ai/endpoints"
            f"?project={project}"
        ),
    )

    # Gateway status
    if settings.gateway_api_id:
        try:
            gw_dashboard = await gw_service.get_dashboard(
                api_id=settings.gateway_api_id,
                gateway_id=settings.gateway_api_id,
                location=region,
            )
            dashboard.api_gateway_deployed = gw_dashboard.gateway_exists
            dashboard.gateway_url = gw_dashboard.gateway_url
            dashboard.gateway_state = gw_dashboard.gateway_state
        except Exception:
            logger.info("Could not fetch gateway dashboard")

    # Proxy status
    if settings.proxy_service_name:
        try:
            proxy_status = await proxy_service.get_proxy_status(
                settings.proxy_service_name, settings.vertex_ai_region
            )
            dashboard.proxy_deployed = proxy_status.deployed
            dashboard.proxy_url = proxy_status.url
        except Exception:
            logger.info("Could not fetch proxy status")

    # Key count
    try:
        keys = keys_service.list_keys()
        dashboard.api_key_count = len(keys)
    except Exception:
        logger.info("Could not fetch key count")

    return dashboard
