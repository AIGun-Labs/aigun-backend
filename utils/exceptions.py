from fastapi import status
from data import code as common_code, msg as common_msg


class AuthException(Exception):
    def __init__(self, code: int = None, msg: str = None, status_code: int = None, *args, **kwargs):
        self.code = code or common_code.CODE_AUTH_FAIL
        self.msg = msg or common_msg.AUTH_FAIL
        self.status_code = status_code or status.HTTP_401_UNAUTHORIZED
        self.args = args
        self.kwargs = kwargs