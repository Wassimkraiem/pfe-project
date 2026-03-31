"""Email service for rendering MJML templates and sending emails."""

import logging
import re
import uuid
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any

import aiosmtplib
from app.db.database import async_engine
from app.email.queries import (
    get_account_setup_reminder_email_recipients,
    get_pre_payment_reminder_email_recipients,
    record_onboarding_email_sent,
)
from jinja2 import Environment, FileSystemLoader, TemplateNotFound
from mjml import mjml2html

from app.core.config import settings
from app.email.exceptions import (
    EmailSendError,
    MJMLConversionError,
    TemplateNotFoundError,
    TemplateRenderError,
)
from app.email.enums import EmailStatus, OnboardingEmailCode
from app.email.schemas import (
    CustomQuoteCreatedEmailData,
    CustomQuotePriceSubmittedEmailData,
    CustomQuoteTeamNotificationEmailData,
    EmailAttachment,
    EmailMessage,
    EmailRecipient,
    EmailSendResult,
    PaymentIssueEmailData,
    PaymentSuccessEmailData,
    PrePaymentReminderEmailData,
    SetupAccountEmailData,
    WelcomeEmailData,
)

logger = logging.getLogger(__name__)

# Template directory path
TEMPLATES_DIR = Path(__file__).parent / "templates"
COMPONENTS_DIR = TEMPLATES_DIR / "components"


class EmailTemplateRenderer:
    """Handles MJML template rendering with Jinja2."""

    def __init__(self, templates_dir: Path = TEMPLATES_DIR) -> None:
        """
        Initialize the template renderer.

        Args:
            templates_dir: Path to the templates directory.
        """
        self.templates_dir = templates_dir
        self.components_dir = templates_dir / "components"
        self._jinja_env = Environment(
            loader=FileSystemLoader(str(templates_dir)),
            autoescape=True,
        )

    def _load_component(self, component_name: str) -> str:
        """
        Load a reusable MJML component.

        Args:
            component_name: Name of the component file (without .mjml extension).

        Returns:
            The component content as a string.

        Raises:
            TemplateNotFoundError: If the component file doesn't exist.
        """
        component_path = self.components_dir / f"{component_name}.mjml"
        if not component_path.exists():
            raise TemplateNotFoundError(f"components/{component_name}.mjml")
        return component_path.read_text()

    def render_mjml_template(
        self,
        template_name: str,
        context: dict[str, Any],
    ) -> str:
        """
        Render an MJML template with Jinja2 and convert to HTML.

        Args:
            template_name: Name of the template file (without .mjml extension).
            context: Dictionary of variables to pass to the template.

        Returns:
            The rendered HTML string.

        Raises:
            TemplateNotFoundError: If the template doesn't exist.
            TemplateRenderError: If Jinja2 rendering fails.
            MJMLConversionError: If MJML to HTML conversion fails.
        """
        # Load base components
        base_context = {
            "head_content": self._load_component("head"),
            "header_content": self._load_component("header"),
            "footer_content": self._load_component("footer"),
            **context,
        }

        # Load and render Jinja2 template
        try:
            template = self._jinja_env.get_template(f"{template_name}.mjml")
            rendered_mjml = template.render(**base_context)
        except TemplateNotFound as exc:
            logger.error("Template not found: %s", template_name)
            raise TemplateNotFoundError(template_name) from exc
        except Exception as exc:
            logger.error("Failed to render template %s: %s", template_name, exc)
            raise TemplateRenderError(template_name, str(exc)) from exc

        # Convert MJML to HTML
        try:
            html = mjml2html(rendered_mjml)
            return html
        except Exception as exc:
            logger.error("MJML conversion failed for %s: %s", template_name, exc)
            raise MJMLConversionError(str(exc)) from exc


