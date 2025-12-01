from sqlalchemy import Column, String, Boolean, Float, Double, TIMESTAMP, BigInteger, Text, Integer

from sqlalchemy.sql import func
from sqlalchemy import DateTime, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy import text

import settings
from data.db import Base


class IntelligenceModel(Base):
    """
    Intelligence Table
    """
    __tablename__ = "intelligence"

    published_at = Column(DateTime(timezone=True), nullable=False,
                          comment="Original intelligence publish timestamp (UTC0 during storage)")
    created_at = Column(DateTime(timezone=True), server_default=text('CURRENT_TIMESTAMP(3)'),
                        comment="Creation time")
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), comment="Update time")
    is_deleted = Column(Boolean, nullable=False, default=False, comment="Whether deleted")
    is_visible = Column(Boolean, nullable=False, default=True, comment="Whether to display")
    is_valuable = Column(Boolean, nullable=True, comment="Whether has judgment value")
    source_id = Column(UUID(as_uuid=True), nullable=True, comment="Corresponding original data ID")
    source_url = Column(Text, nullable=True, comment="Source link (e.g. original tweet)")
    type = Column(Text, nullable=True, comment="Common types: twitter/telegram/news")
    subtype = Column(Text, nullable=True, comment="Subtype")
    title = Column(Text, nullable=True, comment="Title")
    content = Column(Text, nullable=True, comment="Content")
    abstract = Column(Text, nullable=True, comment="Summary")
    extra_datas = Column(JSONB, nullable=True, comment="Additional data")
    medias = Column(JSONB, nullable=True, comment="Multimedia resources")
    analyzed = Column(JSONB, nullable=True, comment="AI analysis results")
    score = Column(Double, nullable=True, comment="AI value score (-1~1)")
    tags = Column(JSONB, nullable=True)
    analyzed_time = Column(BigInteger, default=0)
    showed_tokens = Column(JSONB, nullable=True)
    spider_time = Column(DateTime(timezone=True))
    push_time = Column(DateTime(timezone=True))
    adjusted_tokens = Column(JSONB)

    # Logical foreign key
    entity_intelligences = relationship("EntityIntelligenceModel", back_populates="intelligence", lazy="select",
                                        primaryjoin="IntelligenceModel.id == EntityIntelligenceModel.intelligence_id",
                                        foreign_keys="[EntityIntelligenceModel.intelligence_id]",
                                        )

    tag_intelligences = relationship(
        "TagIntelligenceModel",
        back_populates="intelligence",
        lazy="select",
        primaryjoin="IntelligenceModel.id == TagIntelligenceModel.intelligence_id",
        foreign_keys="[TagIntelligenceModel.intelligence_id]"
    )


class ChainModel(Base):
    __tablename__ = "chain"
    is_active = Column(Boolean, default=True)
    slug = Column(Text, unique=True)
    network_id = Column(Text, nullable=True)
    type = Column(Text, nullable=True)
    main_token = Column(Text, nullable=True)
    name = Column(Text)
    symbol = Column(Text)
    rpcs = Column(JSONB)
    logo = Column(Text, nullable=True)
    okx_chain_index = Column(Text)

    token_chain_datas = relationship("TokenChainDataModel", back_populates="chain", lazy="select",
                                     primaryjoin="ChainModel.id == TokenChainDataModel.chain_id",
                                     foreign_keys="[TokenChainDataModel.chain_id]")


