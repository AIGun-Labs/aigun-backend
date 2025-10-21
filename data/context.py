import time

from .fetch import AsyncLimitClient
from .cache import Cache
from .rabbit import RabbitMQ
from .db import DatabaseConfig, declare_database, close_all_sessions, DatabaseFactory
from .logger import create_logger
from typing import Any
import traceback
import asyncio
import sys


class DatabaseProxy:
    __METHODS__ = {
        'restart'
    }

    async def restart(self):
        await close_all_sessions()
        for db_name in self._dbs:
            self._dbs[db_name] = declare_database(self._db_configs[db_name])

    def __init__(self, dbs: dict[str, tuple[DatabaseFactory, DatabaseConfig]]) -> None:
        self._dbs = {key: db[0] for key, db in dbs.items()}
        self._db_configs = {key: db[1] for key, db in dbs.items()}

    def __getitem__(self, key: str) -> DatabaseFactory:
        return self._dbs[key]

    def __getattribute__(self, name: str) -> DatabaseFactory:
        if name.startswith('_') or name in self.__METHODS__:
            return super().__getattribute__(name)
        return self._dbs[name]


class Context:
    def __init__(
            self,
            slavecache: Any | None = None,
            mastercache: Any | None = None,
            databases: list[DatabaseConfig] | dict[str, DatabaseConfig] | None = None,
            rabbit: Any | None = None,
            limits: int = 20,
            period: float = 1.0,
    ) -> None:
        self._loop = None
        self._slavecache = None
        self._mastercache = None
        self._amqp = None
        self._dbs = None
        self._slavecache_config = slavecache
        self._mastercache_config = mastercache
        self._rabbit_config = rabbit
        self._databases = databases
        self._client = AsyncLimitClient(limits=limits, sleeps=period)
        self._logger = create_logger('context', index=True, ecosystem=False)
        self._configs = {}
        self._init = False

    def __getitem__(self, key: str) -> Any:
        return self._configs[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self._configs[key] = value

    async def close(self):
        if self._slavecache is not None:
            await self._slavecache.close()
        if self._mastercache is not None:
            await self._mastercache.close()
        if self._amqp is not None:
            await self._amqp.close()
        if self._dbs:
            await close_all_sessions()
        await self._client.aclose()

    async def initalize(self):
        if not self._init:
            self._loop = asyncio.get_event_loop()
            if self._slavecache_config is not None:
                self._slavecache = Cache(self._slavecache_config)
            if self._mastercache_config is not None:
                self._mastercache = Cache(self._mastercache_config)
            if self._rabbit_config is not None:
                self._amqp = RabbitMQ(self._rabbit_config)
            if self._databases is not None:
                if isinstance(self._databases, dict):
                    self._dbs = DatabaseProxy({
                        key: (declare_database(database), database)
                        for key, database in self._databases.items()
                    })
                elif isinstance(self._databases, list):
                    self._dbs = DatabaseProxy({
                        database.url.split('/')[-1]: (declare_database(database), database)
                        for database in self._databases
                    })
            self._init = True

    async def __aenter__(self) -> 'Context':
        await self.initalize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()

    @property
    def loop(self) -> asyncio.AbstractEventLoop:
        return self._loop

    @property
    def mastercache(self) -> Cache:
        """
        Get cache object
        """
        assert self._mastercache is not None, "mastercache is not configured"
        return self._mastercache

    @property
    def slavecache(self) -> Cache:
        """
        Get cache object
        """
        assert self._slavecache is not None, "slavecache is not configured"
        return self._slavecache

    @property
    def log(self):
        """
        Get logger object
        """
        return self._logger

    @property
    def amqp(self) -> RabbitMQ:
        """
        Get message queue object
        """
        assert self._amqp is not None, "rabbitmq is not configured"
        return self._amqp

    @property
    def database(self) -> DatabaseProxy:
        """
        Get database connection factory
        """
        assert self._dbs is not None, "database is not configured"
        return self._dbs

    @property
    def client(self) -> AsyncLimitClient:
        """
        Get rate-limited request client
        """
        return self._client

    @property
    def ts(self):
        """
        Get current timestamp
        """
        return int(time.time() * 1000)

    @property
    def traceback(self):
        """
        Get current context error stack trace (text)
        """
        exc_type, exc_val, exc_tb = sys.exc_info()
        return ''.join(traceback.format_exception(exc_type, exc_val, exc_tb))