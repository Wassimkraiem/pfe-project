"""FastAPI dependencies for email module."""

from app.email.services import EmailService, get_email_service


def get_email_service_dependency() -> EmailService:
    """
    FastAPI dependency for getting the email service.

    Returns:
        The EmailService instance.
    """
    return get_email_service()
