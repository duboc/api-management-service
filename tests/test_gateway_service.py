from unittest.mock import AsyncMock, patch

import pytest
import yaml

from app.schemas.gateway import ApiConfigCreateRequest, GatewayCreateRequest
from app.services.gateway_service import GatewayService, SUPPORTED_GATEWAY_REGIONS


@pytest.fixture
def gateway_service():
    return GatewayService("mestrealvaro")


@pytest.fixture
def mock_run_gcloud():
    with patch("app.services.gateway_service.run_gcloud", new_callable=AsyncMock) as m:
        yield m


class TestCreateApi:
    async def test_creates_and_returns_api(self, gateway_service, mock_run_gcloud):
        mock_run_gcloud.side_effect = [
            None,  # create call (parse_json=False)
            {  # describe call
                "name": "projects/mestrealvaro/locations/global/apis/my-api",
                "displayName": "my-api",
                "state": "ACTIVE",
                "managedService": "my-api-svc.apigateway.mestrealvaro.cloud.goog",
                "createTime": "2024-01-01T00:00:00Z",
            },
        ]

        result = await gateway_service.create_api("my-api")

        assert result.name == "projects/mestrealvaro/locations/global/apis/my-api"
        assert result.state == "ACTIVE"
        assert mock_run_gcloud.call_count == 2


class TestGetApi:
    async def test_returns_api_response(self, gateway_service, mock_run_gcloud):
        mock_run_gcloud.return_value = {
            "name": "projects/mestrealvaro/locations/global/apis/test",
            "state": "ACTIVE",
            "managedService": "svc",
        }

        result = await gateway_service.get_api("test")

        assert result.state == "ACTIVE"
        assert result.managed_service == "svc"


class TestListApis:
    async def test_returns_list(self, gateway_service, mock_run_gcloud):
        mock_run_gcloud.return_value = [
            {"name": "api-1", "state": "ACTIVE"},
            {"name": "api-2", "state": "ACTIVE"},
        ]

        result = await gateway_service.list_apis()
        assert len(result) == 2

    async def test_returns_empty_when_none(self, gateway_service, mock_run_gcloud):
        mock_run_gcloud.return_value = None
        result = await gateway_service.list_apis()
        assert result == []


class TestDeleteApi:
    async def test_calls_delete(self, gateway_service, mock_run_gcloud):
        mock_run_gcloud.return_value = None
        await gateway_service.delete_api("my-api")
        mock_run_gcloud.assert_called_once()
        assert "delete" in mock_run_gcloud.call_args[0][0]


class TestGenerateOpenapiSpec:
    def test_spec_structure(self, gateway_service):
        spec_yaml = gateway_service._generate_openapi_spec("https://proxy.run.app")
        spec = yaml.safe_load(spec_yaml)

        assert spec["swagger"] == "2.0"
        assert "api_key" in spec["securityDefinitions"]

    def test_has_generative_ai_paths(self, gateway_service):
        spec_yaml = gateway_service._generate_openapi_spec("https://proxy.run.app")
        spec = yaml.safe_load(spec_yaml)

        assert "/publishers/google/models/{model}:generateContent" in spec["paths"]
        assert "/publishers/google/models/{model}:streamGenerateContent" in spec["paths"]
        assert "/publishers/google/models/{model}:countTokens" in spec["paths"]

    def test_has_custom_endpoint_paths(self, gateway_service):
        spec_yaml = gateway_service._generate_openapi_spec("https://proxy.run.app")
        spec = yaml.safe_load(spec_yaml)

        assert "/endpoints/{endpoint}:predict" in spec["paths"]
        assert "/endpoints/{endpoint}:generateContent" in spec["paths"]

    def test_uses_append_path_translation(self, gateway_service):
        spec_yaml = gateway_service._generate_openapi_spec("https://proxy.run.app")
        spec = yaml.safe_load(spec_yaml)

        backend = spec["paths"]["/publishers/google/models/{model}:generateContent"]["post"]["x-google-backend"]
        assert backend["address"] == "https://proxy.run.app"
        assert backend["path_translation"] == "APPEND_PATH_TO_ADDRESS"

    def test_health_has_no_auth(self, gateway_service):
        spec_yaml = gateway_service._generate_openapi_spec("https://proxy.run.app")
        spec = yaml.safe_load(spec_yaml)

        assert spec["paths"]["/health"]["get"]["security"] == []


