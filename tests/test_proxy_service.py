from unittest.mock import AsyncMock, patch

import pytest

from app.schemas.proxy import ProxyDeployRequest
from app.services.gcloud_runner import GcloudError
from app.services.proxy_service import (
    PROXY_DOCKERFILE,
    PROXY_MAIN_PY,
    PROXY_REQUIREMENTS_TXT,
    ProxyService,
)


@pytest.fixture
def proxy_service():
    return ProxyService("mestrealvaro", "us-central1")


@pytest.fixture
def deploy_request():
    return ProxyDeployRequest(
        vertex_ai_region="us-central1",
        service_name="vertex-ai-proxy",
        service_account_email="sa@proj.iam.gserviceaccount.com",
    )


@pytest.fixture
def mock_run_gcloud():
    with patch("app.services.proxy_service.run_gcloud", new_callable=AsyncMock) as m:
        yield m


class TestGenerateProxyFiles:
    def test_returns_all_files(self, proxy_service, deploy_request):
        files = proxy_service.generate_proxy_files(deploy_request)

        assert "flask" in files.requirements_txt
        assert "python" in files.dockerfile

    def test_proxy_is_transparent(self, proxy_service, deploy_request):
        files = proxy_service.generate_proxy_files(deploy_request)

        # The proxy should have a catch-all route, not endpoint-specific routes
        assert "/<path:path>" in files.main_py
        assert "/health" in files.main_py
        # Should NOT have hardcoded /predict route
        assert '@app.route("/predict"' not in files.main_py

    def test_proxy_adds_auth(self, proxy_service, deploy_request):
        files = proxy_service.generate_proxy_files(deploy_request)

        assert "_get_access_token" in files.main_py
        assert "Bearer" in files.main_py


class TestDeployProxy:
    async def test_deploys_and_returns_status(self, proxy_service, deploy_request, mock_run_gcloud):
        mock_run_gcloud.side_effect = [
            None,  # deploy
            {  # describe
                "status": {"url": "https://vertex-ai-proxy-abc.run.app"},
                "spec": {
                    "template": {
                        "spec": {
                            "containers": [
                                {
                                    "env": [
                                        {"name": "VERTEX_AI_REGION", "value": "us-central1"},
                                    ]
                                }
                            ]
                        }
                    }
                },
            },
        ]

        result = await proxy_service.deploy_proxy(deploy_request)

        assert result.deployed is True
        assert result.url == "https://vertex-ai-proxy-abc.run.app"

        deploy_args = mock_run_gcloud.call_args_list[0][0][0]
        assert "run" in deploy_args
        assert "deploy" in deploy_args
        assert any("--service-account=" in arg for arg in deploy_args)

    async def test_deploy_without_sa(self, proxy_service, mock_run_gcloud):
        req = ProxyDeployRequest(
            vertex_ai_region="us-central1",
            service_name="my-proxy",
        )
        mock_run_gcloud.side_effect = [
            None,
            {"status": {"url": "https://my-proxy.run.app"}, "spec": {"template": {"spec": {"containers": [{}]}}}},
        ]

        await proxy_service.deploy_proxy(req)

        deploy_args = mock_run_gcloud.call_args_list[0][0][0]
        assert not any("--service-account=" in arg for arg in deploy_args)

    async def test_env_vars_no_endpoint_id(self, proxy_service, deploy_request, mock_run_gcloud):
        mock_run_gcloud.side_effect = [None, {"status": {}, "spec": {"template": {"spec": {"containers": [{}]}}}}]

        await proxy_service.deploy_proxy(deploy_request)

        deploy_args = mock_run_gcloud.call_args_list[0][0][0]
        env_arg = [a for a in deploy_args if "--set-env-vars" in a][0]
        assert "GCP_PROJECT_ID=" in env_arg
        assert "VERTEX_AI_REGION=" in env_arg
        # Transparent proxy doesn't need endpoint ID
        assert "VERTEX_AI_ENDPOINT_ID" not in env_arg


class TestGetProxyStatus:
    async def test_deployed_service(self, proxy_service, mock_run_gcloud):
        mock_run_gcloud.return_value = {
            "status": {"url": "https://proxy.run.app"},
            "spec": {
                "template": {
                    "spec": {
                        "containers": [
                            {
                                "env": [
                                    {"name": "VERTEX_AI_REGION", "value": "us-east1"},
                                ]
                            }
                        ]
                    }
                }
            },
        }

        result = await proxy_service.get_proxy_status("proxy", "us-central1")

        assert result.deployed is True
        assert result.url == "https://proxy.run.app"
        assert "logs" in result.logs_url

    async def test_not_deployed(self, proxy_service, mock_run_gcloud):
        mock_run_gcloud.side_effect = GcloudError("not found")

        result = await proxy_service.get_proxy_status("missing", "us-central1")

        assert result.deployed is False
        assert result.service_name == "missing"


class TestDeleteProxy:
    async def test_calls_delete(self, proxy_service, mock_run_gcloud):
        mock_run_gcloud.return_value = None

        await proxy_service.delete_proxy("my-proxy", "us-central1")

        args = mock_run_gcloud.call_args[0][0]
        assert "delete" in args
        assert "my-proxy" in args


class TestProxyTemplates:
    def test_main_py_has_catch_all_route(self):
        assert "/<path:path>" in PROXY_MAIN_PY

    def test_main_py_has_health_route(self):
        assert "/health" in PROXY_MAIN_PY

    def test_main_py_streams_response(self):
        assert "stream=True" in PROXY_MAIN_PY

    def test_requirements_has_flask(self):
        assert "flask" in PROXY_REQUIREMENTS_TXT

    def test_dockerfile_has_gunicorn(self):
        assert "gunicorn" in PROXY_DOCKERFILE
