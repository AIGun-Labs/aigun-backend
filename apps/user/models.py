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


class UserModel(Base):
    __tablename__ = "user"

    tid = Column(BigInteger, unique=True)
    email = Column(String)
    nickname = Column(String)
    avatar = Column(String)
    invite_code = Column(String)
    superior_id = Column(String, nullable=True)
    ancestor_id = Column(String, nullable=True)
    invite_amount = Column(Integer, default=0)
    indirect_invite_amount = Column(Integer, default=0)
    expand_invite_list = Column(String, default='0|0|0')
    power = Column(BigInteger, default=0, nullable=False, comment='Current computing power')
    claimed_amount = Column(BigInteger, default=0, nullable=True, comment='Total claimed gold')
    destroyed_amount = Column(BigInteger, default=0, nullable=True, comment='Total destroyed gold')
    reward_claimed_amount = Column(BigInteger, default=0, nullable=True, comment='Total claimed reward gold')
    reward_destroyed_amount = Column(BigInteger, default=0, nullable=True, comment='Total destroyed reward gold')
    reward_unclaimed_amount = Column(BigInteger, default=0, nullable=True, comment='Unclaimed reward gold')
    is_active = Column(Integer, default=1)
    is_obsolete = Column(Integer, default=0)
    role_id = Column(Integer, default=1)
    device_id = Column(String, default="")
    wallet_user_id = Column(String)
    organization_id = Column(String)
    total_trading_volume = Column(String, default="0", nullable=False,
                                  comment='Total trading volume')  # Total trading volume
    aigun_claimed_amount = Column(String, default="0", nullable=False,
                                  comment='AI Gun total claimed gold')  # AI Gun total claimed gold
    unclaimed_invite_gold = Column(String, default="0", nullable=False,
                                   comment='Unclaimed invite reward gold')  # Unclaimed invite reward gold
    unclaimed_trade_gold = Column(String, default="0", nullable=False,
                                  comment='Unclaimed trade reward gold')  # Unclaimed trade reward gold
    claimed_dollar = Column(Numeric(38, 18), default="0", nullable=False,
                            comment='Total claimed USD')  # Total claimed USD

    # Subscription set
    user_subset = relationship("UserSubSetModel", back_populates="user", lazy="select",
                               primaryjoin="UserModel.id == UserSubSetModel.user_id",
                               foreign_keys="[UserSubSetModel.user_id]")