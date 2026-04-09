from pydantic import BaseModel


class OverallDashboardResponse(BaseModel):
    gcp_project_id: str
    # Gateway
    api_gateway_deployed: bool = False
    gateway_url: str = ""
    gateway_state: str = ""
    # Proxy
    proxy_deployed: bool = False
    proxy_url: str = ""
    # Keys
    api_key_count: int = 0
    # Console links
    gateway_console_url: str = ""
    cloud_run_console_url: str = ""
    vertex_ai_console_url: str = ""
