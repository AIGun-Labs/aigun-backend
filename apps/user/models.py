"""
Store model of  user module
"""

from data.db import Base
from sqlalchemy.orm import  relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy import Column, String, Text,  Integer, BigInteger, Numeric



class AiAgentModel(Base):
    __tablename__ = "ai_agent"

    name = Column(JSONB, nullable=False, comment='AI Agent Name')
    description = Column(JSONB, nullable=True, comment='AI Agent Description')
    avatar = Column(Text, nullable=True, comment='AI Agent Avatar')
    rank = Column(Integer, nullable=False, comment='AI Agent Rank, smaller value means higher rank')
    subset_id = Column(UUID(as_uuid=True), nullable=True, comment='Associated Subscription Set ID')
    tag_id = Column(UUID(as_uuid=True), nullable=True, comment='Associated Tag ID')

    subset = relationship("SubSet", lazy="select", primaryjoin="AiAgentModel.subset_id == SubSet.id", foreign_keys=[subset_id])
    tag = relationship("TagModel", lazy="select", primaryjoin="AiAgentModel.tag_id == TagModel.id", foreign_keys=[tag_id])
