from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    gcp_project_id: str = "mestrealvaro"
    gcp_region: str = "us-central1"
    host: str = "0.0.0.0"
    port: int = 8081
    log_level: str = "INFO"

    # API Gateway
    gateway_api_id: str = ""
    gateway_region: str = "us-central1"

    # Cloud Run
    proxy_service_name: str = ""
    proxy_service_account: str = ""

    # Vertex AI
    vertex_ai_endpoint_id: str = ""
    vertex_ai_region: str = "us-central1"
    vertex_ai_model: str = "gemini-3.0-flash-preview"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