class EntityIntelligenceModel(Base):
    """
    Entity Intelligence Association Table
    """
    __tablename__ = "entity_intelligence"
    id = Column(UUID(as_uuid=True), primary_key=True)
    entity_id = Column(UUID(as_uuid=True), nullable=False, comment="Entity ID")
    intelligence_id = Column(UUID(as_uuid=True), nullable=False, comment="Intelligence ID")
    type = Column(Text, nullable=True, comment="Type (e.g. author)")
    master_type = Column(Text, nullable=True, comment="Main type (e.g. author)")
    master_id = Column(UUID(as_uuid=True), nullable=True, comment="Main ID")
    highest_increase_rate = Column(Float, default=0)
    warning_price_usd = Column(Float, default=0)
    warning_market_cap = Column(Float, default=0)

    # Logical foreign key
    entity = relationship("EntityModel", back_populates="entity_intelligences", lazy="select",
                          primaryjoin="EntityIntelligenceModel.entity_id == EntityModel.id", foreign_keys=[entity_id])
    intelligence = relationship("IntelligenceModel", back_populates="entity_intelligences", lazy="select",
                                primaryjoin="EntityIntelligenceModel.intelligence_id == IntelligenceModel.id",
                                foreign_keys=[intelligence_id])


class EntityModel(Base):
    __tablename__ = "entity"

    name = Column(String(255), comment="Name")
    type = Column(String(100), comment="Entity type: exchange, fig token, agency")
    influence_level = Column(Text, comment="Influence level")
    influence_score = Column(Double, comment="Influence score")
    locations = Column(JSONB, comment="Location")
    description = Column(Text, comment="Description")
    source = Column(Text, comment="Source")
    avatar = Column(String(500), comment="Avatar (without domain)")
    extra_data = Column(JSONB, comment="Redundant field")
    is_deleted = Column(Boolean, nullable=False, default=False, comment="Whether deleted")
    is_test = Column(Boolean, nullable=False, comment="Whether test entity")
    is_visible = Column(Boolean, nullable=False, default=True, comment="Whether to display")
    subtype = Column(Text, comment="Subtype")

    # Influence level enum values
    INFLUENCE_LEVEL_VALUE = settings.INFLUENCE_LEVEL_VALUE

    entity_tags = relationship("EntityTagModel", back_populates="entity", lazy="select",
                               primaryjoin="EntityModel.id == EntityTagModel.entity_id",
                               foreign_keys="[EntityTagModel.entity_id]")

    entity_intelligences = relationship("EntityIntelligenceModel", back_populates="entity", lazy="select",
                                        primaryjoin="EntityModel.id == EntityIntelligenceModel.entity_id",
                                        foreign_keys="[EntityIntelligenceModel.entity_id]")

    entity_datasources = relationship("EntityDatasource", back_populates="entity", lazy="select",
                                      primaryjoin="EntityModel.id == EntityDatasource.entity_id",
                                      foreign_keys="[EntityDatasource.entity_id]")

    token_entity = relationship("TokenModel", back_populates="token_entity", lazy="select",
                                primaryjoin="EntityModel.id == TokenModel.entity_id",
                                foreign_keys="[TokenModel.entity_id]")

    tokendata_entity = relationship("TokenChainDataModel", back_populates="tokendata_entity", lazy="select",
                                    primaryjoin="EntityModel.id == TokenChainDataModel.entity_id",
                                    foreign_keys="[TokenChainDataModel.entity_id]")

    entity_NewsPlatform = relationship("NewsPlatformModel", back_populates="entity_NewsPlatformModel", lazy="select",
                                       primaryjoin="EntityModel.id == NewsPlatformModel.entity_id",
                                       foreign_keys="[NewsPlatformModel.entity_id]")

    exchange_platform = relationship("ExchangeModel", back_populates="entity_ExchangeModel", lazy="select",
                                     primaryjoin="EntityModel.id == ExchangeModel.entity_id",
                                     foreign_keys="[ExchangeModel.entity_id]")


