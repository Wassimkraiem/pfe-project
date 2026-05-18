from http import HTTPStatus

from app.exceptionhandler import AppError


class CantoGroupRemovalFailed(AppError):
    default_message = "Failed to remove user from Canto basic group"
    default_error_code = "canto_group_removal_failed"
    default_status_code = HTTPStatus.BAD_GATEWAY


class CantoDownloadConfigMissing(AppError):
    default_message = "Canto download is not configured"
    default_error_code = "canto_download_config_missing"
    default_status_code = HTTPStatus.SERVICE_UNAVAILABLE


class CantoVideoNotFound(AppError):
    default_message = "Canto video not found"
    default_error_code = "canto_video_not_found"
    default_status_code = HTTPStatus.NOT_FOUND


class CantoDownloadFailed(AppError):
    default_message = "Failed to download Canto video"
    default_error_code = "canto_download_failed"
    default_status_code = HTTPStatus.BAD_GATEWAY


class CantoInvalidDownloadRequest(AppError):
    default_message = "Invalid Canto download request"
    default_error_code = "canto_invalid_download_request"
    default_status_code = HTTPStatus.BAD_REQUEST
