import logging

from google.cloud import api_keys_v2
from google.cloud.api_keys_v2 import types

from app.schemas.api_keys import KeyCreateRequest, KeyResponse

logger = logging.getLogger(__name__)


class ApiKeysService:
    def __init__(self, project_id: str) -> None:
        self._client = api_keys_v2.ApiKeysClient()
        self._project_id = project_id
        self._parent = f"projects/{project_id}/locations/global"

    def _build_key_name(self, key_id: str) -> str:
        return f"{self._parent}/keys/{key_id}"

    def _key_to_response(
        self, key: types.Key, key_string: str = ""
    ) -> KeyResponse:
        return KeyResponse(
            name=key.name,
            uid=key.uid,
            display_name=key.display_name,
            key_string=key_string,
            create_time=key.create_time,
            delete_time=key.delete_time,
        )

    def list_keys(self) -> list[KeyResponse]:
        logger.info("Listing keys for project %s", self._project_id)
        pager = self._client.list_keys(parent=self._parent)
        return [self._key_to_response(key) for key in pager]

    def get_key_string(self, key_id: str) -> str:
        logger.info("Getting key string for %s", key_id)
        name = self._build_key_name(key_id)
        response = self._client.get_key_string(name=name)
        return response.key_string

    def create_key(
        self, request: KeyCreateRequest, managed_service: str = ""
    ) -> KeyResponse:
        logger.info(
            "Creating key with display_name=%s", request.display_name
        )
        key = types.Key(display_name=request.display_name)

        if request.restrict_to_gateway and managed_service:
            key.restrictions = types.Restrictions(
                api_targets=[
                    types.ApiTarget(service=managed_service)
                ]
            )
            logger.info(
                "Restricting key to managed service: %s", managed_service
            )

        operation = self._client.create_key(parent=self._parent, key=key)
        created_key = operation.result()

        key_string = self._client.get_key_string(
            name=created_key.name
        ).key_string

        logger.info("Key created: %s", created_key.name)
        return self._key_to_response(created_key, key_string)

    def delete_key(self, key_id: str) -> KeyResponse:
        logger.info("Deleting key %s", key_id)
        name = self._build_key_name(key_id)
        operation = self._client.delete_key(name=name)
        deleted_key = operation.result()
        logger.info("Key deleted: %s", name)
        return self._key_to_response(deleted_key)
