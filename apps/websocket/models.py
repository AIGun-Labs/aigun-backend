import settings
from typing import Any
from pydantic import BaseModel
from sqlalchemy import Column, String, Enum, Text
from sqlalchemy.orm import relationship
from data.db import Base
from sqlalchemy.dialects.postgresql import UUID, JSONB





class WebSocketMessage(BaseModel):
    message: dict[str, Any]

    @classmethod
    def generate_broadcast(cls, event: str = 'feed', tag: str = 'all', message: dict[str, Any] = {}) -> 'WebSocketMessage':
        return cls(event=event, env=settings.ENV, tag=tag, message=message)

class WebSocketMessageBase(BaseModel):
    type: str

class WebSocketRequest(WebSocketMessageBase):
    data: dict[str, Any] | None = {}


# Subscription set enumeration type
class SubSetType(str, Enum):
    AI_AGENT = "ai_agent"
    SOCIAL_NETWORK = "social_network"


# Subscription set
class SubSet (Base):
    __tablename__ = 'subset'

    # uuid = Column(String(36), primary_key=True, nullable=False, default=lambda: str(uuid.uuid4()), comment='Subscription set unique identifier')

    name = Column(String, nullable=False, comment='Tag set name')
    description = Column(Text, nullable=True, comment='Tag set description')
    tags = Column(JSONB, default=list, comment='Tags that the entire subscription set must contain')
    type = Column(String, nullable=False, comment='Subscription set type, ai_agent/social_network')

    user_subset = relationship("UserSubSetModel", back_populates="subset", lazy="select", primaryjoin="UserSubSetModel.subset_id == SubSet.id", foreign_keys="[UserSubSetModel.subset_id]")


class UserSubSetModel (Base):
    __tablename__ = 'user_subset'

    user_id = Column(UUID(as_uuid=True),  nullable=False, comment='User ID')
    subset_id = Column(UUID(as_uuid=True), nullable=False, comment='Subscription set ID')

    user = relationship("UserModel", back_populates="user_subset", lazy="select", primaryjoin="UserSubSetModel.user_id == UserModel.id", foreign_keys="[UserSubSetModel.user_id]")
    subset = relationship("SubSet", back_populates="user_subset", lazy="select", primaryjoin="UserSubSetModel.subset_id == SubSet.id", foreign_keys="[UserSubSetModel.subset_id]")