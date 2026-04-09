import pytest


class TestOverallDashboard:
    def test_returns_dashboard(self, test_client):
        resp = test_client.get("/api/dashboard")
        assert resp.status_code == 200
        data = resp.json()
        assert data["gcp_project_id"] == "mestrealvaro"
        assert "console.cloud.google.com" in data["gateway_console_url"]
        assert "console.cloud.google.com" in data["cloud_run_console_url"]
        assert "console.cloud.google.com" in data["vertex_ai_console_url"]

    def test_includes_key_count(self, test_client):
        resp = test_client.get("/api/dashboard")
        data = resp.json()
        assert data["api_key_count"] == 1


class TestStaticFiles:
    def test_index_page_serves(self, test_client):
        resp = test_client.get("/")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]