class TokenChainDataModel(Base):
    __tablename__ = "token"

    is_visible = Column(Boolean, default=True)
    entity_id = Column(UUID(as_uuid=True), nullable=True)
    project_id = Column(UUID(as_uuid=True))
    chain_id = Column(UUID(as_uuid=True))
    contract_address = Column(Text)
    decimals = Column(Integer)
    name = Column(Text)
    symbol = Column(Text)
    logo = Column(Text)
    type = Column(Text)
    lifi_coin_key = Column(Text)
    volume_24h = Column(Float, default=0)
    market_cap = Column(Float, default=0)
    price_usd = Column(Float, default=0)
    is_verified = Column(Boolean, default=False)
    description = Column(Text)
    price_change_24h = Column(Float, default=0)
    standard = Column(Text)
    network = Column(Text)
    version = Column(Text)
    liquidity = Column(Float, default=0)
    display_time = Column(TIMESTAMP)
    is_native = Column(Boolean, default=False)
    is_internal = Column(Boolean, default=False)
    is_mainstream = Column(Boolean, default=False)
    is_follow = Column(Boolean, default=False)

    chain = relationship("ChainModel", back_populates="token_chain_datas", lazy="select",
                         primaryjoin="TokenChainDataModel.chain_id == ChainModel.id",
                         foreign_keys=[chain_id])

    tokendata_entity = relationship("EntityModel", back_populates="tokendata_entity", lazy="select",
                               primaryjoin="TokenChainDataModel.entity_id == EntityModel.id",
                               foreign_keys=[entity_id])

    chain_datas = relationship("TokenModel", back_populates="chain_datas", lazy="select",
                               primaryjoin="TokenChainDataModel.project_id == TokenModel.id",
                               foreign_keys=[project_id])

class EntityDatasource(Base):
    __tablename__ = "entity_datasource"

    entity_id = Column(UUID(as_uuid=True), comment="Entity ID")
    account_id = Column(UUID(as_uuid=True), comment="Account ID")
    account_type = Column(Text, comment="Type")
    is_visible = Column(Boolean, nullable=False, default=True, comment="Whether to display, not null, default true")
    account_slug = Column(Text, comment="Identifier")
    url = Column(Text, comment="Link address")
    extra_data = Column(JSONB, comment="Redundant field")

    # Logical foreign key
    entity = relationship("EntityModel", back_populates="entity_datasources", lazy="select",
                          primaryjoin="EntityDatasource.entity_id == EntityModel.id", foreign_keys=[entity_id])

    account = relationship("AccountModel", back_populates="entity_datasource", lazy="select",
                           primaryjoin="AccountModel.id == EntityDatasource.account_id", foreign_keys=[account_id])


class AccountModel(Base):
    __tablename__ = 'account'
    __mapper_args__ = {'exclude_properties': ['is_deleted']}

    twitter_id = Column(BigInteger, nullable=False)
    screen_name = Column(Text, nullable=False)
    name = Column(Text, nullable=False)
    avatar = Column(Text, nullable=False)
    banner = Column(Text)
    description = Column(Text)
    desc_urls = Column(JSONB)
    categories = Column(JSONB)
    display_urls = Column(JSONB)
    aff_highlight_labels = Column(JSONB)
    joined_at = Column(BigInteger, nullable=False)
    verified_status = Column(Text, nullable=False, server_default='unverified')
    follower_count = Column(BigInteger)
    following_count = Column(BigInteger)
    location = Column(Text)
    source = Column(JSONB)
    level = Column(Integer, nullable=False, server_default="0")
    group = Column(Integer, nullable=False, server_default="0")
    is_monitoring = Column(Boolean, nullable=False, server_default="false")
    tags = Column(JSONB)
    version = Column(Integer, nullable=False, server_default="1")
    entry_source = Column(Text)
    type = Column(Text)

    entity_datasource = relationship("EntityDatasource", back_populates="account", uselist=False, lazy="select",
                                     primaryjoin="AccountModel.id == EntityDatasource.account_id",
                                     foreign_keys="[EntityDatasource.account_id]")


