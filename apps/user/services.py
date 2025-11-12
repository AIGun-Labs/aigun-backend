import json
import settings

from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from apps.user import models
from apps.user import schemas
from middleware import Request
from views.render import JsonResponseEncoder


class AiAgentFollowServices:

    @staticmethod
    async def get_ai_agent_list(request: Request) -> Optional[List[schemas.AiAgentOutSchema]]:
        """Get AI Agent list"""
        master_cache = request.context.mastercache.backend
        slave_cache = request.context.slavecache.backend
        if not slave_cache:
            slave_cache = master_cache

        # Try to get from cache first
        cache_key = f"dogex:intel_user:ai_agent_list"
        cached_data = await slave_cache.get(cache_key)
        if cached_data:
            agent_dicts = json.loads(cached_data.decode("utf-8"))

            # Restore to Pydantic model list
            return [schemas.AiAgentOutSchema.model_validate(d) for d in agent_dicts]

        # Not in cache, fetch from database
        async with request.context.database.dogex() as session:
            result = await session.execute(select(models.AiAgentModel).options(joinedload(models.AiAgentModel.tag)).order_by(models.AiAgentModel.rank))
            agents = result.scalars().all()
            ai_agent_data = []
            if not agents:
                return []
            for agent in agents:
                agent_data = schemas.AiAgentOutSchema.model_validate(agent)
                ai_agent_data.append(agent_data)

        # Convert Pydantic models to dictionaries for JSON serialization, and set cache expiration (seconds)
        ai_agent_dicts = [m.model_dump() for m in ai_agent_data]

        # Cache AI Agent list, expiration time adjusted to 1 day
        await master_cache.set(
            cache_key,
            json.dumps(ai_agent_dicts, cls=JsonResponseEncoder),
            ex=int(settings.EXPIRES_FOR_AI_AGENT_LIST) if isinstance(settings.EXPIRES_FOR_AI_AGENT_LIST, (int, float)) else None,
        )
        return ai_agent_data



ai_agent_follow_services = AiAgentFollowServices()