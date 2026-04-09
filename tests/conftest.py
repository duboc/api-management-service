from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.schemas.api_keys import KeyResponse
from app.schemas.gateway import (
    ApiConfigResponse,
    GatewayApiResponse,
    GatewayDashboardResponse,
    GatewayResponse,
)
from app.schemas.proxy import ProxyBuildFiles, ProxyStatusResponse


# --- Sample Data ---


@pytest.fixture
def sample_api_response():
    return GatewayApiResponse(
        name="projects/mestrealvaro/locations/global/apis/my-api",
        display_name="my-api",
        state="ACTIVE",
        managed_service="my-api-abc123.apigateway.mestrealvaro.cloud.goog",
        create_time="2024-06-01T10:00:00Z",
    )


@pytest.fixture
def sample_config_response():
    return ApiConfigResponse(
        name="projects/mestrealvaro/locations/global/apis/my-api/configs/my-config",
        state="ACTIVE",
        service_rollout_state="ROLLED_OUT",
        create_time="2024-06-01T11:00:00Z",
    )


@pytest.fixture
def sample_gateway_response():
    return GatewayResponse(
        name="projects/mestrealvaro/locations/us-central1/gateways/my-gw",
        api_config="projects/mestrealvaro/locations/global/apis/my-api/configs/my-config",
        state="ACTIVE",
        default_hostname="my-gw-abc123.uc.gateway.dev",
        create_time="2024-06-01T12:00:00Z",
    )


@pytest.fixture
def sample_gateway_dashboard(sample_config_response):
    return GatewayDashboardResponse(
        api_exists=True,
        api_name="projects/mestrealvaro/locations/global/apis/my-api",
        managed_service="my-api-abc123.apigateway.mestrealvaro.cloud.goog",
        gateway_exists=True,
        gateway_url="https://my-gw-abc123.uc.gateway.dev",
        gateway_state="ACTIVE",
        active_config="projects/mestrealvaro/locations/global/apis/my-api/configs/my-config",
        configs=[sample_config_response],
    )


@pytest.fixture
def sample_proxy_status():
    return ProxyStatusResponse(
        deployed=True,
        service_name="vertex-ai-proxy",
        url="https://vertex-ai-proxy-abc123.run.app",
        region="us-central1",
        vertex_ai_region="us-central1",
        logs_url="https://console.cloud.google.com/logs/query",
    )


@pytest.fixture
def sample_proxy_files():
    return ProxyBuildFiles(
        main_py="# main.py",
        requirements_txt="flask>=3.0.0",
        dockerfile="FROM python:3.11-slim",
    )


@pytest.fixture
def sample_key_response():
    return KeyResponse(
        name="projects/mestrealvaro/locations/global/keys/test-key-123",
        uid="test-key-123",
        display_name="Test Key",
        key_string="AIzaSyTest123456",
        create_time=datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
        delete_time=None,
    )


@pytest.fixture
def sample_deleted_key_response():
    return KeyResponse(
        name="projects/mestrealvaro/locations/global/keys/deleted-key-456",
        uid="deleted-key-456",
        display_name="Deleted Key",
        key_string="",
        create_time=datetime(2024, 1, 10, 8, 0, 0, tzinfo=timezone.utc),
        delete_time=datetime(2024, 1, 12, 8, 0, 0, tzinfo=timezone.utc),
    )


# --- Mock Services ---


@pytest.fixture
def mock_gateway_service(
    sample_api_response,
    sample_config_response,
    sample_gateway_response,
    sample_gateway_dashboard,
):
    service = AsyncMock()
    service.create_api.return_value = sample_api_response
    service.get_api.return_value = sample_api_response
    service.delete_api.return_value = None
    service.list_apis.return_value = [sample_api_response]
    service.create_api_config.return_value = sample_config_response
    service.get_api_config.return_value = sample_config_response
    service.list_api_configs.return_value = [sample_config_response]
    service.delete_api_config.return_value = None
    service.create_gateway.return_value = sample_gateway_response
    service.get_gateway.return_value = sample_gateway_response
    service.update_gateway.return_value = sample_gateway_response
    service.delete_gateway.return_value = None
    service.get_dashboard.return_value = sample_gateway_dashboard
    return service


@pytest.fixture
def mock_proxy_service(sample_proxy_status, sample_proxy_files):
    service = AsyncMock()
    service.get_proxy_status.return_value = sample_proxy_status
    # generate_proxy_files is sync, so use MagicMock to avoid returning a coroutine
    service.generate_proxy_files = MagicMock(return_value=sample_proxy_files)
    service.deploy_proxy.return_value = sample_proxy_status
    service.delete_proxy.return_value = None
    return service


@pytest.fixture
def mock_api_keys_service(sample_key_response, sample_deleted_key_response):
    service = MagicMock()
    service.list_keys.return_value = [sample_key_response]
    service.get_key_string.return_value = "AIzaSyTest123456"
    service.create_key.return_value = sample_key_response
    service.delete_key.return_value = sample_deleted_key_response
    return service


# --- Test Client ---


@pytest.fixture
def test_client(mock_gateway_service, mock_proxy_service, mock_api_keys_service):
    from app.main import app

    app.state.gateway_service = mock_gateway_service
    app.state.proxy_service = mock_proxy_service
    app.state.api_keys_service = mock_api_keys_service
    app.state.gateway_managed_service = (
        "my-api-abc123.apigateway.mestrealvaro.cloud.goog"
    )
    client = TestClient(app, raise_server_exceptions=False)
    yield client