class TokenModel(Base):
    __tablename__ = "project"

    entity_id = Column(UUID(as_uuid=True))
    name = Column(Text)
    symbol = Column(Text)
    description = Column(Text, nullable=True)
    logo = Column(Text, nullable=True)
    established_at = Column(TIMESTAMP, nullable=True)
    issued_at = Column(TIMESTAMP, nullable=True)
    lending_total = Column(Double, nullable=True)

    chain_datas = relationship("TokenChainDataModel", back_populates="chain_datas", lazy="select",
                               primaryjoin="TokenModel.id == TokenChainDataModel.project_id",
                               foreign_keys="[TokenChainDataModel.project_id]")
    token_entity = relationship("EntityModel", back_populates="token_entity", lazy="select",
                                primaryjoin="TokenModel.entity_id == EntityModel.id",
                                foreign_keys=[entity_id])


class NewsPlatformModel(Base):
    __tablename__ = "news_platform"

    name = Column(Text)
    content_type = Column(Text)
    extra_data = Column(JSONB)
    entity_id = Column(UUID(as_uuid=True))
    type = Column(Text)
    interval = Column(Text)

    entity_NewsPlatformModel = relationship("EntityModel", back_populates="entity_NewsPlatform", lazy="select",
                                            primaryjoin="NewsPlatformModel.entity_id == EntityModel.id",
                                            foreign_keys=[entity_id])


class ExchangeModel(Base):
    __tablename__ = "exchange_platform"

    entity_id = Column(UUID(as_uuid=True))
    type = Column(Text)
    name = Column(Text)
    content_type = Column(Text)
    interval = Column(Text)
    extra_data = Column(JSONB)
    entity_ExchangeModel = relationship("EntityModel", back_populates="exchange_platform", lazy="select",
                                        primaryjoin="ExchangeModel.entity_id == EntityModel.id",
                                        foreign_keys=[entity_id])


class EntityTagModel(Base):
    __tablename__ = "entity_tag"

    entity_id = Column(UUID(as_uuid=True), index=True, comment="entity ID")
    tag_id = Column(UUID(as_uuid=True), index=True)
    type = Column(String)

    entity = relationship("EntityModel", back_populates="entity_tags", lazy="select",
                          primaryjoin="EntityTagModel.entity_id == EntityModel.id", foreign_keys=[entity_id])
    tag = relationship("TagModel", back_populates="entity_tags", lazy="select",
                       primaryjoin="EntityTagModel.tag_id == TagModel.id", foreign_keys=[tag_id])


class TagModel(Base):
    __tablename__ = "tag"

    slug = Column(String)
    is_visible = Column(Boolean, nullable=False, default=True)

    entity_tags = relationship("EntityTagModel", back_populates="tag", lazy="select",
                               primaryjoin="TagModel.id == EntityTagModel.tag_id",
                               foreign_keys="[EntityTagModel.tag_id]")
    tag_intelligences = relationship(
        "TagIntelligenceModel",
        back_populates="tag",
        lazy="select",
        primaryjoin="TagModel.id == TagIntelligenceModel.tag_id",
        foreign_keys="[TagIntelligenceModel.tag_id]"
    )

    ai_agent = relationship("AiAgentModel", back_populates="tag", lazy="select",
                            primaryjoin="TagModel.id == AiAgentModel.tag_id", foreign_keys="[AiAgentModel.tag_id]")


class TagIntelligenceModel(Base):

    __tablename__ = "tag_intelligence"

    tag_id = Column(UUID(as_uuid=True), nullable=False, comment="tag ID")
    intelligence_id = Column(UUID(as_uuid=True), nullable=False, comment="intel ID")
    type = Column(Text, nullable=True, comment="type (such as signal)")

    tag = relationship(
        "TagModel",
        back_populates="tag_intelligences",
        lazy="select",
        primaryjoin="TagIntelligenceModel.tag_id == TagModel.id",
        foreign_keys=[tag_id]
    )

    intelligence = relationship(
        "IntelligenceModel",
        back_populates="tag_intelligences",
        lazy="select",
        primaryjoin="TagIntelligenceModel.intelligence_id == IntelligenceModel.id",
        foreign_keys=[intelligence_id]
    )