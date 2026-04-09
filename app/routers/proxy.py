import logging

from fastapi import APIRouter, Depends, Request, status

from app.config import settings
from app.schemas.proxy import (
    ProxyBuildFiles,
    ProxyDeployRequest,
    ProxyStatusResponse,
)
from app.services.proxy_service import ProxyService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/proxy", tags=["proxy"])


def get_proxy_service(request: Request) -> ProxyService:
    return request.app.state.proxy_service


@router.get("/status", response_model=ProxyStatusResponse)
async def get_proxy_status(
    service_name: str = "",
    region: str = "",
    service: ProxyService = Depends(get_proxy_service),
) -> ProxyStatusResponse:
    name = service_name or settings.proxy_service_name
    rgn = region or settings.vertex_ai_region
    return await service.get_proxy_status(name, rgn)


@router.post("/preview", response_model=ProxyBuildFiles)
async def preview_proxy_files(
    body: ProxyDeployRequest,
    service: ProxyService = Depends(get_proxy_service),
) -> ProxyBuildFiles:
    return service.generate_proxy_files(body)


@router.post(
    "/deploy",
    response_model=ProxyStatusResponse,
    status_code=status.HTTP_201_CREATED,
)
async def deploy_proxy(
    body: ProxyDeployRequest,
    service: ProxyService = Depends(get_proxy_service),
) -> ProxyStatusResponse:
    return await service.deploy_proxy(body)


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def delete_proxy(
    service_name: str = "",
    region: str = "",
    service: ProxyService = Depends(get_proxy_service),
) -> None:
    name = service_name or settings.proxy_service_name
    rgn = region or settings.vertex_ai_region
    await service.delete_proxy(name, rgn)
