import uuid
from fastapi import Query
from pydantic import BaseModel, model_validator, model_serializer, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

from app.services import format_time
from data.logger import create_logger

logger = create_logger("dogex-intelligence")



class IntelligenceQueryParams(BaseModel):
    type: Optional[str] | None = Query(default=None, description="radar_signal/event")
    subtype: Optional[str] | None = Query(default=None, description="subtype")
    is_valuable: Optional[bool] | None = Query(default=True, description="Whether it is valuable")

    address: Optional[str] | None = Query(default=None, description="Token address")
    chain_name: Optional[str] | None = Query(default=None, description="Chain")



class IntelligenceListOutSchema(BaseModel):

    id: uuid.UUID
    is_valuable: Optional[bool]
    analyzed_time: Optional[int | float]
    analyzed: Optional[dict]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    type: Optional[str] = None
    title: Optional[str]
    extra_datas: Optional[dict] = None
    content: Optional[str]
    source_url: Optional[str]
    tags: Optional[List[str]]
    score: Optional[float]
    medias: Optional[list[dict]]
    subtype: Optional[str]
    published_at: Optional[datetime]
    showed_tokens: Optional[List]
    spider_time: Optional[datetime]


    class Config:
        from_attributes = True
        json_encoders = {
            datetime: format_time,
        }


class TokenInfoOutSchema(BaseModel):
    price_usd: Optional[float] = 0
    market_cap: Optional[float] = 0
    liquidity: Optional[float] = 0
    volume_24h: Optional[float] = 0
    holders: Optional[int]
    price_change_24h: Optional[float] = 0

    is_native: Optional[bool] = False
    is_mainstream: Optional[bool] = False
    narrative: Optional[str] = ""

    class Config:
        from_attributes = True



class EntityResponse(BaseModel):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    name: str
    type: Optional[str] = None
    influence_level: Optional[str] = None
    influence_score: Optional[float] = None
    description: Optional[str] = None
    avatar: Optional[str] = None
    extra_data: Optional[dict] = None
    is_test: bool
    is_visible: bool = True
    subtype: Optional[str] = None
    interval: Optional[float] = None

    @model_validator(mode='before')
    def convert_orm(cls, data):

        influence_level = data.influence_level.upper() if data.influence_level else "B"
        interval_mapping = {
            "EX":  0.1,
            "S": 0.5,
            "A": 1,
            "B": 2
        }

        try:
            data.interval = interval_mapping[influence_level]
        except:
            data.interval = 0

        return data

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: format_time,
        }

    @model_serializer(mode='wrap')
    def serialize_wrap(self, handler):
        data = handler(self)

        for key, val in data.items():
            if isinstance(val, datetime):
                data[key] = val.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

        return data


class IntelligenceWithoutEntitiesOutSchema(BaseModel):
    id: uuid.UUID
    published_at: datetime
    created_at: datetime
    updated_at: Optional[datetime]
    is_valuable: Optional[bool]
    source_id: Optional[uuid.UUID]
    source_url: Optional[str]
    type: Optional[str] = None
    subtype: Optional[str]
    title: Optional[str]
    content: Optional[str]
    abstract: Optional[str]
    extra_datas: Optional[dict]
    medias: Optional[list[dict]]
    analyzed: Optional[dict]
    score: Optional[float]
    spider_time: Optional[datetime]
    push_time: Optional[datetime]
    signal_tags: Optional[List[str]] = []
    analysis_tags: Optional[List[Dict]] = Field(default=None, description="The intelligence analysis tag associated with this entity is filtered by the tag's type being intel_analysis")
    review_status: Optional[str] = "unreviewed"
    info: Optional[dict] = {}
    is_adjusted: Optional[bool] = False

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: format_time,
        }

    @model_serializer(mode='wrap')
    def serialize_wrap(self, handler):
        data = handler(self)

        for key, val in data.items():
            if isinstance(val, datetime):
                data[key] = val.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

        return data

    @model_validator(mode='before')
    def add_field_before_validate(cls, data):

        # Process tag association, if type is signal, place it in signal_tags, otherwise place it in tags
        signal_tags = []
        analysis_tags_list = []
        if hasattr(data, 'tag_intelligences') and data.tag_intelligences:
            for tag_intelligence in data.tag_intelligences:
                if hasattr(tag_intelligence, 'tag') and tag_intelligence.tag:
                    if tag_intelligence.type == "signal":
                        signal_tags.append(tag_intelligence.tag.slug)
                # Get tags of type intel_analysis (to defend against empty tags)
                if (
                        hasattr(tag_intelligence, 'tag')
                        and tag_intelligence.tag is not None
                        and getattr(tag_intelligence.tag, 'type', None) == "intel_analysis"
                        and getattr(tag_intelligence, 'is_deleted', False) == False
                ):
                    analysis_tags_dict: Dict[str, Any] = {}
                    if tag_intelligence.tag:
                        analysis_tags_dict["id"] = tag_intelligence.tag.id
                        analysis_tags_dict["slug"] = tag_intelligence.tag.slug
                        analysis_tags_dict["type"] = tag_intelligence.tag.type
                        analysis_tags_list.append(analysis_tags_dict)

        # Manually aligned information
        data.info = {
            "analyze": data.intelligence_info.analyze if data.intelligence_info else "",
            "problem": data.intelligence_info.problem if data.intelligence_info else ""
        }

        # Is it manually aligned
        if data.adjusted_tokens is not None or any(data.info.values()):
            data.is_adjusted = True

        data.analysis_tags = analysis_tags_list
        data.signal_tags = signal_tags

        if not data.review_status:
            data.review_status = "unreviewed"

        return data


class IntelligenceQueryParamsCount(BaseModel):
    type: Optional[str] | None = Query(default=None, description="Intelligence type: twitter/telegram/news")
    subtype: Optional[str] | None = Query(default=None, description="Subtype (optional)")
    platform_type: Optional[str] | None = Query(default=None, description="Platform type")

    entity_id: Optional[str] | None = Query(default=None, description="Associated entity ID")
    is_valuable: Optional[bool] | None = Query(default=True, description="Is valuable")
    influence_level: Optional[str] | None = Query(default=None, description="Entity influence level: Ex/S/A/B")
    entity_type: Optional[str] | None = Query(default=None, description="Entity type: person/token")

    key_word: Optional[str] | None = Query(default=None, description="Keyword")

    address: Optional[str] | None = Query(default=None, description="Token address")
    network: Optional[str] | None = Query(default=None, description="Chain network")
