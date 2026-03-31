from http import HTTPStatus
from app.exceptionhandler import AppError


class ChannelNotFound(AppError):
    default_message = "Channel not found"
    default_error_code = "channel_not_found"
    default_status_code = HTTPStatus.NOT_FOUND


class ChannelForbidden(AppError):
    default_message = "You do not have access to this channel"
    default_error_code = "channel_forbidden"
    default_status_code = HTTPStatus.FORBIDDEN


class ChannelAlreadyExists(AppError):
    default_message = "Channel with this URL already exists"
    default_error_code = "channel_already_exists"
    default_status_code = HTTPStatus.CONFLICT


class InvalidChannelURL(AppError):
    default_message = "Invalid channel URL format"
    default_error_code = "invalid_channel_url"
    default_status_code = HTTPStatus.BAD_REQUEST
