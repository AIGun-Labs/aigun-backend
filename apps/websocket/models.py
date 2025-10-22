from typing import Any
from pydantic import BaseModel, Field, field_serializer, field_validator
import settings



class WebSocketMessage(BaseModel):
    message: dict[str, Any]

    @classmethod
    def generate_broadcast(cls, event: str = 'feed', tag: str = 'all', message: dict[str, Any] = {}) -> 'WebSocketMessage':
        return cls(event=event, env=settings.ENV, tag=tag, message=message)

class WebSocketMessageBase(BaseModel):
    type: str

class WebSocketRequest(WebSocketMessageBase):
    data: dict[str, Any] | None = {}