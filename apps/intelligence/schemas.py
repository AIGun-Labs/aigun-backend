import uuid
from fastapi import Query
from pydantic import BaseModel, model_validator
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