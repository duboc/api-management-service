from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from google.cloud.api_keys_v2 import types

from app.schemas.api_keys import KeyCreateRequest
from app.services.api_keys_service import ApiKeysService


def _make_proto_key(
    name="projects/mestrealvaro/locations/global/keys/key-1",
    uid="key-1",
    display_name="Test Key",
    create_time=None,
    delete_time=None,
):
    key = MagicMock(spec=types.Key)
    key.name = name
    key.uid = uid
    key.display_name = display_name
    key.create_time = create_time or datetime(2024, 1, 15, tzinfo=timezone.utc)
    key.delete_time = delete_time
    return key


@pytest.fixture
def service():
    with patch("app.services.api_keys_service.api_keys_v2.ApiKeysClient") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        svc = ApiKeysService("mestrealvaro")
        svc._mock_client = mock_client
        yield svc


class TestListKeys:
    def test_returns_mapped_responses(self, service):
        key1 = _make_proto_key(uid="key-1", display_name="Key One")
        key2 = _make_proto_key(uid="key-2", display_name="Key Two")
        service._mock_client.list_keys.return_value = [key1, key2]

        result = service.list_keys()

        assert len(result) == 2
        assert result[0].uid == "key-1"
        assert result[1].uid == "key-2"

    def test_uses_correct_parent(self, service):
        service._mock_client.list_keys.return_value = []
        service.list_keys()

        call_args = service._mock_client.list_keys.call_args
        assert call_args.kwargs["parent"] == "projects/mestrealvaro/locations/global"


class TestGetKeyString:
    def test_returns_string(self, service):
        response = MagicMock()
        response.key_string = "AIzaSyTestKey123"
        service._mock_client.get_key_string.return_value = response

        result = service.get_key_string("key-1")
        assert result == "AIzaSyTestKey123"

    def test_builds_correct_name(self, service):
        response = MagicMock()
        response.key_string = "test"
        service._mock_client.get_key_string.return_value = response

        service.get_key_string("my-key-id")

        call_args = service._mock_client.get_key_string.call_args
        assert "my-key-id" in call_args.kwargs["name"]


class TestCreateKey:
    def test_creates_with_gateway_restriction(self, service):
        created_key = _make_proto_key(display_name="New Key")
        operation = MagicMock()
        operation.result.return_value = created_key
        service._mock_client.create_key.return_value = operation

        key_string_resp = MagicMock()
        key_string_resp.key_string = "AIzaSyNewKey"
        service._mock_client.get_key_string.return_value = key_string_resp

        request = KeyCreateRequest(display_name="New Key")
        result = service.create_key(request, managed_service="my-svc.apigateway.cloud.goog")

        assert result.display_name == "New Key"
        assert result.key_string == "AIzaSyNewKey"

        create_call = service._mock_client.create_key.call_args
        key_arg = create_call.kwargs["key"]
        assert key_arg.restrictions is not None
        assert len(key_arg.restrictions.api_targets) > 0

    def test_rejects_without_managed_service(self, service):
        request = KeyCreateRequest(display_name="Bad Key")

        with pytest.raises(ValueError, match="no gateway managed service"):
            service.create_key(request, managed_service="")


class TestDeleteKey:
    def test_deletes_key(self, service):
        deleted_key = _make_proto_key(
            delete_time=datetime(2024, 2, 1, tzinfo=timezone.utc)
        )
        operation = MagicMock()
        operation.result.return_value = deleted_key
        service._mock_client.delete_key.return_value = operation

        result = service.delete_key("key-1")

        assert result.delete_time is not None

    def test_builds_correct_name(self, service):
        deleted_key = _make_proto_key()
        operation = MagicMock()
        operation.result.return_value = deleted_key
        service._mock_client.delete_key.return_value = operation

        service.delete_key("my-key-id")

        call_args = service._mock_client.delete_key.call_args
        assert "my-key-id" in call_args.kwargs["name"]


class TestErrorHandling:
    def test_not_found_propagates(self, service):
        from google.api_core.exceptions import NotFound

        service._mock_client.get_key_string.side_effect = NotFound("not found")

        with pytest.raises(NotFound):
            service.get_key_string("nonexistent")
