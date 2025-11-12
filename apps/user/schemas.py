from typing import Optional

from pydantic import BaseModel
from uuid import UUID


class TagOutSchema(BaseModel):
    id: UUID
    slug: str
    is_visible: Optional[bool] = None

    class Config:
        from_attributes = True

class AiAgentOutSchema(BaseModel):
    id: UUID
    name: dict
    description: dict
    avatar: str
    rank: int
    subset_id: UUID
    tag: Optional[TagOutSchema] = None

    class Config:
        from_attributes = True