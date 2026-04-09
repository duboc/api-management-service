from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class KeyCreateRequest(BaseModel):
    display_name: str = ""


class KeyResponse(BaseModel):
    name: str
    uid: str
    display_name: str
    key_string: str = ""
    create_time: Optional[datetime] = None
    delete_time: Optional[datetime] = None


class KeyListResponse(BaseModel):
    keys: list[KeyResponse]
    total_count: int