class EmailService:
    """
    Service for composing and sending emails via SMTP.

    Uses aiosmtplib for async SMTP communication.
    Configured for AWS SES SMTP or any standard SMTP server.
    """

    def __init__(self) -> None:
        """Initialize the email service."""
        self._renderer = EmailTemplateRenderer()

    def _is_configured(self) -> bool:
        """Check if SMTP is properly configured."""
        return bool(
            settings.SMTP_HOST
            and settings.SMTP_USERNAME
            and settings.SMTP_PASSWORD
        )

    def _create_text_body(self, html_body: str) -> str:
        """
        Create a plain text version of the email body.

        Args:
            html_body: The HTML content.

        Returns:
            A simplified plain text version.
        """
        text = re.sub(r"<[^>]+>", "", html_body)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def _build_mime_message(self, message: EmailMessage) -> MIMEMultipart:
        """
        Build a MIME message from EmailMessage.

        When attachments are present the structure is multipart/mixed with the
        text/html alternatives nested inside, followed by each attachment.
        Without attachments a simple multipart/alternative is used.

        Args:
            message: The email message data.

        Returns:
            A MIMEMultipart message ready to send.
        """
        if message.attachments:
            outer = MIMEMultipart("mixed")
        else:
            outer = MIMEMultipart("alternative")

        outer["Subject"] = message.subject
        outer["From"] = f"{settings.EMAIL_SENDER_NAME} <{settings.EMAIL_SENDER}>"
        if message.recipient.name:
            outer["To"] = f"{message.recipient.name} <{message.recipient.email}>"
        else:
            outer["To"] = message.recipient.email

        if message.bcc:
            outer["Bcc"] = ", ".join(message.bcc)

        if message.attachments:
            alt = MIMEMultipart("alternative")
            if message.text_body:
                alt.attach(MIMEText(message.text_body, "plain", "utf-8"))
            alt.attach(MIMEText(message.html_body, "html", "utf-8"))
            outer.attach(alt)

            import email.encoders as encoders  # noqa: PLC0415

            for attachment in message.attachments:
                main_type, sub_type = attachment.mime_type.split("/", 1)
                part = MIMEBase(main_type, sub_type)
                part.set_payload(attachment.content)
                encoders.encode_base64(part)
                part.add_header(
                    "Content-Disposition",
                    "attachment",
                    filename=attachment.filename,
                )
                outer.attach(part)
        else:
            if message.text_body:
                outer.attach(MIMEText(message.text_body, "plain", "utf-8"))
            outer.attach(MIMEText(message.html_body, "html", "utf-8"))

        return outer

    def compose_setup_account_email(
        self,
        recipient: EmailRecipient,
        data: SetupAccountEmailData,
        email_code: OnboardingEmailCode | None = None,
    ) -> EmailMessage:
        """
        Compose a setup account email.

        Args:
            recipient: The email recipient.
            data: The template data.

        Returns:
            A composed EmailMessage ready to be sent.
        """
        template_name = "setup_account"
        subject = "Almost done! Finish your account setup"
        if email_code == OnboardingEmailCode.ALREADY_PAID_ONBOARDING:
            template_name = "already_paid_onboarding"
            subject = "Action Needed: Existing Subscription Found"

        html_body = self._renderer.render_mjml_template(
            template_name,
            data.model_dump(),
        )

        return EmailMessage(
            recipient=recipient,
            subject=subject,
            html_body=html_body,
            text_body=self._create_text_body(html_body),
        )

    def compose_pre_payment_reminder_email(
        self,
        recipient: EmailRecipient,
        data: PrePaymentReminderEmailData,
    ) -> EmailMessage:
        """
        Compose a pre-payment drop-off reminder email.

        Args:
            recipient: The email recipient.
            data: The template data.

        Returns:
            A composed EmailMessage ready to be sent.
        """
        html_body = self._renderer.render_mjml_template(
            "pre_payment_reminder",
            data.model_dump(),
        )

        return EmailMessage(
            recipient=recipient,
            subject="Complete Your BVIRAL Subscription",
            html_body=html_body,
            text_body=self._create_text_body(html_body),
        )

    def compose_custom_quote_created_email(
        self,
        recipient: EmailRecipient,
        data: CustomQuoteCreatedEmailData,
    ) -> EmailMessage:
        """
        Compose the custom quote created email.
        """
        html_body = self._renderer.render_mjml_template(
            "custom_quote_created",
            data.model_dump(),
        )

        return EmailMessage(
            recipient=recipient,
            subject="Quote Request Received",
            html_body=html_body,
            text_body=self._create_text_body(html_body),
        )

    def compose_custom_quote_team_notification_email(
        self,
        recipient: EmailRecipient,
        data: CustomQuoteTeamNotificationEmailData,
    ) -> EmailMessage:
        """
        Compose the custom quote team notification email.
        """
        html_body = self._renderer.render_mjml_template(
            "custom_quote_team_notification",
            data.model_dump(),
        )

        return EmailMessage(
            recipient=recipient,
            subject="New Custom Quote Submitted",
            html_body=html_body,
            text_body=self._create_text_body(html_body),
        )

    def compose_custom_quote_price_submitted_email(
        self,
        recipient: EmailRecipient,
        data: CustomQuotePriceSubmittedEmailData,
    ) -> EmailMessage:
        """
        Compose the custom quote price submitted notification email.
        """
        html_body = self._renderer.render_mjml_template(
            "custom_quote_price_submitted",
            data.model_dump(),
        )
        return EmailMessage(
            recipient=recipient,
            subject="Your Custom Quote Is Ready - Complete Your Subscription",
            html_body=html_body,
            text_body=self._create_text_body(html_body),
        )

    def compose_payment_success_email(
        self,
        recipient: EmailRecipient,
        data: PaymentSuccessEmailData,
        attachments: list[EmailAttachment] | None = None,
    ) -> EmailMessage:
        """
        Compose a payment success confirmation email.

        Args:
            recipient: The email recipient.
            data: The template data.
            attachments: Optional list of file attachments (e.g. signed agreement PDF).

        Returns:
            A composed EmailMessage ready to be sent.
        """
        html_body = self._renderer.render_mjml_template(
            "payment_success",
            data.model_dump(),
        )

        bcc_list: list[str] = []
        if settings.PAYMENT_CONFIRMATION_BCC_EMAIL:
            bcc_list.append(settings.PAYMENT_CONFIRMATION_BCC_EMAIL)

        return EmailMessage(
            recipient=recipient,
            subject="Confirmation: BVIRAL Subscription",
            html_body=html_body,
            text_body=self._create_text_body(html_body),
            attachments=attachments or [],
            bcc=bcc_list,
        )

    def compose_payment_issue_email(
        self,
        recipient: EmailRecipient,
        data: PaymentIssueEmailData,
    ) -> EmailMessage:
        """
        Compose a payment processing issue email.

        Args:
            recipient: The email recipient.
            data: The template data.

        Returns:
            A composed EmailMessage ready to be sent.
        """
        html_body = self._renderer.render_mjml_template(
            "payment_issue",
            data.model_dump(),
        )
        return EmailMessage(
            recipient=recipient,
            subject="Payment Processing Issue - BVIRAL Support",
            html_body=html_body,
            text_body=self._create_text_body(html_body),
        )

    async def send_email(self, message: EmailMessage) -> EmailSendResult:
        """
        Send an email message via SMTP.

        Args:
            message: The email message to send.

        Returns:
            EmailSendResult indicating success or failure.

        Raises:
            EmailSendError: If sending fails.
        """
        if not self._is_configured():
            logger.warning(
                "SMTP not configured. Email to %s not sent (subject: %s)",
                message.recipient.email,
                message.subject,
            )
            return EmailSendResult(
                success=False,
                error="SMTP not configured",
            )

        mime_message = self._build_mime_message(message)
        message_id = str(uuid.uuid4())

        try:
            await aiosmtplib.send(
                mime_message,
                hostname=settings.SMTP_HOST,
                port=settings.SMTP_PORT,
                username=settings.SMTP_USERNAME,
                password=settings.SMTP_PASSWORD,
                start_tls=settings.SMTP_USE_TLS,
            )

            logger.info(
                "Email sent successfully to %s (message_id: %s)",
                message.recipient.email,
                message_id,
            )

            return EmailSendResult(
                success=True,
                message_id=message_id,
            )

        except aiosmtplib.SMTPException as exc:
            logger.error(
                "SMTP error sending email to %s: %s",
                message.recipient.email,
                exc,
            )
            raise EmailSendError(message.recipient.email, str(exc)) from exc
        except Exception as exc:
            logger.error(
                "Unexpected error sending email to %s: %s",
                message.recipient.email,
                exc,
            )
            raise EmailSendError(message.recipient.email, str(exc)) from exc

    async def send_setup_account_email(
        self,
        recipient_email: str,
        first_name: str,
        complete_account_link: str,
        recipient_name: str | None = None,
        email_code: OnboardingEmailCode | None = None,
    ) -> EmailSendResult:
        """
        Send an email to users who haven't completed their account setup.

        Args:
            recipient_email: The recipient's email address.
            first_name: First name of the user.
            complete_account_link: Link to complete account setup.
            recipient_name: Full name (optional).

        Returns:
            EmailSendResult indicating success or failure.
        """
        recipient = EmailRecipient(email=recipient_email, name=recipient_name)
        data = SetupAccountEmailData(
            first_name=first_name,
            complete_account_link=complete_account_link,
        )

        message = self.compose_setup_account_email(
            recipient=recipient,
            data=data,
            email_code=email_code,
        )
        return await self.send_email(message)

    async def send_welcome_email(
        self,
        recipient_email: str,
        first_name: str,
        recipient_name: str | None = None,
        assignee_link: str | None = None,
    ) -> EmailSendResult:
        """
        Send a welcome email to a new user.

        Args:
            recipient_email: The recipient's email address.
            first_name: First name of the user.
            recipient_name: Full name (optional).
            assignee_link: Optional link to copyright assignment form.

        Returns:
            EmailSendResult indicating success or failure.
        """
        recipient = EmailRecipient(email=recipient_email, name=recipient_name)
        data = WelcomeEmailData(
            first_name=first_name,
            dashboard_link=f"{settings.FRONTEND_URL.rstrip('/')}/signin",
            assignee_link=assignee_link,
        )

        html_body = self._renderer.render_mjml_template(
            "welcome",
            data.model_dump(),
        )

        attachments: list[EmailAttachment] = []
        get_started_guide_path = Path(__file__).parent / "assets" / "get_started_guide.pdf"
        if get_started_guide_path.exists():
            try:
                pdf_bytes = get_started_guide_path.read_bytes()
                attachments.append(
                    EmailAttachment(
                        filename="BVIRAL_Get_Started_Guide.pdf",
                        content=pdf_bytes,
                        mime_type="application/pdf",
                    )
                )
            except Exception:
                logger.exception(
                    "Failed to read get started guide PDF; sending email without attachment."
                )

        message = EmailMessage(
            recipient=recipient,
            subject="Welcome to BVIRAL",
            html_body=html_body,
            text_body=self._create_text_body(html_body),
            attachments=attachments,
        )
        return await self.send_email(message)

    async def send_pre_payment_reminder_email(
        self,
        recipient_email: str,
        first_name: str,
        resume_link: str,
        recipient_name: str | None = None,
    ) -> EmailSendResult:
        """
        Send a pre-payment drop-off reminder email.

        Args:
            recipient_email: The recipient's email address.
            first_name: First name of the user.
            resume_link: Link to resume checkout/onboarding.
            recipient_name: Full name (optional).

        Returns:
            EmailSendResult indicating success or failure.
        """
        recipient = EmailRecipient(email=recipient_email, name=recipient_name)
        data = PrePaymentReminderEmailData(
            first_name=first_name,
            resume_link=resume_link,
        )

        message = self.compose_pre_payment_reminder_email(recipient, data)
        return await self.send_email(message)

    async def send_custom_quote_created_email(
        self,
        recipient_email: str,
        first_name: str,
        recipient_name: str | None = None,
    ) -> EmailSendResult:
        """
        Send an email confirming the custom quote was created.
        """
        recipient = EmailRecipient(email=recipient_email, name=recipient_name)
        data = CustomQuoteCreatedEmailData(first_name=first_name)

        message = self.compose_custom_quote_created_email(recipient, data)
        return await self.send_email(message)

    async def send_custom_quote_team_notification_email(
        self,
        submitter_email: str,
        channels: list[str],
        triggers: list[dict],
    ) -> EmailSendResult:
        """
        Send a custom quote notification email to the team.
        """
        recipient = EmailRecipient(email=settings.CUSTOM_QUOTE_TEAM_EMAIL)
        data = CustomQuoteTeamNotificationEmailData(
            submitter_email=submitter_email,
            channels=channels,
            triggers=triggers,
        )
        message = self.compose_custom_quote_team_notification_email(recipient, data)
        return await self.send_email(message)

    async def send_custom_quote_price_submitted_email(
        self,
        recipient_email: str,
        first_name: str,
        finish_link: str,
        recipient_name: str | None = None,
    ) -> EmailSendResult:
        """
        Send an email notifying the user that a price has been submitted for their custom quote.
        """
        recipient = EmailRecipient(email=recipient_email, name=recipient_name)
        data = CustomQuotePriceSubmittedEmailData(
            first_name=first_name,
            finish_link=finish_link,
        )
        message = self.compose_custom_quote_price_submitted_email(recipient, data)
        return await self.send_email(message)

    async def send_payment_success_email(
        self,
        recipient_email: str,
        first_name: str,
        complete_account_link: str,
        recipient_name: str | None = None,
        channels: list[str] | None = None,
        amount_display: str = "",
        plan_label: str = "",
        signature: str | None = None,
        signed_at: str | None = None,
    ) -> EmailSendResult:
        """
        Send a payment success confirmation email.

        The email body includes the signatory details, electronic signature,
        whitelisted channels, and fee breakdown. The base agreement PDF
        (``app/email/assets/service_agreement.pdf``) is attached with a
        signature page appended containing the signatory details.

        Args:
            recipient_email: The recipient's email address.
            first_name: First name of the user.
            complete_account_link: Link to complete account setup.
            recipient_name: Full name (optional).
            channels: Whitelisted channel URLs from the onboarding session.
            amount_display: Human-readable fee string, e.g. "$1,200.00 USD".
            plan_label: Plan name, e.g. "Monthly" or "Yearly".
            signature: Electronic signature text captured before checkout.
            signed_at: ISO timestamp when the agreement was signed.
        """
        from app.email.pdf import SignatureData, create_signed_agreement_pdf  # noqa: PLC0415

        recipient = EmailRecipient(email=recipient_email, name=recipient_name)
        data = PaymentSuccessEmailData(
            first_name=first_name,
            complete_account_link=complete_account_link,
            channels=channels or [],
            amount_display=amount_display,
            plan_label=plan_label,
            customer_email=recipient_email,
            signature=signature or "",
            signed_at=signed_at or "",
        )

        attachments: list[EmailAttachment] = []
        try:
            sig_data = SignatureData(
                signature=signature or "",
                signed_at=signed_at or "",
                customer_email=recipient_email,
                channels=channels or [],
            )
            pdf_bytes = create_signed_agreement_pdf(sig_data)
            if pdf_bytes:
                attachments.append(
                    EmailAttachment(
                        filename="BVIRAL_Licensing_Agreement.pdf",
                        content=pdf_bytes,
                        mime_type="application/pdf",
                    )
                )
        except Exception:
            logger.exception(
                "Failed to create signed agreement PDF; sending email without attachment."
            )

        message = self.compose_payment_success_email(recipient, data, attachments=attachments)
        return await self.send_email(message)

    async def send_payment_issue_email(
        self,
        recipient_email: str,
        first_name: str,
        recipient_name: str | None = None,
    ) -> EmailSendResult:
        """
        Send a payment processing issue email.

        Args:
            recipient_email: The recipient's email address.
            first_name: First name of the user.
            recipient_name: Full name (optional).

        Returns:
            EmailSendResult indicating success or failure.
        """
        recipient = EmailRecipient(email=recipient_email, name=recipient_name)
        data = PaymentIssueEmailData(first_name=first_name)
        message = self.compose_payment_issue_email(recipient, data)
        return await self.send_email(message)


