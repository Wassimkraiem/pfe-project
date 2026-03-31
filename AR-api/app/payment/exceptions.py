from http import HTTPStatus

from app.exceptionhandler import AppError


class InvalidWebhookSignature(AppError):
    default_message = "Invalid webhook signature"
    default_error_code = "invalid_webhook_signature"
    default_status_code = HTTPStatus.FORBIDDEN


class WebhookProcessingError(AppError):
    default_message = "Error processing webhook"
    default_error_code = "webhook_processing_error"
    default_status_code = HTTPStatus.INTERNAL_SERVER_ERROR


class PaymentNotFound(AppError):
    default_message = "Payment not found"
    default_error_code = "payment_not_found"
    default_status_code = HTTPStatus.NOT_FOUND


class PaymentProviderError(AppError):
    default_message = "Payment provider error"
    default_error_code = "payment_provider_error"
    default_status_code = HTTPStatus.BAD_GATEWAY
