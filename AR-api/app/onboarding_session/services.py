import asyncio
import logging
from http import HTTPStatus
from urllib.parse import urlparse
from fastapi import Depends
from pydantic import HttpUrl
from sqlalchemy import case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import attributes

from app.channel.enums import Platform, VerificationStatus
from app.channel.schemas import ChannelCreateSchema
from app.channel.services import ChannelService
from app.channel.exceptions import ChannelAlreadyExists
from app.core.config import settings
from app.db.database import get_db
from app.exceptionhandler import AppError
from app.onboarding_session.enums import (
    CustomQuoteTriggerFlag,
    OnboardingStep,
    PaymentFlowType,
)
from app.onboarding_session.exceptions import NotInCustomQuoteFlow
from app.onboarding_session.exceptions import (
    CustomQuoteAlreadySubmitted,
    DuplicateChannelURL,
    OnboardingSessionNotFound,
)
from app.onboarding_session.models import OnboardingSessionModel
from app.onboarding_session.schemas import AccountUpdateRequestSchema, OnboardingSessionOutSchema
from app.sms_sdk import (
    SMSAPIError,
    get_facebook_page_details,
    get_instagram_user_details,
    get_snapchat_user_details,
    get_tiktok_user_details,
    get_twitter_user_details,
    get_youtube_channel_details,
)
from app.payment.enums import PaymentStatus, PaymentType, PlanType
from app.payment.schemas import PaymentCreateSchema
from app.canto.tasks import create_basic_canto_user_task
from app.payment.services import PaymentService
from app.user.schemas import UserCreateSchema
from app.user.services import UserService
from datetime import datetime, timedelta, timezone
import json
from app.auth.clerk_client import clerk_client

logger = logging.getLogger(__name__)




