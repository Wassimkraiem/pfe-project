"""Email-related exceptions."""


class EmailError(Exception):
    """Base exception for email-related errors."""

    pass


class TemplateNotFoundError(EmailError):
    """Raised when an email template is not found."""

    def __init__(self, template_name: str) -> None:
        self.template_name = template_name
        super().__init__(f"Email template not found: {template_name}")


class TemplateRenderError(EmailError):
    """Raised when template rendering fails."""

    def __init__(self, template_name: str, reason: str) -> None:
        self.template_name = template_name
        self.reason = reason
        super().__init__(f"Failed to render template '{template_name}': {reason}")


class MJMLConversionError(EmailError):
    """Raised when MJML to HTML conversion fails."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(f"MJML conversion failed: {reason}")


class EmailSendError(EmailError):
    """Raised when email sending fails."""

    def __init__(self, recipient: str, reason: str) -> None:
        self.recipient = recipient
        self.reason = reason
        super().__init__(f"Failed to send email to '{recipient}': {reason}")
