import asyncio
from types import SimpleNamespace
from typing import Any, Callable, Coroutine, Awaitable, Sequence
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp, Receive, Scope, Send
from fastapi.requests import Request as BaseRequest
from fastapi.responses import Response as BaseResponse
from .security import SecurityData, RS256Checker, SecurityCheckerBase
from data.logger import create_logger
from colorama import Fore, Style
from data import Context
import json as jsonlib
import datetime



class Request(BaseRequest):
    req_logger = create_logger('request')
    user_id = None

    def __init__(self, scope: Scope, receive: Receive) -> None:
        super().__init__(scope, receive)

    def authorize(self, checker: SecurityCheckerBase | None = None) -> SecurityData:
        """
        Support multiple verifications, if checker is not empty, use the specified checker, otherwise use the app's default checker
        """
        if checker is not None:
            self.scope['checker'] = checker
            self.scope['auth_data'] = checker.authorize(self.headers)
        elif self.scope.get('checker') is None:
            checker = self.app.state.checker
            if checker is not None:
                self.scope['checker'] = checker
                self.scope['auth_data'] = checker.authorize(self.headers)
        return self.scope.get('auth_data')

    @property
    def user(self) -> dict[str, Any]:
        auth_data: SecurityData | None = self.scope.get('auth_data')
        return auth_data.data if auth_data else {}

    @property
    def auth(self) -> str | None:
        auth_data: SecurityData | None = self.scope.get('auth_data')
        return auth_data.auth if auth_data else None

    @property
    def verified(self) -> bool:
        auth_data: SecurityData | None = self.scope.get('auth_data')
        return auth_data and auth_data.verified

    @property
    def credentials(self) -> SecurityData | None:
        return self.scope.get('auth_data')

    def raise_for_verify(self):
        """
        Throw exception if verification fails
        """
        if not self.verified:
            raise PermissionError('Unauthorized request')

    def response_for_verify(self):
        """
        Return error response if verification fails
        """
        if not self.verified:
            return self.credentials.response if self.credentials else dict(code=100001, message='Unauthorized request', status=401)

    @property
    def now(self) -> datetime.datetime:
        return datetime.datetime.now(datetime.UTC)

    @property
    def context(self) -> Context:
        """
        Get app's context object
        """
        return self.app.state.context

    @property
    def ip(self) -> str:
        if self.scope.get('client_ip') is None:
            ip =  str(
                self.headers.get('CF-Connecting-IP') or \
                self.headers.get("X-Forwarded-For") or \
                self.headers.get("X-Real-IP") or \
                (self.client or SimpleNamespace(host='127.0.0.1')).host
            )

            try:
                self.scope['client_ip'] = ip.split(",")[0]
            except:
                self.req_logger.exception("Exception in getting IP from request")
                self.scope['client_ip'] = ip

        return self.scope.get('client_ip')

    @property
    def region(self) -> str:
        if self.scope.get('client_region') is None:
            self.scope['client_region'] = str(
                self.headers.get('CF-IPCountry') or 'UNKNOWN'
            )
        return self.scope.get('client_region')

    @classmethod
    def from_request(cls, request: BaseRequest) -> 'Request':
        return cls(request.scope, request.receive)


class RequestMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, public_key: str, url_filters: Sequence[str] = ['/ping']) -> None:
        super().__init__(app)
        self._checker = RS256Checker(public_key)
        self._access_logger = create_logger('access')
        self._path_filters = set(url_filters)


    @classmethod
    def print_headers(cls, headers: dict[str, str]):
        return '\n'.join([f'{'-'.join(map(lambda s: s.capitalize(), k.split('-')))}: {v}' for k, v in headers.items()])


    async def dispatch(self, request: BaseRequest, call_next: RequestResponseEndpoint) -> BaseResponse:
        request = Request(request.scope, request.receive)
        if not hasattr(request.app.state, 'checker'):
            request.app.state.checker = self._checker
        # request.authorize(request.app.state.checker)
        response = await call_next(request)
        if request.url.path not in self._path_filters:
            base_text = f'{request.ip}#{request.region}-{request.method}<{response.status_code}>[{str(request.url.include_query_params())[:256]}]'
            if response.status_code >= 500:
                # Only 5xx errors need user information and other data for troubleshooting
                try: user_data = jsonlib.dumps(request.user, ensure_ascii=False)
                except: user_data = str(request.user)
                # self._access_logger.exception(base_text + f'\n{Fore.LIGHTWHITE_EX}UserData: {Fore.LIGHTBLUE_EX}' + user_data + f'\n{Fore.LIGHTWHITE_EX}RequestBody: {Fore.LIGHTBLUE_EX}' + (await request.body()).decode(errors='ignore') + Fore.LIGHTRED_EX)
            elif response.status_code >= 400:
                self._access_logger.warning(base_text)
            else:
                self._access_logger.info(base_text)
        if response.status_code == 404:
            response = BaseResponse(content=jsonlib.dumps(
                dict(code=-1, message='Access Denied', data=None),
                ensure_ascii=False
            ), status_code=403)
        return response