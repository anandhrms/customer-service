from http import HTTPStatus

from core.exceptions import CustomException
from core.security.access_control import AccessControl, Everyone


class InsufficientPermissionsException(CustomException):
    code = HTTPStatus.FORBIDDEN
    error_code = HTTPStatus.FORBIDDEN
    message = "Insufficient permissions"


async def get_user_principals() -> list:
    principals = [Everyone]

    return principals


Permissions = AccessControl(
    user_principals_getter=get_user_principals,
    permission_exception=InsufficientPermissionsException,
)