# Singleton instance for dependency injection
_email_service: EmailService | None = None


def get_email_service() -> EmailService:
    """
    Get the email service singleton instance.

    Returns:
        The EmailService instance.
    """
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service


async def send_pre_payment_reminder_email() -> EmailSendResult | None:
    """
    Send a pre-payment drop-off reminder email.
    """
    try:
        recipients = await get_pre_payment_reminder_email_recipients()
        email_service = get_email_service()
        last_result: EmailSendResult | None = None
        for recipient in recipients:
            first_name = recipient.email.split("@")[0]
            resume_link = f"{settings.FRONTEND_URL}/signup?session_id={recipient.session_uuid}"
            last_result = await email_service.send_pre_payment_reminder_email(
                recipient_email=recipient.email,
                first_name=first_name,
                resume_link=resume_link,
                recipient_name=None,
            )
            await record_onboarding_email_sent(
                session_uuid=recipient.session_uuid,
                recipient_email=recipient.email,
                email_code=OnboardingEmailCode.PRE_PAYMENT_REMINDER,
                status=EmailStatus.SENT,
            )
        return last_result
    finally:
        await async_engine.dispose()


async def send_account_setup_reminder_email() -> EmailSendResult | None:
    """
    Send an account setup reminder email to users who paid but haven't completed setup.
    """
    try:
        recipients = await get_account_setup_reminder_email_recipients()
        email_service = get_email_service()
        last_result: EmailSendResult | None = None
        for recipient in recipients:
            first_name = recipient.email.split("@")[0]
            complete_account_link = (
                f"{settings.FRONTEND_URL}/signup?session_id={recipient.session_uuid}"
            )
            last_result = await email_service.send_setup_account_email(
                recipient_email=recipient.email,
                first_name=first_name,
                complete_account_link=complete_account_link,
                recipient_name=None,
                email_code=OnboardingEmailCode.ACCOUNT_SETUP_REMINDER,
            )
            await record_onboarding_email_sent(
                session_uuid=recipient.session_uuid,
                recipient_email=recipient.email,
                email_code=OnboardingEmailCode.ACCOUNT_SETUP_REMINDER,
                status=EmailStatus.SENT,
            )
        return last_result
    finally:
        await async_engine.dispose()
