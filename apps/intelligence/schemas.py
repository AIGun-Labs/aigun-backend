from fastapi import Query
from pydantic import BaseModel
from typing import Optional

from data.logger import create_logger

logger = create_logger("dogex-intelligence")



class IntelligenceQueryParams(BaseModel):

    is_valuable: Optional[bool] | None = Query(default=True, description="Whether it is valuable")

    address: Optional[str] | None = Query(default=None, description="Token address")
    chain_name: Optional[str] | None = Query(default=None, description="Chain")