class OnboardingSessionService:
    """Service for onboarding session operations."""

    FOLLOWER_CUSTOM_QUOTE_THRESHOLD = 2000000
    INSTAGRAM_USER_DETAILS_TIMEOUT_SECONDS = 30


    def __init__(self, db: AsyncSession = Depends(get_db)) -> None:
        self.db = db

    def _sanitize_payment_metadata(self, checkout_data: dict) -> dict:
        sanitized = dict(checkout_data or {})
        sanitized.pop("onboarding_session_uuid", None)
        return sanitized

    async def get_by_id(self, session_id: int) -> OnboardingSessionModel | None:
        """Get an onboarding session by ID."""
        result = await self.db.execute(
            select(OnboardingSessionModel).where(OnboardingSessionModel.id == session_id)
        )
        return result.scalar_one_or_none()

    async def delete_by_uuid(self, session_uuid: str) -> None:
        """Delete an onboarding session by UUID."""
        session = await self.get_by_uuid(session_uuid)
        if session:
            await self.db.delete(session)
            await self.db.commit()

    async def get_by_email(self, email: str) -> OnboardingSessionModel | None:
        """Get an onboarding session by email or payment email (case-insensitive)."""
        normalized_email = email.strip().lower() if email else ""
        if not normalized_email:
            return None

        result = await self.db.execute(
            select(OnboardingSessionModel)
            .where(
                or_(
                    func.lower(OnboardingSessionModel.email) == normalized_email,
                    func.lower(OnboardingSessionModel.payment_email) == normalized_email,
                )
            )
            # Prefer direct email matches over payment_email matches, then latest record.
            .order_by(
                case(
                    (func.lower(OnboardingSessionModel.email) == normalized_email, 0),
                    else_=1,
                ),
                OnboardingSessionModel.created_at.desc(),
            )
            .limit(2)
        )
        sessions = list(result.scalars().all())
        if len(sessions) > 1:
            logger.warning(
                "Multiple onboarding sessions matched normalized email '%s'; using id=%s uuid=%s",
                normalized_email,
                sessions[0].id,
                sessions[0].uuid,
            )

        return sessions[0] if sessions else None

    async def get_by_uuid(self, session_uuid: str) -> OnboardingSessionModel | None:
        """Get an onboarding session by UUID."""
        import uuid as uuid_lib
        
        try:
            uuid_obj = uuid_lib.UUID(session_uuid)
        except ValueError:
            return None
        
        result = await self.db.execute(
            select(OnboardingSessionModel).where(OnboardingSessionModel.uuid == uuid_obj)
        )
        return result.scalar_one_or_none()

    async def mark_custom_quote_submitted(self, email: str) -> OnboardingSessionModel:
        """Mark custom quote as submitted for an onboarding session by email."""
        session = await self.get_by_email(email)
        if not session:
            raise OnboardingSessionNotFound(
                message=f"No onboarding session found for email: {email}"
            )
        if session.custom_quote_submitted:
            raise CustomQuoteAlreadySubmitted()
        if not session.requires_custom_quote:
            raise NotInCustomQuoteFlow()
        session.custom_quote_submitted = True
        await self.db.flush()
        await self.db.refresh(session)
        return session

    async def add_channels(
        self,
        email: str,
        channels: list[HttpUrl],
    ) -> OnboardingSessionModel:
        """
        Add channels to an onboarding session, creating the session if it doesn't exist.

        This is the first step of the onboarding flow. If no session exists for the
        email, a new one is created with the provided channels.

        Args:
            email: User email address
            channels: List of channel URLs to add

        Returns:
            Created or updated OnboardingSessionModel

        Raises:
            DuplicateChannelURL: If any URL already exists in the session
            AppError: If session exists but is not in PAGES step
        """
        # Normalize email for consistency
        
        normalized_email = email.strip().lower()

        # Convert channels to strings and normalize (remove trailing slash)
        new_channel_strs = [str(url).rstrip("/") for url in channels]

        # Ensure channels do not already exist in the database
        channel_service = ChannelService(db=self.db)
        existing_urls: list[str] = []
        for url in new_channel_strs:
            if await channel_service.get_by_url(url):
                existing_urls.append(url)
        if existing_urls:
            raise ChannelAlreadyExists(
                message=(
                    "Channel(s) already exist in the system: "
                    + ", ".join(existing_urls)
                )
            )

        # Check whether any channel requires custom quote flow.
        requires_custom_quote, custom_quote_triggers = (
            await self._compute_custom_quote_state(new_channel_strs)
        )

        # Check if session exists
        session = await self.get_by_email(normalized_email)

        if not session:
            # Create new session with channels
            session_details = {
                "pages": {
                    "channels": new_channel_strs,
                    "custom_quote_triggers": custom_quote_triggers,
                },
                "checkout": None,
                "account": None,
            }
            session = OnboardingSessionModel(
                email=normalized_email,
                current_step=OnboardingStep.PAGES,
                payment_received=False,
                requires_custom_quote=requires_custom_quote,
                session_details=session_details,
            )
            self.db.add(session)
            await self.db.flush()
            await self.db.refresh(session)
            return session

        # Session exists - validate step
        if session.current_step != OnboardingStep.PAGES:
            raise AppError(
                message="Channels can only be added during the PAGES step",
                error_code="invalid_step_for_channels",
                status_code=HTTPStatus.BAD_REQUEST,
            )

        existing_details = dict(session.session_details or {})
        pages_data = existing_details.get("pages", {})
        existing_channels = pages_data.get("channels", [])

        # Normalize existing channels for comparison
        existing_normalized = [ch.rstrip("/") for ch in existing_channels]

        # Check for duplicates (compare normalized URLs)
        duplicates = [url for url in new_channel_strs if url in existing_normalized]
        if duplicates:
            raise DuplicateChannelURL(
                message=f"The following URL(s) already exist in your channels: {', '.join(duplicates)}"
            )

        # Merge channels
        updated_channels = existing_channels + new_channel_strs
        pages_data["channels"] = updated_channels
        existing_details["pages"] = pages_data
        session.session_details = existing_details

        # Recompute requires_custom_quote for all channels in session.
        (
            session.requires_custom_quote,
            custom_quote_triggers,
        ) = await self._compute_custom_quote_state(updated_channels)
        pages_data["custom_quote_triggers"] = custom_quote_triggers

        # Flag the JSON column as modified so SQLAlchemy detects the change
        attributes.flag_modified(session, "session_details")

        await self.db.flush()
        await self.db.refresh(session)
        return session

    async def remove_channel(
        self,
        email: str,
        channel: HttpUrl,
    ) -> OnboardingSessionModel:
        """
        Remove a single channel from an onboarding session.

        Args:
            email: User email address
            channel: Channel URL to remove

        Returns:
            Updated OnboardingSessionModel

        Raises:
            OnboardingSessionNotFound: If no session exists for the email
            AppError: If session is not in PAGES step or channel not found
        """
        session = await self.get_by_email(email)
        if not session:
            raise OnboardingSessionNotFound(
                message=f"No onboarding session found for email: {email}"
            )

        if session.current_step != OnboardingStep.PAGES:
            raise AppError(
                message="Channels can only be removed during the PAGES step",
                error_code="invalid_step_for_channels",
                status_code=HTTPStatus.BAD_REQUEST,
            )

        existing_details = dict(session.session_details or {})
        pages_data = existing_details.get("pages", {})
        existing_channels = pages_data.get("channels", [])

        # Normalize URL by removing trailing slash for comparison
        channel_str = str(channel).rstrip("/")

        # Find the channel to remove (normalize stored URLs too for comparison)
        channel_to_remove = None
        for ch in existing_channels:
            if ch.rstrip("/") == channel_str:
                channel_to_remove = ch
                break

        if channel_to_remove is None:
            raise AppError(
                message=f"Channel URL not found: {channel_str}",
                error_code="channel_not_found",
                status_code=HTTPStatus.NOT_FOUND,
            )

        # Remove the channel
        updated_channels = [ch for ch in existing_channels if ch != channel_to_remove]
        pages_data["channels"] = updated_channels
        existing_details["pages"] = pages_data
        session.session_details = existing_details

        # Recompute requires_custom_quote for remaining channels.
        (
            session.requires_custom_quote,
            custom_quote_triggers,
        ) = await self._compute_custom_quote_state(updated_channels)
        pages_data["custom_quote_triggers"] = custom_quote_triggers

        # Flag the JSON column as modified so SQLAlchemy detects the change
        attributes.flag_modified(session, "session_details")

        await self.db.flush()
        await self.db.refresh(session)
        return session

    async def update_account_details_by_uuid(
        self,
        session_uuid: str,
        account_data: AccountUpdateRequestSchema,
    ) -> OnboardingSessionModel:
        """
        Update account details in an onboarding session by UUID.

        Args:
            session_uuid: UUID of the onboarding session
            account_data: Account details to update

        Returns:
            Updated OnboardingSessionModel

        Raises:
            OnboardingSessionNotFound: If no session exists for the UUID
            AppError: If session is not in ACCOUNT step
        """
        session = await self.get_by_uuid(session_uuid)
        if not session:
            raise OnboardingSessionNotFound(
                message=f"No onboarding session found for UUID: {session_uuid}"
            )

        if session.current_step != OnboardingStep.ACCOUNT:
            raise AppError(
                message="Account details can only be updated during the ACCOUNT step",
                error_code="invalid_step_for_account",
                status_code=HTTPStatus.BAD_REQUEST,
            )

        existing_details = dict(session.session_details or {})
        
        # Update account section
        account_dict = account_data.model_dump(mode="json")
        existing_details["account"] = account_dict
        session.session_details = existing_details

        # Flag the JSON column as modified so SQLAlchemy detects the change
        attributes.flag_modified(session, "session_details")

        await self.db.flush()
        await self.db.refresh(session)
        return session

    async def mark_payment_received(
        self,
        webhook_data: dict,
        onboarding_session_uuid: str | None = None,
        signature: str | None = None,
        custom_data: dict | None = None,
    ) -> OnboardingSessionModel:
        """
        Mark payment as received and update checkout data in session_details.

        Extracts payment information from Stripe webhook event objects
        and stores it in the checkout section.

        Args:
            webhook_data: Stripe event data.object payload.
            onboarding_session_uuid: Session UUID from checkout metadata.
            signature: Signature from checkout metadata.
            custom_data: Metadata from checkout session or invoice.
            
        Returns:
            Updated OnboardingSessionModel
            
        Raises:
            OnboardingSessionNotFound: If no matching session exists and cannot be created
        """
        object_type = str(webhook_data.get("object", ""))
        metadata = custom_data or {}
        if object_type == "checkout.session":
            user_email = (
                webhook_data.get("customer_email")
                or (webhook_data.get("customer_details") or {}).get("email")
            )
            invoice_id = str(webhook_data.get("invoice", "") or "")
            subscription_id = str(webhook_data.get("subscription", "") or "")
            amount = int(webhook_data.get("amount_total") or 0)
            currency = (webhook_data.get("currency") or "USD").upper()
            billing_reason = "initial"
            created_at = webhook_data.get("created")
            payment_completed_at = (
                datetime.fromtimestamp(created_at) if isinstance(created_at, int) else datetime.utcnow()
            )
            customer_id = webhook_data.get("customer")
            price_id = self._extract_price_id_from_checkout_session(webhook_data)
        elif object_type == "invoice":
            user_email = webhook_data.get("customer_email")
            invoice_id = str(webhook_data.get("id", "") or "")
            subscription_id = str(webhook_data.get("subscription", "") or "")
            amount = int(webhook_data.get("amount_paid") or webhook_data.get("amount_due") or 0)
            currency = (webhook_data.get("currency") or "USD").upper()
            billing_reason = webhook_data.get("billing_reason")
            created_at = webhook_data.get("created")
            payment_completed_at = (
                datetime.fromtimestamp(created_at) if isinstance(created_at, int) else datetime.utcnow()
            )
            customer_id = webhook_data.get("customer")
            price_id = self._extract_price_id_from_invoice(webhook_data)
        else:
            user_email = webhook_data.get("customer_email")
            invoice_id = str(webhook_data.get("id", "") or "")
            subscription_id = str(webhook_data.get("subscription", "") or "")
            amount = int(webhook_data.get("amount_total") or 0)
            currency = (webhook_data.get("currency") or "USD").upper()
            billing_reason = None
            payment_completed_at = datetime.utcnow()
            customer_id = webhook_data.get("customer")
            price_id = None

        session: OnboardingSessionModel | None = (
            await self.get_by_uuid(onboarding_session_uuid)
            if onboarding_session_uuid
            else None
        )

        if not session and user_email:
            # Invoice events may omit checkout metadata; fall back to payer email
            # so we can update the existing onboarding session instead of creating a new one.
            logger.info(
                "UUID lookup returned no session (uuid=%s), falling back to email lookup: %s",
                onboarding_session_uuid,
                user_email,
            )
            session = await self.get_by_email(user_email)
        if not session:
            # If UUID was explicitly provided but session wasn't found by UUID or email,
            # fail without creating a new session (strict UUID lookup requirement).
            if onboarding_session_uuid:
                raise OnboardingSessionNotFound(
                    message=(
                        "No onboarding session found for webhook identifier "
                        f"(uuid={onboarding_session_uuid}, email={user_email})"
                    )
                )
            # No UUID provided and email lookup failed - create a new session as fallback.
            channels = []
            if metadata:
                raw_channels = metadata.get("channels")
                if isinstance(raw_channels, str):
                    try:
                        raw_channels = json.loads(raw_channels)
                    except json.JSONDecodeError:
                        raw_channels = []
                if isinstance(raw_channels, list):
                    channels = [str(ch).rstrip("/") for ch in raw_channels]
            if not user_email:
                raise OnboardingSessionNotFound(
                    message=(
                        "No onboarding session found for webhook identifier "
                        f"(uuid={onboarding_session_uuid})"
                    )
                )
            requires_custom_quote, custom_quote_triggers = (
                await self._compute_custom_quote_state(channels)
            )
            session_details = {
                "pages": {
                    "channels": channels,
                    "custom_quote_triggers": custom_quote_triggers,
                },
                "checkout": None,
                "account": None,
            }
            session = OnboardingSessionModel(
                email=user_email.strip().lower(),
                current_step=OnboardingStep.ACCOUNT,
                payment_received=True,
                requires_custom_quote=requires_custom_quote,
                session_details=session_details,
            )
            self.db.add(session)
            await self.db.flush()
            await self.db.refresh(session)

        if user_email:
            normalized_payment_email = user_email.strip().lower()
            session.payment_email = normalized_payment_email

        # Get existing session_details or initialize
        existing_details = dict(session.session_details or {})
        
        # Get existing checkout data to preserve checkout fields captured earlier.
        existing_checkout = existing_details.get("checkout") or {}
        
        # Preserve fields set during checkout creation.
        existing_price_id = (
            existing_checkout.get("price_id") if isinstance(existing_checkout, dict) else None
        )
        existing_service_agreement_signed_at = (
            existing_checkout.get("service_agreement_signed_at")
            if isinstance(existing_checkout, dict)
            else None
        )
        payment_flow_type = (
            existing_checkout.get("payment_flow_type")
            if isinstance(existing_checkout, dict)
            else None
        )

        pages_data = existing_details.get("pages", {}) if isinstance(existing_details, dict) else {}
        channels = pages_data.get("channels", []) if isinstance(pages_data, dict) else []

        # Update checkout section with webhook payment data
        checkout_data = {
            # Preserved from checkout creation
            "price_id": price_id or existing_price_id,
            "payment_flow_type": payment_flow_type,
            "service_agreement_signed_at": (
                metadata.get("service_agreement_signed_at")
                or existing_service_agreement_signed_at
            ),
            # From webhook
            "invoice_id": invoice_id,
            "subscription_id": subscription_id,
            "amount": amount,
            "currency": currency,
            "payment_completed_at": payment_completed_at.isoformat(),
            "billing_reason": billing_reason,
            "user_email": user_email,
            "onboarding_session_uuid": onboarding_session_uuid or str(session.uuid),
            "channels": channels,
        }
        if customer_id is not None:
            checkout_data["customer_id"] = str(customer_id)
        if signature:
            checkout_data["signature"] = signature

        existing_details["checkout"] = checkout_data
        
        # Update session fields
        session.payment_received = True
        session.session_details = existing_details

        # Flag all modified columns so SQLAlchemy detects the changes
        attributes.flag_modified(session, "session_details")
        attributes.flag_modified(session, "payment_received")
        if session.current_step != OnboardingStep.COMPLETED:
            session.current_step = OnboardingStep.ACCOUNT
            attributes.flag_modified(session, "current_step")
        else:
            logger.info(
                "Preserving completed onboarding step for session uuid=%s on payment webhook update",
                session.uuid,
            )

        await self.db.flush()
        await self.db.refresh(session)

        return session

    async def set_checkout_payment_flow_type(
        self,
        email: str,
        payment_flow_type: PaymentFlowType,
        price_id: str,
        signature: str | None = None,
        service_agreement_signed_at: str | None = None,
    ) -> OnboardingSessionModel:
        """
        Set the payment flow type and Stripe price ID for an onboarding session's checkout.

        This should be called before creating a checkout URL to track whether
        the user is going through a regular subscription or custom quote flow.

        Args:
            email: User email
            payment_flow_type: Type of payment flow (subscription or custom_quote)
            price_id: Stripe price ID used in checkout
            signature: Service agreement signature captured before checkout
            service_agreement_signed_at: ISO timestamp when signature was captured

        Returns:
            Updated OnboardingSessionModel

        Raises:
            OnboardingSessionNotFound: If no session exists for the email
        """
        session = await self.get_by_email(email)
        if not session:
            raise OnboardingSessionNotFound(
                message=f"No onboarding session found for email: {email}"
            )

        existing_details = dict(session.session_details or {})
        existing_checkout = existing_details.get("checkout") or {}

        if isinstance(existing_checkout, dict):
            existing_checkout["payment_flow_type"] = payment_flow_type.value
            existing_checkout["price_id"] = price_id
            if signature is not None:
                existing_checkout["signature"] = signature
            if service_agreement_signed_at is not None:
                existing_checkout["service_agreement_signed_at"] = (
                    service_agreement_signed_at
                )
        else:
            existing_checkout = {
                "payment_flow_type": payment_flow_type.value,
                "price_id": price_id,
            }
            if signature is not None:
                existing_checkout["signature"] = signature
            if service_agreement_signed_at is not None:
                existing_checkout["service_agreement_signed_at"] = (
                    service_agreement_signed_at
                )

        existing_details["checkout"] = existing_checkout
        session.session_details = existing_details

        attributes.flag_modified(session, "session_details")

        await self.db.flush()
        await self.db.refresh(session)
        return session

    async def set_custom_quote_price_by_email(
        self,
        email: str,
        price_id: str,
    ) -> OnboardingSessionModel:
        """
        Set a Stripe price ID for a custom quote onboarding session.

        Args:
            email: User email
            price_id: Stripe price ID for the custom quote

        Returns:
            Updated OnboardingSessionModel

        Raises:
            OnboardingSessionNotFound: If no session exists for the email
            AppError: If session is not in custom quote flow or is already paid
        """
        session = await self.get_by_email(email)
        if not session:
            raise OnboardingSessionNotFound(
                message=f"No onboarding session found for email: {email}"
            )

        if not session.custom_quote_submitted:
            raise NotInCustomQuoteFlow()

        if session.payment_received:
            raise AppError(
                message="Payment already received for this onboarding session",
                error_code="payment_already_received",
                status_code=HTTPStatus.BAD_REQUEST,
            )

        session.price_id = price_id.strip()

        attributes.flag_modified(session, "price_id")

        await self.db.flush()
        await self.db.refresh(session)
        return session

    async def get_pending_custom_quotes(self) -> list[OnboardingSessionModel]:
        """
        List onboarding sessions pending custom quote price.

        Returns sessions where custom quote was submitted, price_id is not yet set,
        and payment is not received.
        """
        result = await self.db.execute(
            select(OnboardingSessionModel)
            .where(
                OnboardingSessionModel.custom_quote_submitted.is_(True),
                OnboardingSessionModel.payment_received.is_(False),
                or_(
                    OnboardingSessionModel.price_id.is_(None),
                    OnboardingSessionModel.price_id == "",
                ),
            )
            .order_by(OnboardingSessionModel.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_custom_quotes_pending_payment(self) -> list[OnboardingSessionModel]:
        """
        List custom quote sessions where admin set price_id but user has not paid yet.

        Returns sessions where custom_quote_submitted=true, price_id is set,
        and payment_received=false.
        """
        result = await self.db.execute(
            select(OnboardingSessionModel)
            .where(
                OnboardingSessionModel.custom_quote_submitted.is_(True),
                OnboardingSessionModel.payment_received.is_(False),
                OnboardingSessionModel.price_id.isnot(None),
                OnboardingSessionModel.price_id != "",
            )
            .order_by(OnboardingSessionModel.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_custom_quotes_paid(self) -> list[OnboardingSessionModel]:
        """
        List custom quote sessions that have been paid.

        Returns sessions where custom_quote_submitted=true and payment_received=true.
        """
        result = await self.db.execute(
            select(OnboardingSessionModel)
            .where(
                OnboardingSessionModel.custom_quote_submitted.is_(True),
                OnboardingSessionModel.payment_received.is_(True),
            )
            .order_by(OnboardingSessionModel.created_at.desc())
        )
        return list(result.scalars().all())

    async def complete_onboarding_session_by_uuid(self, session_uuid: str) -> dict:
        """
        Complete an onboarding session by UUID, creating:
        1. User account (Clerk + Database via UserService)
        2. Channel records for all provided URLs
        3. Payment record from checkout data
        4. Mark onboarding session as completed

        This method processes the entire onboarding flow and creates all necessary
        records. If any DB operation fails after Clerk user creation, the Clerk user
        is deleted to maintain consistency (compensating transaction pattern).

        Args:
            session_uuid: UUID of the onboarding session to complete

        Returns:
            Dictionary with completion details:
            {
                "user_id": int,
                "channels_created": int,
                "payment_id": int,
            }

        Raises:
            OnboardingSessionNotFound: If session doesn't exist
            AppError: If prerequisites are not met (payment, account info, channels)
        """
        # Get onboarding session by UUID
        session = await self.get_by_uuid(session_uuid)
        if not session:
            raise OnboardingSessionNotFound(
                message=f"No onboarding session found for UUID: {session_uuid}"
            )

        # Validate prerequisites
        if not session.payment_received:
            raise AppError(
                message="Payment must be received before completing onboarding",
                error_code="payment_not_received",
                status_code=HTTPStatus.BAD_REQUEST,
            )

        session_details = session.session_details or {}
        account_data = session_details.get("account")
        checkout_data = session_details.get("checkout")
        pages_data = session_details.get("pages", {})

        if not account_data:
            raise AppError(
                message="Account information is required to complete onboarding",
                error_code="missing_account_info",
                status_code=HTTPStatus.BAD_REQUEST,
            )

        if not checkout_data:
            raise AppError(
                message="Payment information is required to complete onboarding",
                error_code="missing_payment_info",
                status_code=HTTPStatus.BAD_REQUEST,
            )

        channels = pages_data.get("channels", [])
        if not channels:
            raise AppError(
                message="At least one channel URL is required to complete onboarding",
                error_code="missing_channels",
                status_code=HTTPStatus.BAD_REQUEST,
            )

        # Extract account information
        account_info = account_data
        password = account_info.get("password")
        if not password:
            raise AppError(
                message="Password is required to create user account",
                error_code="missing_password",
                status_code=HTTPStatus.BAD_REQUEST,
            )

        # Create user via UserService (handles Clerk + DB)
        user_service = UserService(db=self.db)
        user_create_data = UserCreateSchema(
            email=session.email,
            first_name=account_info["first_name"],
            last_name=account_info["last_name"],
            password=password,
            account_type=account_info["account_type"],
        )
        
        user = await user_service.create(user_create_data)
        clerk_user_id = user.clerk_user_id  # Store for potential rollback

        try:
            # Create channels
            channel_service = ChannelService(db=self.db)
            created_channels = []

            # Phase 1: verify all channels concurrently (each has a 30s timeout)
            channel_url_strs = [str(url) for url in channels]
            platforms = [self._detect_platform_from_url(s) for s in channel_url_strs]
            verification_results = await asyncio.gather(
                *[self._verify_channel(s, p) for s, p in zip(channel_url_strs, platforms)],
                return_exceptions=True,
            )

            # Phase 2: insert into DB sequentially (fast, shared session)
            for channel_url_str, platform, result in zip(
                channel_url_strs, platforms, verification_results
            ):
                if isinstance(result, Exception):
                    logger.warning(
                        "Channel verification failed for %s: %s", channel_url_str, result
                    )
                    username, follower_count, verification_status = (
                        None,
                        None,
                        VerificationStatus.FAILED,
                    )
                else:
                    username, follower_count, verification_status = result

                channel_data = ChannelCreateSchema(
                    user_id=user.id,
                    url=channel_url_str,
                    platform=platform,
                    username=username,
                    follower_count=follower_count,
                    verification_status=verification_status,
                )
                channel = await channel_service.create(channel_data)

                # Update platform if detected
                if platform:
                    channel.platform = platform
                    await self.db.flush()
                    await self.db.refresh(channel)

                created_channels.append(channel.id)

            # Create payment record from checkout data
            invoice_id = checkout_data.get("invoice_id")
            subscription_id = checkout_data.get("subscription_id")
            customer_id = checkout_data.get("customer_id")
            price_id = checkout_data.get("price_id")
            amount = checkout_data.get("amount", 0)
            currency = checkout_data.get("currency", "USD")
            payment_flow_type = checkout_data.get("payment_flow_type")
            signature = checkout_data.get("signature")
            service_agreement_signed_at_raw = checkout_data.get(
                "service_agreement_signed_at"
            )
            service_agreement_signed_at = self._parse_iso_datetime(
                service_agreement_signed_at_raw
            )

            # Determine plan type from Stripe price_id
            plan_type = self._determine_plan_type(price_id)

            # Use invoice_id as order_id (from webhook data.id)
            order_id = invoice_id or subscription_id or f"order_{datetime.utcnow().timestamp()}"

            # Determine payment type from payment flow type
            if payment_flow_type == "custom_quote":
                payment_type = PaymentType.CUSTOM_QUOTE
            else:
                payment_type = PaymentType.SUBSCRIPTION

            payment_service = PaymentService(db=self.db)
            payment_data = PaymentCreateSchema(
                user_id=user.id,
                order_id=order_id,
                subscription_id=subscription_id,
                customer_id=customer_id,
                status=PaymentStatus.COMPLETED,
                payment_type=payment_type,
                amount=amount,
                currency=currency,
                plan_type=plan_type,
                signature=signature,
                service_agreement_signed_at=service_agreement_signed_at,
                metadata_=self._sanitize_payment_metadata(checkout_data),
            )
            payment = await payment_service.create(payment_data)

            # Mark onboarding session as completed
            session.current_step = OnboardingStep.COMPLETED
            attributes.flag_modified(session, "current_step")
            await self.db.flush()
            await self.db.refresh(session)

            try:
                create_basic_canto_user_task.delay(
                    user_email=session.email,
                    first_name=account_info["first_name"],
                    last_name=account_info["last_name"],
                )
            except Exception:
                logger.exception(
                    "Failed to enqueue Canto user creation for session %s",
                    session.uuid,
                )

            return {
                "user_id": user.id,
                "channels_created": len(created_channels),
                "payment_id": payment.id,
            }

        except Exception as e:
            # Compensating transaction: Delete Clerk user if subsequent operations fail
            logger.error(f"Onboarding completion failed after Clerk user creation: {e}")
            try:
                await clerk_client.users.delete_async(user_id=clerk_user_id)
                logger.info(f"Rolled back Clerk user {clerk_user_id} due to completion failure")
            except Exception as clerk_error:
                logger.error(f"Failed to rollback Clerk user {clerk_user_id}: {clerk_error}")
            raise

    async def _verify_channel(
        self,
        channel_url: str,
        platform: Platform | None,
    ) -> tuple[str | None, int | None, VerificationStatus]:
        """
        Verify a channel via SMS SDK and return username, follower_count, status.
        """
        username: str | None = None
        follower_count: int | None = None
        verification_status = VerificationStatus.FAILED

        if platform == Platform.INSTAGRAM:
            handle = self._extract_instagram_handle_from_url(channel_url)
            if handle:
                try:
                    response_data = await get_instagram_user_details(
                        handle=handle,
                        timeout_seconds=self.INSTAGRAM_USER_DETAILS_TIMEOUT_SECONDS,
                    )
                    username = (
                        response_data.get("data", {})
                        .get("user", {})
                        .get("username")
                    ) or handle
                    follower_count = self._coerce_int(
                        response_data.get("data", {})
                        .get("user", {})
                        .get("stats", {})
                        .get("follower_count")
                    )
                except SMSAPIError:
                    logger.warning(
                        "SMS API error during Instagram verification for %s",
                        channel_url,
                    )

        elif platform == Platform.TIKTOK:
            handle = self._extract_tiktok_handle_from_url(channel_url)
            if handle:
                try:
                    response_data = await get_tiktok_user_details(
                        handle=handle,
                        timeout_seconds=self.INSTAGRAM_USER_DETAILS_TIMEOUT_SECONDS,
                    )
                    username = (
                        response_data.get("data", {})
                        .get("user", {})
                        .get("unique_id")
                    ) or (
                        response_data.get("data", {})
                        .get("user", {})
                        .get("uniqueId")
                    ) or (
                        response_data.get("data", {})
                        .get("user", {})
                        .get("username")
                    ) or handle
                    follower_count = self._coerce_int(
                        response_data.get("data", {})
                        .get("user", {})
                        .get("stats", {})
                        .get("follower_count")
                    )
                    if follower_count is None:
                        follower_count = self._coerce_int(
                            response_data.get("data", {})
                            .get("user", {})
                            .get("stats", {})
                            .get("followerCount")
                        )
                except SMSAPIError:
                    logger.warning(
                        "SMS API error during TikTok verification for %s",
                        channel_url,
                    )

        elif platform == Platform.YOUTUBE:
            name = self._extract_youtube_name_from_url(channel_url)
            if name:
                try:
                    response_data = await get_youtube_channel_details(
                        name=name,
                        timeout_seconds=self.INSTAGRAM_USER_DETAILS_TIMEOUT_SECONDS,
                    )
                    username = (
                        response_data.get("data", {})
                        .get("user", {})
                        .get("name")
                    ) or name
                    follower_count = self._coerce_int(
                        response_data.get("data", {})
                        .get("user", {})
                        .get("stats", {})
                        .get("subscriber_count")
                    )
                    if follower_count is None:
                        follower_count = self._coerce_int(
                            response_data.get("data", {})
                            .get("user", {})
                            .get("stats", {})
                            .get("subscriberCount")
                        )
                except SMSAPIError:
                    logger.warning(
                        "SMS API error during YouTube verification for %s",
                        channel_url,
                    )

        elif platform == Platform.FACEBOOK:
            page_url = self._extract_facebook_url(channel_url)
            if page_url:
                try:
                    response_data = await get_facebook_page_details(
                        url=page_url,
                        timeout_seconds=self.INSTAGRAM_USER_DETAILS_TIMEOUT_SECONDS,
                    )
                    username = (
                        response_data.get("data", {})
                        .get("page", {})
                        .get("name")
                    )
                    follower_count = self._coerce_int(
                        response_data.get("data", {})
                        .get("page", {})
                        .get("stats", {})
                        .get("followers_count")
                    )
                    if follower_count is None:
                        follower_count = self._coerce_int(
                            response_data.get("data", {})
                            .get("page", {})
                            .get("stats", {})
                            .get("follower_count")
                        )
                    if follower_count is None:
                        follower_count = self._coerce_int(
                            response_data.get("data", {})
                            .get("page", {})
                            .get("stats", {})
                            .get("followerCount")
                        )
                except SMSAPIError:
                    logger.warning(
                        "SMS API error during Facebook verification for %s",
                        channel_url,
                    )

        if follower_count is not None:
            verification_status = VerificationStatus.VERIFIED

        if verification_status != VerificationStatus.VERIFIED:
            logger.warning(
                "Channel verification failed or missing follower_count for %s",
                channel_url,
            )

        return username, follower_count, verification_status

    

    async def _compute_custom_quote_state(
        self, channels: list[str]
    ) -> tuple[bool, list[dict]]:
        """
        Determine custom quote requirement and per-channel trigger flags.

        Returns:
            (requires_custom_quote, triggers)
        """
        if not channels:
            return False, []

        normalized_channels = [str(ch).rstrip("/") for ch in channels]
        triggers: list[dict] = []
        trigger_keys: set[tuple[str, str]] = set()
        supported_detected = False

        def _trigger_message(flag: CustomQuoteTriggerFlag) -> str:
            if flag == CustomQuoteTriggerFlag.HIGH_FOLLOWERS:
                return "Over 2 million followers"
            if flag == CustomQuoteTriggerFlag.UNSUPPORTED_PLATFORM:
                return "Unsupported platform"
            if flag == CustomQuoteTriggerFlag.UNKNOWN_FOLLOWER_COUNT:
                return "Follower count unavailable"
            if flag == CustomQuoteTriggerFlag.SMS_API_ERROR:
                return "Unable to verify follower count (service unavailable)"
            return "Custom quote required"

        def add_trigger(channel_url: str, flag: CustomQuoteTriggerFlag) -> None:
            key = (channel_url, flag.value)
            if key in trigger_keys:
                return
            trigger_keys.add(key)
            triggers.append(
                {
                    "channel_url": channel_url,
                    "flag": flag.value,
                    "message": _trigger_message(flag),
                }
            )

        instagram_cache: dict[str, tuple[int | None, bool]] = {}
        tiktok_cache: dict[str, tuple[int | None, bool]] = {}
        youtube_cache: dict[str, tuple[int | None, bool]] = {}
        facebook_cache: dict[str, tuple[int | None, bool]] = {}
        twitter_cache: dict[str, tuple[int | None, bool]] = {}
        snapchat_cache: dict[str, tuple[int | None, bool]] = {}

        platform_caches: dict[str, dict[str, tuple[int | None, bool]]] = {
            "instagram": instagram_cache,
            "tiktok": tiktok_cache,
            "youtube": youtube_cache,
            "facebook": facebook_cache,
            "twitter": twitter_cache,
            "snapchat": snapchat_cache,
        }

        for channel_url in normalized_channels:
            parsed = urlparse(channel_url)
            if parsed.netloc.lower() == "2m.com":
                add_trigger(channel_url, CustomQuoteTriggerFlag.HIGH_FOLLOWERS)

            # Extract all handles (no I/O)
            instagram_handle = self._extract_instagram_handle_from_url(channel_url)
            tiktok_handle = self._extract_tiktok_handle_from_url(channel_url)
            youtube_name = self._extract_youtube_name_from_url(channel_url)
            facebook_url = self._extract_facebook_url(channel_url)
            twitter_handle = self._extract_twitter_handle_from_url(channel_url)
            snapchat_handle = self._extract_snapchat_handle_from_url(channel_url)

            if instagram_handle:
                supported_detected = True
            if tiktok_handle:
                supported_detected = True
            if youtube_name:
                supported_detected = True
            if facebook_url:
                supported_detected = True
            if twitter_handle:
                supported_detected = True
            if snapchat_handle:
                supported_detected = True

            # Build concurrent fetch tasks for uncached handles
            fetch_tasks: list[tuple[str, str]] = []  # (platform, cache_key)
            fetch_coros: list = []
            if instagram_handle and instagram_handle not in instagram_cache:
                fetch_tasks.append(("instagram", instagram_handle))
                fetch_coros.append(self._get_instagram_follower_count(instagram_handle))
            if tiktok_handle and tiktok_handle not in tiktok_cache:
                fetch_tasks.append(("tiktok", tiktok_handle))
                fetch_coros.append(self._get_tiktok_follower_count(tiktok_handle))
            if youtube_name and youtube_name not in youtube_cache:
                fetch_tasks.append(("youtube", youtube_name))
                fetch_coros.append(self._get_youtube_subscriber_count(youtube_name))
            if facebook_url and facebook_url not in facebook_cache:
                fetch_tasks.append(("facebook", facebook_url))
                fetch_coros.append(self._get_facebook_follower_count(facebook_url))
            if twitter_handle and twitter_handle not in twitter_cache:
                fetch_tasks.append(("twitter", twitter_handle))
                fetch_coros.append(self._get_twitter_follower_count(twitter_handle))
            if snapchat_handle and snapchat_handle not in snapchat_cache:
                fetch_tasks.append(("snapchat", snapchat_handle))
                fetch_coros.append(self._get_snapchat_follower_count(snapchat_handle))

            # Run all uncached platform lookups for this URL concurrently
            if fetch_coros:
                fetch_results = await asyncio.gather(*fetch_coros, return_exceptions=True)
                for (platform, key), result in zip(fetch_tasks, fetch_results):
                    cache = platform_caches[platform]
                    if isinstance(result, SMSAPIError):
                        logger.warning("SMS API error for %s %s", platform, key)
                        cache[key] = (None, True)
                    elif isinstance(result, Exception):
                        logger.warning(
                            "Unexpected error fetching %s followers for %s: %s",
                            platform, key, result,
                        )
                        cache[key] = (None, True)
                    else:
                        cache[key] = (result, False)

            # Evaluate triggers from caches
            if instagram_handle:
                count, api_error = instagram_cache[instagram_handle]
                if api_error:
                    add_trigger(channel_url, CustomQuoteTriggerFlag.SMS_API_ERROR)
                elif count is None:
                    add_trigger(channel_url, CustomQuoteTriggerFlag.UNKNOWN_FOLLOWER_COUNT)
                elif count > self.FOLLOWER_CUSTOM_QUOTE_THRESHOLD:
                    add_trigger(channel_url, CustomQuoteTriggerFlag.HIGH_FOLLOWERS)

            if tiktok_handle:
                count, api_error = tiktok_cache[tiktok_handle]
                if api_error:
                    add_trigger(channel_url, CustomQuoteTriggerFlag.SMS_API_ERROR)
                elif count is None:
                    add_trigger(channel_url, CustomQuoteTriggerFlag.UNKNOWN_FOLLOWER_COUNT)
                elif count > self.FOLLOWER_CUSTOM_QUOTE_THRESHOLD:
                    add_trigger(channel_url, CustomQuoteTriggerFlag.HIGH_FOLLOWERS)

            if youtube_name:
                count, api_error = youtube_cache[youtube_name]
                if api_error:
                    add_trigger(channel_url, CustomQuoteTriggerFlag.SMS_API_ERROR)
                elif count is None:
                    add_trigger(channel_url, CustomQuoteTriggerFlag.UNKNOWN_FOLLOWER_COUNT)
                elif count > self.FOLLOWER_CUSTOM_QUOTE_THRESHOLD:
                    add_trigger(channel_url, CustomQuoteTriggerFlag.HIGH_FOLLOWERS)

            if facebook_url:
                count, api_error = facebook_cache[facebook_url]
                if api_error:
                    add_trigger(channel_url, CustomQuoteTriggerFlag.SMS_API_ERROR)
                elif count is None:
                    add_trigger(channel_url, CustomQuoteTriggerFlag.UNKNOWN_FOLLOWER_COUNT)
                elif count > self.FOLLOWER_CUSTOM_QUOTE_THRESHOLD:
                    add_trigger(channel_url, CustomQuoteTriggerFlag.HIGH_FOLLOWERS)

            if twitter_handle:
                count, api_error = twitter_cache[twitter_handle]
                if api_error:
                    add_trigger(channel_url, CustomQuoteTriggerFlag.SMS_API_ERROR)
                elif count is None:
                    add_trigger(channel_url, CustomQuoteTriggerFlag.UNKNOWN_FOLLOWER_COUNT)
                elif count > self.FOLLOWER_CUSTOM_QUOTE_THRESHOLD:
                    add_trigger(channel_url, CustomQuoteTriggerFlag.HIGH_FOLLOWERS)

            if snapchat_handle:
                count, api_error = snapchat_cache[snapchat_handle]
                if api_error:
                    add_trigger(channel_url, CustomQuoteTriggerFlag.SMS_API_ERROR)
                elif count is None:
                    add_trigger(channel_url, CustomQuoteTriggerFlag.UNKNOWN_FOLLOWER_COUNT)
                elif count > self.FOLLOWER_CUSTOM_QUOTE_THRESHOLD:
                    add_trigger(channel_url, CustomQuoteTriggerFlag.HIGH_FOLLOWERS)

            if not (
                instagram_handle
                or tiktok_handle
                or youtube_name
                or facebook_url
                or twitter_handle
                or snapchat_handle
            ):
                if (
                    channel_url,
                    CustomQuoteTriggerFlag.HIGH_FOLLOWERS.value,
                ) not in trigger_keys:
                    add_trigger(
                        channel_url,
                        CustomQuoteTriggerFlag.UNSUPPORTED_PLATFORM,
                    )

        if not supported_detected:
            for channel_url in normalized_channels:
                if (
                    channel_url,
                    CustomQuoteTriggerFlag.HIGH_FOLLOWERS.value,
                ) in trigger_keys:
                    continue
                add_trigger(
                    channel_url,
                    CustomQuoteTriggerFlag.UNSUPPORTED_PLATFORM,
                )
            return True, triggers

        return len(triggers) > 0, triggers


    async def _get_instagram_follower_count(self, handle: str) -> int | None:
        """
        Get Instagram follower count for a handle via SMS API.

        Raises:
            SMSAPIError: When the SMS API call fails.
        """
        response_data = await get_instagram_user_details(
            handle=handle,
            timeout_seconds=self.INSTAGRAM_USER_DETAILS_TIMEOUT_SECONDS,
        )

        follower_count = (
            response_data.get("data", {})
            .get("user", {})
            .get("stats", {})
            .get("follower_count")
        )
        parsed = self._coerce_int(follower_count)
        if parsed is not None:
            return parsed

        logger.warning(
            "Instagram follower_count missing/invalid for handle %s",
            handle,
        )
        return None

    async def _get_tiktok_follower_count(self, handle: str) -> int | None:
        """
        Get TikTok follower count for a handle via SMS API.

        Raises:
            SMSAPIError: When the SMS API call fails.
        """
        response_data = await get_tiktok_user_details(
            handle=handle,
            timeout_seconds=self.INSTAGRAM_USER_DETAILS_TIMEOUT_SECONDS,
        )

        follower_count = (
            response_data.get("data", {})
            .get("user", {})
            .get("stats", {})
            .get("follower_count")
        )
        parsed = self._coerce_int(follower_count)
        if parsed is not None:
            return parsed

        follower_count = (
            response_data.get("data", {})
            .get("user", {})
            .get("stats", {})
            .get("followerCount")
        )
        parsed = self._coerce_int(follower_count)
        if parsed is not None:
            return parsed

        logger.warning(
            "TikTok follower_count missing/invalid for handle %s",
            handle,
        )
        return None

    async def _get_youtube_subscriber_count(self, name: str) -> int | None:
        """
        Get YouTube subscriber count for a channel name via SMS API.

        Raises:
            SMSAPIError: When the SMS API call fails.
        """
        response_data = await get_youtube_channel_details(
            name=name,
            timeout_seconds=self.INSTAGRAM_USER_DETAILS_TIMEOUT_SECONDS,
        )

        subscriber_count = (
            response_data.get("data", {})
            .get("user", {})
            .get("stats", {})
            .get("subscriber_count")
        )
        parsed = self._coerce_int(subscriber_count)
        if parsed is not None:
            return parsed

        subscriber_count = (
            response_data.get("data", {})
            .get("user", {})
            .get("stats", {})
            .get("subscriberCount")
        )
        parsed = self._coerce_int(subscriber_count)
        if parsed is not None:
            return parsed

        logger.warning(
            "YouTube subscriber_count missing/invalid for channel %s",
            name,
        )
        return None

    async def _get_facebook_follower_count(self, url: str) -> int | None:
        """
        Get Facebook follower count for a page URL via SMS API.

        Raises:
            SMSAPIError: When the SMS API call fails.
        """
        response_data = await get_facebook_page_details(
            url=url,
            timeout_seconds=self.INSTAGRAM_USER_DETAILS_TIMEOUT_SECONDS,
        )

        follower_count = (
            response_data.get("data", {})
            .get("page", {})
            .get("stats", {})
            .get("followers_count")
        )
        parsed = self._coerce_int(follower_count)
        if parsed is not None:
            return parsed

        follower_count = (
            response_data.get("data", {})
            .get("page", {})
            .get("stats", {})
            .get("follower_count")
        )
        parsed = self._coerce_int(follower_count)
        if parsed is not None:
            return parsed

        follower_count = (
            response_data.get("data", {})
            .get("page", {})
            .get("stats", {})
            .get("followerCount")
        )
        parsed = self._coerce_int(follower_count)
        if parsed is not None:
            return parsed

        logger.warning(
            "Facebook follower_count missing/invalid for url %s",
            url,
        )
        return None

    async def _get_twitter_follower_count(self, handle: str) -> int | None:
        """
        Get Twitter/X follower count for a handle via SMS API.

        Raises:
            SMSAPIError: When the SMS API call fails.
        """
        response_data = await get_twitter_user_details(
            handle=handle,
            timeout_seconds=self.INSTAGRAM_USER_DETAILS_TIMEOUT_SECONDS,
        )

        follower_count = (
            response_data.get("data", {})
            .get("user", {})
            .get("stats", {})
            .get("follower_count")
        )
        parsed = self._coerce_int(follower_count)
        if parsed is not None:
            return parsed

        follower_count = (
            response_data.get("data", {})
            .get("user", {})
            .get("stats", {})
            .get("followers_count")
        )
        parsed = self._coerce_int(follower_count)
        if parsed is not None:
            return parsed

        logger.warning(
            "Twitter follower_count missing/invalid for handle %s",
            handle,
        )
        return None

    async def _get_snapchat_follower_count(self, handle: str) -> int | None:
        """
        Get Snapchat follower count for a handle via SMS API.

        Raises:
            SMSAPIError: When the SMS API call fails.
        """
        response_data = await get_snapchat_user_details(
            handle=handle,
            timeout_seconds=self.INSTAGRAM_USER_DETAILS_TIMEOUT_SECONDS,
        )

        follower_count = (
            response_data.get("data", {})
            .get("user", {})
            .get("stats", {})
            .get("followers_count")
        )
        parsed = self._coerce_int(follower_count)
        if parsed is not None:
            return parsed

        follower_count = (
            response_data.get("data", {})
            .get("user", {})
            .get("stats", {})
            .get("follower_count")
        )
        parsed = self._coerce_int(follower_count)
        if parsed is not None:
            return parsed

        logger.warning(
            "Snapchat followers_count missing/invalid for handle %s",
            handle,
        )
        return None

    @staticmethod
    def _coerce_int(value: object) -> int | None:
        if isinstance(value, int):
            return value
        if isinstance(value, str):
            value = value.replace(",", "").strip()
            if value.isdigit():
                return int(value)
        return None

    @staticmethod
    def _extract_instagram_handle_from_url(url: str) -> str | None:
        """
        Extract Instagram profile handle from a channel URL.
        """
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]
        if domain.startswith("m."):
            domain = domain[2:]

        if domain != "instagram.com":
            return None

        path_parts = [segment for segment in parsed.path.split("/") if segment]
        if not path_parts:
            return None

        profile_handle = path_parts[0].lstrip("@")
        if not profile_handle:
            return None

        # Skip known non-profile top-level paths.
        if profile_handle.lower() in {"p", "reel", "tv", "stories", "explore"}:
            return None

        allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._")
        if any(char not in allowed for char in profile_handle):
            return None

        return profile_handle

    @staticmethod
    def _extract_tiktok_handle_from_url(url: str) -> str | None:
        """
        Extract TikTok profile handle from a channel URL.
        """
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]
        if domain.startswith("m."):
            domain = domain[2:]

        if domain != "tiktok.com":
            return None

        path_parts = [segment for segment in parsed.path.split("/") if segment]
        if not path_parts:
            return None

        profile_handle = path_parts[0].lstrip("@")
        if not profile_handle:
            return None

        allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._")
        if any(char not in allowed for char in profile_handle):
            return None

        return profile_handle

    @staticmethod
    def _extract_youtube_name_from_url(url: str) -> str | None:
        """
        Extract YouTube channel name from a channel URL.
        """
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]

        if domain not in {"youtube.com", "youtu.be"}:
            return None

        path_parts = [segment for segment in parsed.path.split("/") if segment]
        if not path_parts:
            return None

        # Support /@name, /c/name, /channel/id, /user/name, and youtu.be/name
        if path_parts[0].startswith("@"):
            return path_parts[0].lstrip("@")
        if path_parts[0] in {"c", "channel", "user"} and len(path_parts) > 1:
            return path_parts[1]
        if domain == "youtu.be":
            return path_parts[0]
        if len(path_parts) == 1:
            return path_parts[0]
        return None

    @staticmethod
    def _extract_facebook_url(url: str) -> str | None:
        """
        Validate and return a Facebook page URL for SMS lookup.
        """
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]
        if domain.startswith("m."):
            domain = domain[2:]

        if domain not in {"facebook.com", "fb.com"}:
            return None

        if not parsed.path or parsed.path == "/":
            return None

        return url

    @staticmethod
    def _extract_twitter_handle_from_url(url: str) -> str | None:
        """
        Extract Twitter/X handle from a channel URL.
        """
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]
        if domain.startswith("m."):
            domain = domain[2:]

        if domain not in {"twitter.com", "x.com"}:
            return None

        path_parts = [segment for segment in parsed.path.split("/") if segment]
        if not path_parts:
            return None

        profile_handle = path_parts[0].lstrip("@")
        if not profile_handle:
            return None

        allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_")
        if any(char not in allowed for char in profile_handle):
            return None

        return profile_handle

    @staticmethod
    def _extract_snapchat_handle_from_url(url: str) -> str | None:
        """
        Extract Snapchat handle from a channel URL.
        """
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]

        if domain not in {"snapchat.com", "www.snapchat.com"}:
            return None

        path_parts = [segment for segment in parsed.path.split("/") if segment]
        if not path_parts:
            return None
        if path_parts[0] == "add":
            if len(path_parts) < 2:
                return None
            profile_handle = path_parts[1].lstrip("@")
        else:
            if len(path_parts) != 1:
                return None
            profile_handle = path_parts[0].lstrip("@")
        if not profile_handle:
            return None

        allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._")
        if any(char not in allowed for char in profile_handle):
            return None

        return profile_handle

    @staticmethod
    def _detect_platform_from_url(url: str) -> Platform | None:
        """Detect platform from channel URL."""
        parsed = urlparse(url)
        domain = parsed.netloc.lower()

        if "instagram.com" in domain:
            return Platform.INSTAGRAM
        elif "tiktok.com" in domain:
            return Platform.TIKTOK
        elif "youtube.com" in domain or "youtu.be" in domain:
            return Platform.YOUTUBE
        elif "facebook.com" in domain:
            return Platform.FACEBOOK
        else:
            return None

    @staticmethod
    def _determine_plan_type(price_id: str | int | None) -> PlanType | None:
        """
        Determine plan type from Stripe price ID.
        """
        if not price_id:
            return None

        normalized_price_id = str(price_id)
        if normalized_price_id == settings.STRIPE_PRICE_ID_MONTHLY:
            return PlanType.MONTHLY
        if normalized_price_id == settings.STRIPE_PRICE_ID_YEARLY:
            return PlanType.ANNUAL
        return PlanType.MONTHLY

    @staticmethod
    def _extract_price_id_from_checkout_session(checkout_session: dict) -> str | None:
        line_items = checkout_session.get("line_items")
        if not isinstance(line_items, list) or not line_items:
            return None
        first_item = line_items[0] if isinstance(line_items[0], dict) else {}
        price_data = first_item.get("price")
        if isinstance(price_data, dict):
            return price_data.get("id")
        if isinstance(price_data, str):
            return price_data
        return None

    @staticmethod
    def _extract_price_id_from_invoice(invoice: dict) -> str | None:
        lines = invoice.get("lines")
        if not isinstance(lines, dict):
            return None
        data = lines.get("data")
        if not isinstance(data, list) or not data:
            return None
        first_line = data[0] if isinstance(data[0], dict) else {}
        price_data = first_line.get("price")
        if isinstance(price_data, dict):
            return price_data.get("id")
        return None

    @staticmethod
    def _parse_iso_datetime(value: object) -> datetime | None:
        """Parse ISO datetime strings from session checkout metadata."""
        if not isinstance(value, str) or not value.strip():
            return None

        normalized = value.strip().replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(normalized)
        except ValueError:
            logger.warning("Invalid service agreement signed timestamp: %s", value)
            return None

    async def clean_up_stale_onboarding_sessions(self) -> None:
        """
        Clean up onboarding sessions that have been in the PAGES step for over a week.
        """
        one_week_ago = datetime.now(timezone.utc) - timedelta(days=7)
        result = await self.db.execute(
            select(OnboardingSessionModel).where(
                OnboardingSessionModel.current_step == OnboardingStep.PAGES,
                OnboardingSessionModel.created_at < one_week_ago,
            )
        )
        stale_sessions = list(result.scalars().all())
        for session in stale_sessions:
            await self.delete_by_uuid(str(session.uuid))
        

def serialize_custom_quote_session(session: OnboardingSessionModel) -> dict:
    """Serialize custom quote session and include flattened helper fields."""
    data = OnboardingSessionOutSchema.model_validate(session).model_dump()
    details = session.session_details if isinstance(session.session_details, dict) else {}
    pages = details.get("pages")
    pages = pages if isinstance(pages, dict) else {}
    checkout = details.get("checkout")
    checkout = checkout if isinstance(checkout, dict) else {}
    data["channels"] = list(pages.get("channels") or [])
    data["custom_quote_triggers"] = list(pages.get("custom_quote_triggers") or [])
    data["service_agreement_signed_at"] = checkout.get("service_agreement_signed_at")
    return data