class TestCreateApiConfig:
    async def test_creates_config_with_temp_file(self, gateway_service, mock_run_gcloud):
        mock_run_gcloud.side_effect = [
            None,  # create call
            {  # describe call
                "name": "projects/mestrealvaro/locations/global/apis/my-api/configs/cfg-1",
                "state": "ACTIVE",
                "createTime": "2024-01-01T00:00:00Z",
            },
        ]

        req = ApiConfigCreateRequest(
            config_id="cfg-1",
            backend_url="https://proxy.run.app",
            service_account_email="sa@proj.iam.gserviceaccount.com",
        )

        result = await gateway_service.create_api_config("my-api", req)

        assert result.state == "ACTIVE"
        create_args = mock_run_gcloud.call_args_list[0][0][0]
        assert "api-configs" in create_args
        assert "create" in create_args


class TestListApiConfigs:
    async def test_returns_configs(self, gateway_service, mock_run_gcloud):
        mock_run_gcloud.return_value = [
            {"name": "cfg-1", "state": "ACTIVE"},
        ]
        result = await gateway_service.list_api_configs("my-api")
        assert len(result) == 1

    async def test_returns_empty_when_none(self, gateway_service, mock_run_gcloud):
        mock_run_gcloud.return_value = None
        result = await gateway_service.list_api_configs("my-api")
        assert result == []


class TestCreateGateway:
    async def test_creates_gateway(self, gateway_service, mock_run_gcloud):
        mock_run_gcloud.side_effect = [
            None,  # create
            {  # describe
                "name": "projects/mestrealvaro/locations/us-central1/gateways/gw-1",
                "apiConfig": "cfg-1",
                "state": "ACTIVE",
                "defaultHostname": "gw-1-abc.uc.gateway.dev",
            },
        ]

        req = GatewayCreateRequest(
            gateway_id="gw-1",
            api_config_id="cfg-1",
            location="us-central1",
        )

        result = await gateway_service.create_gateway("my-api", req)
        assert result.state == "ACTIVE"
        assert result.default_hostname == "gw-1-abc.uc.gateway.dev"

    async def test_rejects_unsupported_region(self, gateway_service, mock_run_gcloud):
        req = GatewayCreateRequest(
            gateway_id="gw-1",
            api_config_id="cfg-1",
            location="antarctica-south1",
        )

        with pytest.raises(ValueError, match="Unsupported region"):
            await gateway_service.create_gateway("my-api", req)


class TestGetGateway:
    async def test_returns_gateway(self, gateway_service, mock_run_gcloud):
        mock_run_gcloud.return_value = {
            "name": "gw-1",
            "apiConfig": "cfg-1",
            "state": "ACTIVE",
            "defaultHostname": "gw.dev",
        }
        result = await gateway_service.get_gateway("gw-1", "us-central1")
        assert result.default_hostname == "gw.dev"


class TestUpdateGateway:
    async def test_updates_config(self, gateway_service, mock_run_gcloud):
        mock_run_gcloud.side_effect = [
            None,  # update
            {"name": "gw-1", "apiConfig": "cfg-2", "state": "ACTIVE", "defaultHostname": "gw.dev"},
        ]

        result = await gateway_service.update_gateway("gw-1", "my-api", "cfg-2", "us-central1")
        assert result.api_config == "cfg-2"


class TestDeleteGateway:
    async def test_calls_delete(self, gateway_service, mock_run_gcloud):
        mock_run_gcloud.return_value = None
        await gateway_service.delete_gateway("gw-1", "us-central1")
        assert "delete" in mock_run_gcloud.call_args[0][0]


class TestGetDashboard:
    async def test_full_dashboard(self, gateway_service, mock_run_gcloud):
        mock_run_gcloud.side_effect = [
            # get_api
            {"name": "my-api", "state": "ACTIVE", "managedService": "svc"},
            # get_gateway
            {"name": "gw-1", "state": "ACTIVE", "defaultHostname": "gw.dev", "apiConfig": "cfg-1"},
            # list_api_configs
            [{"name": "cfg-1", "state": "ACTIVE"}],
        ]

        result = await gateway_service.get_dashboard("my-api", "gw-1", "us-central1")

        assert result.api_exists is True
        assert result.gateway_exists is True
        assert result.gateway_url == "https://gw.dev"
        assert len(result.configs) == 1

    async def test_dashboard_no_api(self, gateway_service, mock_run_gcloud):
        mock_run_gcloud.side_effect = Exception("not found")

        result = await gateway_service.get_dashboard("missing", "gw", "us-central1")

        assert result.api_exists is False
        assert result.gateway_exists is False


class TestSupportedRegions:
    def test_has_us_central1(self):
        assert "us-central1" in SUPPORTED_GATEWAY_REGIONS

    def test_has_expected_count(self):
        assert len(SUPPORTED_GATEWAY_REGIONS) == 10
