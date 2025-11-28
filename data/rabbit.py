import aio_pika
from aio_pika import RobustConnection, RobustChannel, RobustExchange, RobustQueue, IncomingMessage
from pydantic import BaseModel, Field
from typing import TypeVar, TypeVarTuple, Unpack, Any, overload, AsyncGenerator, Generator, Tuple
import json as jsonlib
import asyncio
import yarl

ModelType = TypeVar("ModelType", bound=BaseModel)
_Type = TypeVar("_Type")
_TypeGroup = TypeVarTuple("_TypeGroup")

__all__ = ["RabbitConfig", "RabbitMQ", "IncomingMessage", "RobustConnection", "RobustChannel", "RobustExchange",
           "RobustQueue"]


class RabbitConfig(BaseModel):
    host: str = "localhost"
    port: int = 5672
    login: str = Field("guest", alias="user")
    password: str = "guest"
    virtualhost: str = "/"
    ssl: bool = False
    exchange: str | None = None

    def __init__(self, url: str | yarl.URL | None = None, **kwargs):
        if url is not None:
            if isinstance(url, str):
                url = yarl.URL(url)
            kwargs.update({
                "host": url.host,
                "port": url.port,
                "user": url.user,
                "password": url.password,
                "virtualhost": url.path,
                "ssl": url.scheme == "amqps",
            })
        super().__init__(**kwargs)


class RabbitMQ:
    def __init__(
            self,
            config: RabbitConfig | yarl.URL | None = None,
            *,
            host: str | None = None,
            user: str | None = None,
            password: str | None = None,
            exchange: str | None = None,
            loop: asyncio.AbstractEventLoop | None = None
    ) -> None:
        if config is None:
            self._url = aio_pika.connection.make_url(
                host=host,
                login=user,
                password=password,
            )
        elif isinstance(config, yarl.URL):
            self._url = config
        else:
            self._url = aio_pika.connection.make_url(**config.model_dump(exclude=["exchange"]))
        self._loop = loop or asyncio.get_event_loop()
        self._client = aio_pika.RobustConnection(
            self._url,
            loop=self._loop,
        )
        self._channel: aio_pika.RobustChannel | None = None
        self._exchange: aio_pika.RobustExchange | None = None
        self._exchange_name = exchange
        self._init_task: asyncio.Task[None] = self._loop.create_task(self.ensure_connection())
        self._init_task.set_name(f"RabbitMQ.ensure_connection.{id(self):#018x}")

    async def ensure_connection(self) -> None:
        """
        Ensure connection to RabbitMQ server.
        """

        if self._channel is None:
            await self._client.connect()
            self._channel = await self._client.channel()
            if self._exchange_name is not None:
                self._exchange = await self._channel.get_exchange(self._exchange_name)
        elif self._channel.is_closed:
            if self._client.is_closed:
                self._client = aio_pika.RobustConnection(self._url, loop=self._loop, )
            self._channel = await self._client.channel()

    @overload
    async def send(self, queue: str, message: ModelType, **dump_kws) -> None:
        """
        Send a pydantic model to the specified queue.

        """
        ...

    @overload
    async def send(self, queue: str, message: str | bytes, **dump_kws) -> None:
        """
        Send a raw (any json) message to the specified queue.

        Send raw data that can be json.loads to the specified queue.
        """
        ...

    @overload
    async def send(self, queue: str, message: Any, **dump_kws) -> None:
        """
        Send a raw (any json) message to the specified queue.

        Send raw data that can be json.dumps to the specified queue.
        """
        ...

    async def send(self, queue: str, message: Any, **dump_kws) -> None:
        await self._init_task
        delivery_mode = dump_kws.pop("delivery_mode", None)
        if delivery_mode is not None:
            try:
                delivery_mode = int(delivery_mode)
            except:
                delivery_mode = None
        if isinstance(message, BaseModel):
            data = message.model_dump_json(**dump_kws).encode()
        elif isinstance(message, str):
            data = message.encode()
        elif isinstance(message, bytes):
            data = message
        else:
            data = jsonlib.dumps(message, **dump_kws).encode()
        exchange_name, queue_name = queue.split("/", 1) if "/" in queue else (None, queue)
        if exchange_name is not None:
            exchange: RobustExchange = await self._channel.get_exchange(exchange_name)
        elif self._exchange is not None:
            exchange = self._exchange
        else:
            exchange = self._channel.default_exchange
        await exchange.publish(
            aio_pika.Message(
                body=data,
                content_type="application/json",
                content_encoding="utf-8",
                delivery_mode=delivery_mode
            ),
            queue_name
        )

    @overload
    async def receive(
            self,
            queue_name: str,
            model: type[Tuple[Unpack[_TypeGroup]]]
    ) -> AsyncGenerator[Tuple[Tuple[Unpack[_TypeGroup]], IncomingMessage], None]:
        """
        Receive a raw json from the specified queue.

        Receive amorphous data that can be json.loads from the specified queue
        """
        ...

    @overload
    async def receive(
            self,
            queue_name: str,
            model: type[_Type],
            *,
            strict: bool | None = None,
            context: dict[str, Any] | None = None,
    ) -> AsyncGenerator[Tuple[_Type, IncomingMessage], None]:
        """
        Receive a pydantic model from the specified queue.

        Receive a pydantic model or data that can be json.loads from the specified queue

        If string is provided, decode with utf-8, if bytes is provided, return directly.
        """
        ...

    @overload
    async def receive(
            self,
            queue_name: str
    ) -> AsyncGenerator[Tuple[bytes, IncomingMessage], None]:
        """
        Receive a raw (any json) message from the specified queue.

        Receive raw bytes data from the specified queue.
        """
        ...

    async def receive(self, queue_name: str, model: type[_Type] | type[Tuple[Unpack[_TypeGroup]]] | None = None, *,
                      strict: bool | None = None, context: dict[str, Any] | None = None):
        await self._init_task
        async with self._client.channel() as channel:
            exchange_name, queue_name = queue_name.split("/", 1) if "/" in queue_name else (None, queue_name)
            # await self._channel.set_qos(prefetch_count=1)

            # Declare a named queue or temporary queue (all queues with exchanges are temporary queues)
            if queue_name and exchange_name is None:
                queue: aio_pika.robust_queue.RobustQueue = await channel.get_queue(queue_name, ensure=True)
            else:
                queue = await channel.declare_queue("", exclusive=True)

            if exchange_name is not None:
                exchange: RobustExchange = await channel.get_exchange(exchange_name)
            elif self._exchange is not None:
                exchange = self._exchange
            else:
                exchange = None
            if exchange is not None:
                if queue_name:
                    bindings = queue_name.split(',')
                    for binding in bindings:
                        await queue.bind(exchange, binding)
                else:
                    await queue.bind(exchange)

            if model is str:
                async for message in queue:
                    message: aio_pika.IncomingMessage
                    yield message.body.decode(), message
            elif model is bytes or model is None:
                async for message in queue:
                    message: aio_pika.IncomingMessage
                    yield message.body, message
            elif issubclass(model, BaseModel):
                async for message in queue:
                    message: aio_pika.IncomingMessage
                    yield model.model_validate_json(message.body, strict=strict, context=context), message
            else:
                async for message in queue:
                    message: aio_pika.IncomingMessage
                    yield jsonlib.loads(message.body), message

    async def close(self) -> None:
        await self._client.close()
