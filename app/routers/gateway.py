import logging

from fastapi import APIRouter, Depends, Query, Request, status

from app.config import settings
from app.schemas.gateway import (
    ApiConfigCreateRequest,
    ApiConfigResponse,
    GatewayApiResponse,
    GatewayCreateRequest,
    GatewayDashboardResponse,
    GatewayResponse,
    GatewayUpdateRequest,
)
from app.services.gateway_service import GatewayService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/gateway", tags=["gateway"])


def get_gateway_service(request: Request) -> GatewayService:
    return request.app.state.gateway_service


# --- APIs ---


@router.post(
    "/apis",
    response_model=GatewayApiResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_api(
    api_id: str,
    service: GatewayService = Depends(get_gateway_service),
) -> GatewayApiResponse:
    return await service.create_api(api_id)


@router.get("/apis", response_model=list[GatewayApiResponse])
async def list_apis(
    service: GatewayService = Depends(get_gateway_service),
) -> list[GatewayApiResponse]:
    return await service.list_apis()


@router.get("/apis/{api_id}", response_model=GatewayApiResponse)
async def get_api(
    api_id: str,
    service: GatewayService = Depends(get_gateway_service),
) -> GatewayApiResponse:
    return await service.get_api(api_id)


@router.delete("/apis/{api_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_api(
    api_id: str,
    service: GatewayService = Depends(get_gateway_service),
) -> None:
    await service.delete_api(api_id)


# --- API Configs ---


@router.post(
    "/apis/{api_id}/configs",
    response_model=ApiConfigResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_api_config(
    api_id: str,
    body: ApiConfigCreateRequest,
    service: GatewayService = Depends(get_gateway_service),
) -> ApiConfigResponse:
    return await service.create_api_config(api_id, body)


@router.get(
    "/apis/{api_id}/configs", response_model=list[ApiConfigResponse]
)
async def list_api_configs(
    api_id: str,
    service: GatewayService = Depends(get_gateway_service),
) -> list[ApiConfigResponse]:
    return await service.list_api_configs(api_id)


@router.delete(
    "/apis/{api_id}/configs/{config_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_api_config(
    api_id: str,
    config_id: str,
    service: GatewayService = Depends(get_gateway_service),
) -> None:
    await service.delete_api_config(api_id, config_id)


# --- Gateways ---


@router.post(
    "/gateways",
    response_model=GatewayResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_gateway(
    body: GatewayCreateRequest,
    service: GatewayService = Depends(get_gateway_service),
) -> GatewayResponse:
    api_id = settings.gateway_api_id
    return await service.create_gateway(api_id, body)


@router.get("/gateways/{gateway_id}", response_model=GatewayResponse)
async def get_gateway(
    gateway_id: str,
    location: str = Query(default="us-central1"),
    service: GatewayService = Depends(get_gateway_service),
) -> GatewayResponse:
    return await service.get_gateway(gateway_id, location)


@router.patch("/gateways/{gateway_id}", response_model=GatewayResponse)
async def update_gateway(
    gateway_id: str,
    body: GatewayUpdateRequest,
    location: str = Query(default="us-central1"),
    service: GatewayService = Depends(get_gateway_service),
) -> GatewayResponse:
    api_id = settings.gateway_api_id
    return await service.update_gateway(
        gateway_id, api_id, body.api_config_id, location
    )


@router.delete(
    "/gateways/{gateway_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_gateway(
    gateway_id: str,
    location: str = Query(default="us-central1"),
    service: GatewayService = Depends(get_gateway_service),
) -> None:
    await service.delete_gateway(gateway_id, location)


# --- Dashboard ---


@router.get("/dashboard", response_model=GatewayDashboardResponse)
async def get_gateway_dashboard(
    service: GatewayService = Depends(get_gateway_service),
) -> GatewayDashboardResponse:
    return await service.get_dashboard(
        api_id=settings.gateway_api_id,
        gateway_id=settings.gateway_api_id,
        location=settings.gateway_region,
    )
