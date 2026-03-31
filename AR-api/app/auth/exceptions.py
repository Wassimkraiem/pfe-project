from http import HTTPStatus

from app.exceptionhandler import AppError


class InvalidCredentials(AppError):
    """Raised when email or password is incorrect."""

    default_message = "Invalid email or password"
    default_error_code = "invalid_credentials"
    default_status_code = HTTPStatus.UNAUTHORIZED


class UserNotActive(AppError):
    """Raised when user account is deactivated."""

    default_message = "User account is not active"
    default_error_code = "user_not_active"
    default_status_code = HTTPStatus.FORBIDDEN


class ClerkAuthenticationError(AppError):
    """Raised when Clerk authentication fails."""

    default_message = "Authentication service error"
    default_error_code = "clerk_auth_error"
    default_status_code = HTTPStatus.INTERNAL_SERVER_ERROR


class AdminRoleRequired(AppError):
    """Raised when endpoint requires admin role."""

    default_message = "Admin role is required"
    default_error_code = "admin_role_required"
    default_status_code = HTTPStatus.FORBIDDEN
