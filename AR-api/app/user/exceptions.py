from http import HTTPStatus

from app.exceptionhandler import AppError


class EmailAlreadyExists(AppError):
    default_message = "Email already exists"
    default_error_code = "email_already_exists"
    default_status_code = HTTPStatus.CONFLICT


class UserAlreadyExists(AppError):
    default_message = "User with this email already exists"
    default_error_code = "user_already_exists"
    default_status_code = HTTPStatus.CONFLICT


class ClerkUserCreationFailed(AppError):
    default_message = "Failed to create user in authentication service"
    default_error_code = "clerk_user_creation_failed"
    default_status_code = HTTPStatus.BAD_REQUEST


class UserCreationFailed(AppError):
    default_message = "Failed to create user"
    default_error_code = "user_creation_failed"
    default_status_code = HTTPStatus.BAD_REQUEST


class NotFound(AppError):
    default_message = "Not found"
    default_error_code = "not_found"
    default_status_code = HTTPStatus.NOT_FOUND


class UserNotFound(AppError):
    default_message = "User not found"
    default_error_code = "user_not_found"
    default_status_code = HTTPStatus.NOT_FOUND