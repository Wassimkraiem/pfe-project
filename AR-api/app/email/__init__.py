"""Email module for sending templated emails using MJML."""

from app.email.services import EmailService

__all__ = ["EmailService"]
from app.email.models import OnboardingEmailModel  # noqa: F401
from app.email.enums import OnboardingEmailCode, EmailStatus  # noqa: F401
