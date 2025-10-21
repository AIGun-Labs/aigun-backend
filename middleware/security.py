import base64
from enum import Enum
from typing import Callable, Any, Mapping
from pydantic import BaseModel
import hmac
import hashlib
import time
from jose import jwt, exceptions as jwt_exc, JWTError
import json
import settings


class SecurityStatus(Enum):
    UNKNOWN = -1
    AUTHORIZED = 0

    NO_AUTH = 1000
    INVALID_SCHEMA = 1001
    UNSUPPORTED_SCHEMA = 1002
    AUTH_ERROR = 1003
    AUTH_FAILED = 1004
    AUTH_EXPIRED = 1005


class SecurityData(BaseModel):
    auth: str
    verified: bool
    certificated: SecurityStatus
    data: dict[str, Any] = {}

    @property
    def status(self) -> int:
        match self.certificated:
            case SecurityStatus.AUTHORIZED: return 200
            case SecurityStatus.NO_AUTH: return 401
            case SecurityStatus.INVALID_SCHEMA: return 403
            case SecurityStatus.UNSUPPORTED_SCHEMA: return 501
            case SecurityStatus.AUTH_ERROR: return 400
            case SecurityStatus.AUTH_FAILED: return 401
            case SecurityStatus.AUTH_EXPIRED: return 401
            case _: return 500

    @property
    def code(self) -> int:
        value = self.certificated.value
        if value >= 1000:
            return value + 99101
        return value

    @property
    def response(self) -> dict[str, int | str]:
        return {
            'code': self.code,
            'message': self.certificated.name.capitalize().replace('_', ' '),
            'status': self.status,
        }

    @classmethod
    def ok(cls, auth: str, data: dict[str, Any] | None = None) -> 'SecurityData':
        return SecurityData(
            auth=auth,
            verified=True,
            certificated=SecurityStatus.AUTHORIZED,
            data=data or {},
        )

    def with_certificated(self, certificated: SecurityStatus, data: dict[str, Any] | None = None) -> 'SecurityData':
        return SecurityData(
            auth=self.auth,
            verified=self.verified,
            certificated=certificated,
            data=self.data | (data or {}),
        )

    def __str__(self):
        return json.dumps(self.response | {'data': self.data}, indent=4)


def check_checkcode(check_salt: bytes, check_code: str, timestamp: int) -> bool:
    # Calculate the start time of the minute where the current timestamp is located
    now = timestamp - timestamp % 60
    # Decide whether to check the previous minute or the next minute based on the seconds of the timestamp
    other = now - 60 if timestamp % 60 < 30 else now + 60
    # Check timestamps for current minute, previous minute, or next minute
    for ts in [now, other]:
        digest = hmac.new(check_salt, ts.to_bytes(4, 'big'), hashlib.sha256).hexdigest()
        if digest == check_code:
            return True
    return False


class SecurityCheckerBase:
    def get_all_schema(self) -> list[str]:
        return [name[8:] for name in dir(self) if name.startswith('checker_')]

    def authorize(self, headers: Mapping[str, str]) -> SecurityData:
        authorization = headers.get('Authorization', '').strip()
        failed_result = SecurityData(
            auth=authorization,
            verified=False,
            certificated=SecurityStatus.UNKNOWN,
        )
        if not authorization:
            return failed_result.with_certificated(SecurityStatus.NO_AUTH)
        if ' ' not in authorization:
            return failed_result.with_certificated(SecurityStatus.INVALID_SCHEMA)
        schema, token = authorization.split(' ', 1)
        if checker := getattr(self, f'checker_{schema.lower()}', None):
            return checker(token, headers)
        return failed_result.with_certificated(SecurityStatus.UNSUPPORTED_SCHEMA)


class RS256Checker(SecurityCheckerBase):
    def __init__(self, public_key: str | dict[str, Any]) -> None:
        self._public_key = public_key

    def checker_bearer(self, token: str, headers: dict[str, str]) -> SecurityData:
        failed_result = SecurityData(
            auth=token,
            verified=False,
            certificated=SecurityStatus.AUTH_FAILED,
        )
        try:

            data = jwt.decode(token, settings.JWT_PUBLIC_KEY, algorithms=["RS256"], options={"verify_aud": False})
            return SecurityData(
                auth=token,
                verified=True,
                certificated=SecurityStatus.AUTHORIZED,
                data=data,
            )
        except jwt_exc.ExpiredSignatureError:
            return failed_result.with_certificated(SecurityStatus.AUTH_EXPIRED)
        except jwt_exc.JWTError as e:
            return failed_result


class JWTGenerator:
    def __init__(self, secret_key: str, algorithm: str = "RS256", expires_in: int = 3600):

        self.secret_key = secret_key
        self.algorithm = algorithm
        self.expires_in = expires_in

    def generate_token(self, payload: dict) -> str:
        """
        Generate token
        """
        # Add expiration time to the payload
        payload["exp"] = time.time() + self.expires_in
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)