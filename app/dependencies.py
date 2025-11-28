import functools
import logging
from uuid import UUID

from starlette.responses import Response
import settings
from types import SimpleNamespace
from fastapi import Query, FastAPI
import redis.asyncio as redis
from fastapi_limiter import FastAPILimiter
from middleware.lifespan import on_startup
from jose import jwt, exceptions as jwt_exc, JWTError
from middleware.limiter import RateLimiter
from middleware.request import Request
from utils import exceptions
from data.logger import create_logger

req_logger = create_logger("dogex-intelligence-request")


def request_init(*, verify: bool = True, limiter: bool = True):
    async def wrapper(request: Request, response: Response):
        from utils.exceptions import AuthException

        request = Request.from_request(request)

        # Attempt to parse token (if exists)
        request.authorize()

        # If token exists and is verified, parse user information
        if request.verified:
            request.user_id = request.user.get("sub")
            request.tid = request.user.get("tid")
            request.email = request.user.get("email")
            request.state.user_id = request.user.get("sub")

        else:
            # When no token or invalid token, decide whether to raise exception based on verify parameter
            if verify:
                verify_response = request.response_for_verify()
                raise AuthException(
                    code=verify_response.get("code"),
                    msg=verify_response.get("message"),
                    status_code=verify_response.get("status"),
                    request=request
                )
            else:
                # Guest mode, set default values
                request.user_id = None
                request.tid = None
                request.email = None
                request.state.user_id = None

        # Authentication verification
        if verify:
            # Verify if account has been deactivated
            await check_account_valid(request)

        # Log AppStore review access paths
        if request.email and request.email == "aigun_appstore_review@gmail.com":
            req_logger.info(f"AppStore review access path, url: {request.url}")

        # Global rate limiting verification
        # if limiter:
        #     await RateLimiter(
        #         times=settings.LIMITER_CONFIG["GLOBAL_THROTTLE_RATES"]["limit_times"],
        #         seconds=settings.LIMITER_CONFIG["GLOBAL_THROTTLE_RATES"]["limit_seconds"],
        #         identifier=get_id_or_ip
        #     )(request, response)

        return request

    return wrapper

# JWT verification
def auth_verify(request: Request):
    """
    Encapsulate request through dependency injection and perform default JWT authentication
    """
    request = Request.from_request(request)
    # For testing convenience, remove JWT
    request.authorize()
    if not request.verified:
        # Return error response if verification fails
        verify_response = request.response_for_verify()
        # Throw error
        from utils.exceptions import AuthException
        raise AuthException(
            code=verify_response.get("code"),
            msg=verify_response.get("message"),
            status_code=verify_response.get("status"),
            request=request
        )

    return request


@on_startup
async def limiter_init(app: FastAPI):
    """
    Connect to Redis to store rate limit status
    """
    redis_client = await redis.Redis.from_url(settings.CACHE_URL, decode_responses=True)
    await FastAPILimiter.init(redis_client, prefix="dogex")


async def get_id_or_ip(request):
    """
    Get user id, if not available then get IP
    """
    auth_data = request.scope.get("auth_data")
    if auth_data and auth_data.data:
        return auth_data.data.get("id")

    ip = str(
            request.headers.get('CF-Connecting-IP') or \
            request.headers.get("X-Forwarded-For") or \
            request.headers.get("X-Real-IP") or \
            (request.client or SimpleNamespace(host='127.0.0.1')).host
        )

    try:
        ip = ip.split(",")[0]
    except:
        req_logger.exception("Exception in getting IP from request")
        pass

    return ip


async def get_id_or_ip_add_path(request):
    """
    Get user id, if not available then get IP, plus add interface path
    """
    auth_data = request.scope.get("auth_data")
    if auth_data and auth_data.data:
        return auth_data.data.get("id") + ":" + request.scope["path"]

    ip = str(
        request.headers.get('CF-Connecting-IP') or \
        request.headers.get("X-Forwarded-For") or \
        request.headers.get("X-Real-IP") or \
        (request.client or SimpleNamespace(host='127.0.0.1')).host
    )

    try:
        ip = ip.split(",")[0]
    except:
        req_logger.exception("Exception in getting IP from request")
        pass

    return ip + ":" + request.scope["path"]


async def check_account_valid(request: Request):
    """
    Verify if account is obsolete
    """
    from apps.user import exceptions as user_exceptions
    slave_redis = request.context.slavecache.backend

    is_obsolete = await slave_redis.hget(f"dogex:user:info:{request.user_id}", "is_obsolete")

    if is_obsolete is None:
        return

    is_obsolete: int = int(is_obsolete.decode("utf-8"))
    # is_obsolete: int = int(is_obsolete)



# Pagination query parameter dependency class
class PaginationQueryParams:
    def __init__(self,
                 page: int = Query(default=settings.PAGE, ge=1),
                 page_size: int = Query(default=settings.PAGE_SIZE,
                                        ge=settings.MIN_PAGE_SIZE,
                                        le=settings.MAX_PAGE_SIZE,
                                        alias="size")) -> None:
        self.page = page
        self.page_size = page_size