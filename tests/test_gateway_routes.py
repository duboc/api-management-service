import pytest


class TestCreateApi:
    def test_returns_201(self, test_client):
        resp = test_client.post("/api/gateway/apis?api_id=my-api")
        assert resp.status_code == 201
        assert resp.json()["name"] == "projects/mestrealvaro/locations/global/apis/my-api"


class TestListApis:
    def test_returns_list(self, test_client):
        resp = test_client.get("/api/gateway/apis")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 1


class TestGetApi:
    def test_returns_api(self, test_client):
        resp = test_client.get("/api/gateway/apis/my-api")
        assert resp.status_code == 200
        assert resp.json()["state"] == "ACTIVE"


class TestDeleteApi:
    def test_returns_204(self, test_client):
        resp = test_client.delete("/api/gateway/apis/my-api")
        assert resp.status_code == 204


class TestCreateApiConfig:
    def test_returns_201(self, test_client):
        resp = test_client.post(
            "/api/gateway/apis/my-api/configs",
            json={
                "config_id": "cfg-1",
                "backend_url": "https://proxy.run.app",
                "service_account_email": "sa@proj.iam.gserviceaccount.com",
            },
        )
        assert resp.status_code == 201
        assert "ACTIVE" in resp.json()["state"]

    def test_validates_body(self, test_client):
        resp = test_client.post(
            "/api/gateway/apis/my-api/configs",
            json={},
        )
        assert resp.status_code == 422


class TestListApiConfigs:
    def test_returns_list(self, test_client):
        resp = test_client.get("/api/gateway/apis/my-api/configs")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


class TestDeleteApiConfig:
    def test_returns_204(self, test_client):
        resp = test_client.delete("/api/gateway/apis/my-api/configs/cfg-1")
        assert resp.status_code == 204


class TestCreateGateway:
    def test_returns_201(self, test_client):
        resp = test_client.post(
            "/api/gateway/gateways",
            json={
                "gateway_id": "gw-1",
                "api_config_id": "cfg-1",
                "location": "us-central1",
            },
        )
        assert resp.status_code == 201
        assert resp.json()["state"] == "ACTIVE"

    def test_validates_body(self, test_client):
        resp = test_client.post(
            "/api/gateway/gateways",
            json={},
        )
        assert resp.status_code == 422


class TestGetGateway:
    def test_returns_gateway(self, test_client):
        resp = test_client.get("/api/gateway/gateways/gw-1?location=us-central1")
        assert resp.status_code == 200
        assert resp.json()["default_hostname"] == "my-gw-abc123.uc.gateway.dev"

    def test_default_location(self, test_client):
        resp = test_client.get("/api/gateway/gateways/gw-1")
        assert resp.status_code == 200


class TestUpdateGateway:
    def test_returns_updated(self, test_client):
        resp = test_client.patch(
            "/api/gateway/gateways/gw-1?location=us-central1",
            json={"api_config_id": "cfg-2"},
        )
        assert resp.status_code == 200


class TestDeleteGateway:
    def test_returns_204(self, test_client):
        resp = test_client.delete("/api/gateway/gateways/gw-1?location=us-central1")
        assert resp.status_code == 204


class TestGatewayDashboard:
    def test_returns_dashboard(self, test_client):
        resp = test_client.get("/api/gateway/dashboard")
        assert resp.status_code == 200
        data = resp.json()
        assert data["api_exists"] is True
        assert data["gateway_exists"] is True
        assert "gateway.dev" in data["gateway_url"]
