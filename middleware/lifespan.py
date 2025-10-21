from contextlib import asynccontextmanager
from typing import Any, Callable, NoReturn, Awaitable
from fastapi import FastAPI
from data import Context, rabbit, cache, db
from .security import RS256Checker
import logging
import asyncio
import settings


logger = logging.getLogger('app')


LifespanCallable = Callable[..., Awaitable[None]] | Callable[..., Awaitable[NoReturn]]

# Public list area
startup_list: list[LifespanCallable] = []
shutdown_list: list[LifespanCallable] = []


def _startup_done(task: asyncio.Task[None]):
    try:
        task.result()
    except asyncio.CancelledError:
        pass
    except:
        logger.exception(f"Exception occurred during initialization {task.get_name()}")


def _shutdown_done(task: asyncio.Task[None]):
    try:
        task.result()
    except asyncio.CancelledError:
        pass
    except:
        logger.exception(f"Exception occurred during service shutdown {task.get_name()}")


@asynccontextmanager
# Initialize context
async def lifespan_context(app: FastAPI):
    # Startup
    app.state.context = Context(
        rabbit=rabbit.RabbitConfig(settings.RABBIT_URL) if settings.RABBIT_URL else None,
        mastercache=cache.RedisConfig(settings.CACHE_URL) if settings.CACHE_URL else None,
        slavecache=cache.RedisConfig(settings.SLAVE_CACHE_URL) if settings.SLAVE_CACHE_URL else None,
        databases={
            key: db.DatabaseConfig(url)
            for key, url in settings.DATABASE_DICT.items()
        } if settings.DATABASE_DICT else None,
    )

    app.state.checker = RS256Checker(settings.JWT_PUBLIC_KEY)

    async with app.state.context:
        for startup_coro_func in startup_list:
            task = asyncio.create_task(
                startup_coro_func(app), name=startup_coro_func.__name__
            )
            task.add_done_callback(_startup_done)

        # Running
        yield

        # Shutdown
        tasks: list[asyncio.Task[None]] = []
        for end_coro_func in shutdown_list:
            tasks.append(
                asyncio.create_task(end_coro_func(app), name=end_coro_func.__name__)
            )
            tasks[-1].add_done_callback(_shutdown_done)
        await asyncio.gather(*tasks)


def on_startup(
    func: LifespanCallable
):
    """
    Configure initialization startup tasks
    """
    startup_list.append(func)
    return func


def on_shutdown(
    func: LifespanCallable
):
    """
    Configure service shutdown tasks
    """
    shutdown_list.append(func)
    return func