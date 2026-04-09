import pytest


class TestGetProxyStatus:
    def test_returns_status(self, test_client):
        resp = test_client.get("/api/proxy/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["deployed"] is True
        assert "run.app" in data["url"]

    def test_with_params(self, test_client):
        resp = test_client.get(
            "/api/proxy/status?service_name=my-proxy&region=us-east1"
        )
        assert resp.status_code == 200


class TestPreviewProxy:
    def test_returns_files(self, test_client):
        resp = test_client.post(
            "/api/proxy/preview",
            json={
                "vertex_ai_region": "us-central1",
                "service_name": "my-proxy",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "main_py" in data
        assert "requirements_txt" in data
        assert "dockerfile" in data


class TestDeployProxy:
    def test_returns_201(self, test_client):
        resp = test_client.post(
            "/api/proxy/deploy",
            json={
                "vertex_ai_region": "us-central1",
                "service_name": "my-proxy",
            },
        )
        assert resp.status_code == 201
        assert resp.json()["deployed"] is True


class TestDeleteProxy:
    def test_returns_204(self, test_client):
        resp = test_client.delete(
            "/api/proxy?service_name=my-proxy&region=us-central1"
        )
        assert resp.status_code == 204
