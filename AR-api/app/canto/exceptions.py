from http import HTTPStatus

from app.exceptionhandler import AppError


class CantoGroupRemovalFailed(AppError):
    default_message = "Failed to remove user from Canto basic group"
    default_error_code = "canto_group_removal_failed"
    default_status_code = HTTPStatus.BAD_GATEWAY
