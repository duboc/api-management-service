import logging

from fastapi import APIRouter, Depends, Request, status

from app.schemas.api_keys import (
    KeyCreateRequest,
    KeyListResponse,
    KeyResponse,
)
from app.services.api_keys_service import ApiKeysService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/keys", tags=["api-keys"])


def get_api_keys_service(request: Request) -> ApiKeysService:
    return request.app.state.api_keys_service


def get_managed_service(request: Request) -> str:
    return getattr(request.app.state, "gateway_managed_service", "")


@router.get("", response_model=KeyListResponse)
def list_keys(
    service: ApiKeysService = Depends(get_api_keys_service),
) -> KeyListResponse:
    keys = service.list_keys()
    return KeyListResponse(keys=keys, total_count=len(keys))


@router.post(
    "", response_model=KeyResponse, status_code=status.HTTP_201_CREATED
)
def create_key(
    body: KeyCreateRequest,
    service: ApiKeysService = Depends(get_api_keys_service),
    managed_service: str = Depends(get_managed_service),
) -> KeyResponse:
    return service.create_key(body, managed_service)


@router.get("/{key_id}/key-string")
def get_key_string(
    key_id: str,
    service: ApiKeysService = Depends(get_api_keys_service),
) -> dict:
    key_string = service.get_key_string(key_id)
    return {"key_string": key_string}


@router.delete("/{key_id}", response_model=KeyResponse)
def delete_key(
    key_id: str,
    service: ApiKeysService = Depends(get_api_keys_service),
) -> KeyResponse:
    return service.delete_key(key_id)
