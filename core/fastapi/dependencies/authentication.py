from fastapi import Depends, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from core.config import config
from core.exceptions.base import CustomException


class AuthenticationRequiredException(CustomException):
    code = status.HTTP_401_UNAUTHORIZED
    error_code = status.HTTP_401_UNAUTHORIZED
    message = "Authentication required"


class SuperAdminPermissionRequiredException(CustomException):
    code = status.HTTP_403_FORBIDDEN
    error_code = status.HTTP_403_FORBIDDEN
    message = "Admin permission required"


class AuthenticationRequired:
    def __init__(
        self,
        request: Request,
        token: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=False)),
    ):
        if not token or not request.user.id:
            raise AuthenticationRequiredException()


class SuperAdminPermissionRequired(AuthenticationRequired):
    def __init__(
        self,
        request: Request,
        token: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=False)),
    ):
        super().__init__(request, token)
        if request.user.role_id != config.SUPER_USER_ROLE_ID:
            raise SuperAdminPermissionRequiredException()
