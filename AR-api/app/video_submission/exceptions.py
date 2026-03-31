from http import HTTPStatus

from app.exceptionhandler import AppError


class SubmissionNotFound(AppError):
    default_message = "Video submission not found"
    default_error_code = "submission_not_found"
    default_status_code = HTTPStatus.NOT_FOUND


class SubmissionForbidden(AppError):
    default_message = "You do not have access to this submission"
    default_error_code = "submission_forbidden"
    default_status_code = HTTPStatus.FORBIDDEN
