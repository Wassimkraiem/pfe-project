from http import HTTPStatus
from app.exceptionhandler import AppError


class OnboardingSessionNotFound(AppError):
    default_message = "Onboarding session not found"
    default_error_code = "onboarding_session_not_found"
    default_status_code = HTTPStatus.NOT_FOUND


class OnboardingSessionAlreadyExists(AppError):
    default_message = "this email is already in use"
    default_error_code = "onboarding_session_already_exists"
    default_status_code = HTTPStatus.BAD_REQUEST


class InvalidMagicToken(AppError):
    default_message = "Invalid or expired magic token"
    default_error_code = "invalid_magic_token"
    default_status_code = HTTPStatus.BAD_REQUEST


class OnboardingSessionExpired(AppError):
    default_message = "Magic token has expired"
    default_error_code = "magic_token_expired"
    default_status_code = HTTPStatus.BAD_REQUEST


class DuplicateChannelURL(AppError):
    default_message = "Channel URL already exists"
    default_error_code = "duplicate_channel_url"
    default_status_code = HTTPStatus.BAD_REQUEST

class CustomQuoteAlreadySubmitted(AppError):
    default_message = "A custom quote is already submitted for this account, please check your email to finish the process."
    default_error_code = "custom_quote_already_submitted"
    default_status_code = HTTPStatus.BAD_REQUEST

class EmailSentToCompleteProcess(AppError):
    default_message = "An email has been sent to you to complete the account setup process"
    default_error_code = "email_sent_to_complete_process"
    default_status_code = HTTPStatus.BAD_REQUEST

class NotInCustomQuoteFlow(AppError):
    default_message = "You are not in the custom quote flow"
    default_error_code = "not_in_custom_quote_flow"
    default_status_code = HTTPStatus.BAD_REQUEST