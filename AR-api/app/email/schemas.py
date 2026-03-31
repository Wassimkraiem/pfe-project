"""Pydantic schemas for email module."""

from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class EmailRecipient(BaseModel):
    """Email recipient details."""

    email: EmailStr
    name: str | None = None


class PrePaymentReminderRecipientSchema(BaseModel):
    """Recipient data for pre-payment reminder email."""

    email: str
    session_uuid: UUID


class AccountSetupReminderRecipientSchema(BaseModel):
    """Recipient data for account setup reminder email."""

    email: str
    session_uuid: UUID


class SetupAccountEmailData(BaseModel):
    """Data for the setup account email."""

    first_name: str
    complete_account_link: str


class WelcomeEmailData(BaseModel):
    """Data required for the welcome email template."""

    first_name: str
    dashboard_link: str
    assignee_link: str | None = None  # Optional: copyright assignment link


class PrePaymentReminderEmailData(BaseModel):
    """Data for pre-payment drop-off reminder email."""

    first_name: str
    resume_link: str


class PaymentSuccessEmailData(BaseModel):
    """Data for payment success confirmation email."""

    first_name: str
    complete_account_link: str
    channels: list[str] = Field(default_factory=list)
    amount_display: str = ""
    plan_label: str = ""
    customer_email: str = ""
    signature: str = ""
    signed_at: str = ""


class PaymentIssueEmailData(BaseModel):
    """Data for payment processing issue email (e.g. session not found)."""

    first_name: str


class CustomQuoteCreatedEmailData(BaseModel):
    """Data for custom quote created email."""

    first_name: str


class CustomQuoteTeamNotificationEmailData(BaseModel):
    """Data for custom quote team notification email."""

    submitter_email: EmailStr
    channels: list[str]
    triggers: list[dict]


class CustomQuotePriceSubmittedEmailData(BaseModel):
    """Data for custom quote price submitted notification email."""

    first_name: str
    finish_link: str


class TestEmailRequestSchema(BaseModel):
    """Request schema for testing setup account email."""

    recipient_email: EmailStr
    recipient_name: str | None = None
    first_name: str
    complete_account_link: str


class EmailAttachment(BaseModel):
    """A file attachment to include in an outbound email."""

    filename: str
    content: bytes
    mime_type: str = "application/pdf"

    model_config = {"arbitrary_types_allowed": True}


class EmailMessage(BaseModel):
    """Complete email message ready to be sent."""

    recipient: EmailRecipient
    subject: str
    html_body: str
    text_body: str | None = None
    attachments: list[EmailAttachment] = Field(default_factory=list)
    bcc: list[str] = Field(default_factory=list)


class EmailSendResult(BaseModel):
    """Result of sending an email."""

    success: bool
    message_id: str | None = None
    error: str | None = None
