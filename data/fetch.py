import http
import http.cookiejar
import httpx
from typing import IO, Any, Callable, Mapping, MutableMapping, Optional, Sequence, Tuple, TypeVar, Iterable, AsyncIterable
from ssl import SSLError
from anyio import EndOfStream
import asyncio
import time
from data.logger import  create_logger

logger = create_logger("dogex-intelligence")

USE_CLIENT_DEFAULT = httpx.USE_CLIENT_DEFAULT

UseClientDefault = USE_CLIENT_DEFAULT.__class__

URL = httpx.URL | str
Content = str | bytes | Iterable[bytes] | AsyncIterable[bytes] | None
Data = Mapping[str, Any] | None

# File types
BasicFile = IO[bytes] | bytes | str
NamedFile = Tuple[str | None, BasicFile]
NamedTypedFile = Tuple[str | None, BasicFile, str | None]
NamedTypedFileWithHeaders = Tuple[str | None, BasicFile, str | None, Mapping[str, str]]
FileRepresentation = BasicFile | NamedFile | NamedTypedFile | NamedTypedFileWithHeaders
Files = Mapping[str, FileRepresentation] | Sequence[Tuple[str, FileRepresentation]]

# Params types
BasicValue = str | int | float | bool | None
ValueType = BasicValue | Sequence[BasicValue]
Params = httpx.QueryParams | Mapping[str, ValueType] | list[Tuple[str, ValueType]] | Tuple[Tuple[str, ValueType], ...] | str | bytes | None

# Headers types
BasicHeader = str | bytes
HeaderType = httpx.Headers | Mapping[BasicHeader, BasicHeader] | Sequence[Tuple[BasicHeader, BasicHeader]] | None

CookiesType = httpx.Cookies | http.cookiejar.CookieJar | dict[str, str] | list[Tuple[str, str]]

# Auth types
AuthTypes = httpx.Auth | Callable[[httpx.Request], httpx.Request] | None


class AsyncLimiter:
    def __init__(self, limits: int = 20, period: float = 1.0):
        self._limits = limits
        self._period = period
        self._tokens = limits
        self._updated_at = time.monotonic()

    async def _acquire(self):
        now = time.monotonic()
        if now - self._updated_at > self._period:
            self._tokens = self._limits
            self._updated_at = now
        if self._tokens > 0:
            self._tokens -= 1
            return
        await asyncio.sleep(self._period + self._updated_at - now)
        self._tokens -= 1

    def _release(self):
        self._tokens += 1
        if self._tokens > self._limits:
            self._tokens = self._limits

    async def __aenter__(self):
        await self._acquire()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self._release()


class SchemeAuth(httpx.Auth):
    def __init__(self, scheme: str, token: str):
        self._scheme = scheme
        self._token = token

    def auth_flow(self, request: httpx.Request):
        request.headers['Authorization'] = f'{self._scheme.capitalize()} {self._token}'
        yield request


class ParamAuth(httpx.Auth):
    def __init__(self, name: str, token: str) -> None:
        self._name = name
        self._token = token

    def auth_flow(self, request: httpx.Request):
        request.url = request.url.copy_set_param(self._name, self._token)
        yield request


class RetryOverlimit(Exception):
    def __str__(self) -> str:
        return "Retry over limit"


class AsyncLimitClient(httpx.AsyncClient):
    def __init__(self, max_keepalive_connections: int = 50, max_connections: int = 150, timeout: int = 60, limits: int = 35, sleeps: float = 1, retries: int = 5, auth_value: str | None = None, auth_schema: str = 'bearer', **kwargs):
        super().__init__(
            timeout=timeout,
            limits=httpx.Limits(max_keepalive_connections=max_keepalive_connections, max_connections=max_connections),
            proxy='http://twitter:n4vsD4_kjcAPy3F2az@dc.decodo.com:10000',
            **kwargs
        )
        self._sleep = sleeps
        self._retries = retries
        self._limiter = AsyncLimiter(limits=limits, period=sleeps)
        self._auth_scheme = auth_schema
        self._auth_value = auth_value
        if self._auth_value:
            if auth_schema.startswith('param'):
                self._auth = ParamAuth(auth_schema.removeprefix('param:').strip(), auth_value)
            else:
                self._auth = SchemeAuth(auth_schema, auth_value)


    async def send(self,
        request: httpx.Request,
        *,
        stream: bool = False,
        auth: str | AuthTypes | UseClientDefault = USE_CLIENT_DEFAULT,
        follow_redirects: bool | UseClientDefault = USE_CLIENT_DEFAULT,
        auth_scheme: str | UseClientDefault = USE_CLIENT_DEFAULT,
    ) -> httpx.Response:
        if isinstance(auth, str):
            if auth_scheme is USE_CLIENT_DEFAULT:
                auth_scheme = self._auth_scheme
            if auth_scheme.startswith('param'):
                auth = ParamAuth(auth_scheme.removeprefix('param:').strip(), auth)
            else:
                auth = SchemeAuth(auth_scheme, auth)
        for _ in range(self._retries):
            try:
                async with self._limiter:
                    return await super().send(request, stream=stream, auth=auth, follow_redirects=follow_redirects)
            except (httpx.RequestError, SSLError, EndOfStream) as e:
                await asyncio.sleep(self._sleep)
        raise RetryOverlimit()
