import uuid
from fastapi import Query
from pydantic import BaseModel, model_validator, model_serializer
from typing import Optional, List
from datetime import datetime

from app.services import format_time
from data.logger import create_logger

logger = create_logger("dogex-intelligence")



class IntelligenceQueryParams(BaseModel):

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