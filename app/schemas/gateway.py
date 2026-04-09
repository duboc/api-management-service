from typing import Optional

from pydantic import BaseModel


class GatewayApiResponse(BaseModel):
    name: str
    display_name: str = ""
    state: str = ""
    managed_service: str = ""
    create_time: Optional[str] = None


class ApiConfigCreateRequest(BaseModel):
    config_id: str
    backend_url: str
    service_account_email: str


class ApiConfigResponse(BaseModel):
    name: str
    state: str = ""
    service_rollout_state: Optional[str] = None
    create_time: Optional[str] = None


class GatewayCreateRequest(BaseModel):
    gateway_id: str
    api_config_id: str
    location: str = "us-central1"


class GatewayResponse(BaseModel):
    name: str
    api_config: str = ""
    state: str = ""
    default_hostname: str = ""
    create_time: Optional[str] = None
    update_time: Optional[str] = None


class GatewayUpdateRequest(BaseModel):
    api_config_id: str


class GatewayDashboardResponse(BaseModel):
    api_exists: bool = False
    api_name: str = ""
    managed_service: str = ""
    gateway_exists: bool = False
    gateway_url: str = ""
    gateway_state: str = ""
    active_config: str = ""
    configs: list[ApiConfigResponse] = []
