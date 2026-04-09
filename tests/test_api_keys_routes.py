import pytest


class TestListKeys:
    def test_returns_keys(self, test_client):
        resp = test_client.get("/api/keys")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_count"] == 1
        assert len(data["keys"]) == 1
        assert data["keys"][0]["uid"] == "test-key-123"


class TestCreateKey:
    def test_returns_201(self, test_client):
        resp = test_client.post(
            "/api/keys",
            json={"display_name": "My Key", "restrict_to_gateway": True},
        )
        assert resp.status_code == 201
        assert resp.json()["uid"] == "test-key-123"

    def test_default_body(self, test_client):
        resp = test_client.post("/api/keys", json={})
        assert resp.status_code == 201


class TestGetKeyString:
    def test_returns_key_string(self, test_client):
        resp = test_client.get("/api/keys/test-key-123/key-string")
        assert resp.status_code == 200
        assert resp.json()["key_string"] == "AIzaSyTest123456"


class TestDeleteKey:
    def test_returns_deleted_key(self, test_client):
        resp = test_client.delete("/api/keys/test-key-123")
        assert resp.status_code == 200
        assert resp.json()["uid"] == "deleted-key-456"
        assert resp.json()["delete_time"] is not None
