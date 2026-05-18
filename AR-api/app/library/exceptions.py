from http import HTTPStatus

from app.exceptionhandler import AppError


class LibraryVideoNotFound(AppError):
    default_message = "Library video not found"
    default_error_code = "library_video_not_found"
    default_status_code = HTTPStatus.NOT_FOUND


class LibraryCategoryNotFound(AppError):
    default_message = "Unknown library category"
    default_error_code = "library_category_not_found"
    default_status_code = HTTPStatus.NOT_FOUND


class LibraryProviderError(AppError):
    default_message = "Library provider request failed"
    default_error_code = "library_provider_error"
    default_status_code = HTTPStatus.BAD_GATEWAY


class LibraryInvalidFilter(AppError):
    default_message = "Invalid library filter"
    default_error_code = "library_invalid_filter"
    default_status_code = HTTPStatus.BAD_REQUEST

