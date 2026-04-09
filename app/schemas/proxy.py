from typing import Optional

from pydantic import BaseModel


class ProxyDeployRequest(BaseModel):
    vertex_ai_endpoint_id: str = ""
    vertex_ai_model: str = "gemini-2.0-flash"
    vertex_ai_region: str = "us-central1"
    service_name: str = "vertex-ai-proxy"
    service_account_email: str = ""


class ProxyStatusResponse(BaseModel):
    deployed: bool = False
    service_name: str = ""
    url: str = ""
    region: str = ""
    vertex_ai_region: str = ""
    logs_url: str = ""


class ProxyBuildFiles(BaseModel):
    main_py: str
    requirements_txt: str
    dockerfile: str
