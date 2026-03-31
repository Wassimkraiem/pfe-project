import asyncio
import logging
from datetime import UTC, datetime, timedelta

from fastapi import Depends
from http import HTTPStatus
import stripe
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.database import get_db
from app.exceptionhandler import AppError
from app.channel.models import ChannelModel
from app.channel.schemas import ChannelOutSchema
from app.payment.enums import PaymentStatus, PaymentType
from app.payment.exceptions import PaymentNotFound, PaymentProviderError
from app.payment.models import PaymentModel
from app.payment.schemas import PaymentCreateSchema
from app.payment.stripe_client import StripeClient
from app.payment.stripe_sdk import StripeSDK
from app.user.models import UserModel
from app.user.schemas import UserOutSchema

logger = logging.getLogger(__name__)


def verify_webhook_signature(payload: bytes, signature: str, secret: str) -> bool:
    try:
        client = StripeClient()
        client.construct_webhook_event(payload=payload, signature=signature, secret=secret)
        return True
    except (ValueError, stripe.SignatureVerificationError):
        return False


def parse_webhook_event(payload: bytes, signature: str, secret: str) -> dict:
    client = StripeClient()
    return client.construct_webhook_event(payload=payload, signature=signature, secret=secret)


class PaymentService:
    """Service for payment operations."""

    def __init__(self, db: AsyncSession = Depends(get_db)) -> None:
        self.db = db
        self.client = StripeClient()
        self.sdk = StripeSDK(client=self.client)



    async def _resolve_stripe_customer_id(
        self, *, payment_customer_id: str | None, user_email: str | None
    ) -> str | None:
        customer_id = (payment_customer_id or "").strip()
        if customer_id:
            if customer_id.startswith("cus_"):
                return customer_id
            logger.info("Skipping non-Stripe customer id: %s", customer_id)

        try:
            return await self.sdk.get_customer_id_by_email(user_email)
        except stripe.InvalidRequestError:
            logger.warning(
                "Skipping Stripe customer lookup by email due to invalid request. email=%s",
                user_email,
            )
            return None
        except Exception as exc:
            raise PaymentProviderError(details=str(exc)) from exc

    async def _create_customer_portal_url(self, *, customer_id: str | None) -> str | None:
        if not customer_id:
            return None

        try:
            portal = await self.sdk.create_customer_portal_session(
                customer_id=customer_id,
                return_url=settings.STRIPE_CUSTOMER_PORTAL_RETURN_URL,
            )
            url = portal.get("url")
            return url if isinstance(url, str) and url else None
        except stripe.InvalidRequestError:
            logger.warning(
                "Skipping portal creation for invalid Stripe customer id: %s",
                customer_id,
            )
            return None
        except Exception as exc:
            raise PaymentProviderError(details=str(exc)) from exc



    async def create(self, payment_in: PaymentCreateSchema) -> PaymentModel:
        """
        Create a new payment record.

        Args:
            payment_in: Payment creation schema with all required fields.

        Returns:
            Created PaymentModel instance with generated ID.
        """
        payment = PaymentModel(
            user_id=payment_in.user_id,
            order_id=payment_in.order_id,
            subscription_id=payment_in.subscription_id,
            customer_id=payment_in.customer_id,
            status=payment_in.status,
            payment_type=payment_in.payment_type,
            amount=payment_in.amount,
            currency=payment_in.currency,
            plan_type=payment_in.plan_type,
            signature=payment_in.signature,
            service_agreement_signed_at=payment_in.service_agreement_signed_at,
            metadata_=payment_in.metadata_,
        )
        self.db.add(payment)
        await self.db.flush()
        await self.db.refresh(payment)
        logger.info(
            "Created payment record: id=%s, user_id=%s, order_id=%s",
            payment.id,
            payment.user_id,
            payment.order_id,
        )
        return payment

    async def find_user_for_renewal_event(
        self,
        *,
        subscription_id: str | None,
        customer_id: str | None,
        user_email: str | None,
    ) -> UserModel | None:
        """Resolve a user for a renewal invoice event."""
        normalized_subscription_id = (subscription_id or "").strip()
        normalized_customer_id = (customer_id or "").strip()
        normalized_email = (user_email or "").strip().lower()

        if normalized_subscription_id:
            by_subscription = await self.db.execute(
                select(UserModel)
                .join(PaymentModel, PaymentModel.user_id == UserModel.id)
                .where(PaymentModel.subscription_id == normalized_subscription_id)
                .order_by(PaymentModel.created_at.desc())
                .limit(1)
            )
            user = by_subscription.scalar_one_or_none()
            if user:
                return user

        if normalized_customer_id:
            by_customer = await self.db.execute(
                select(UserModel)
                .join(PaymentModel, PaymentModel.user_id == UserModel.id)
                .where(PaymentModel.customer_id == normalized_customer_id)
                .order_by(PaymentModel.created_at.desc())
                .limit(1)
            )
            user = by_customer.scalar_one_or_none()
            if user:
                return user

        if normalized_email:
            by_email = await self.db.execute(
                select(UserModel).where(UserModel.email == normalized_email)
            )
            return by_email.scalar_one_or_none()

        return None

    async def create_or_update_renewal_payment(
        self,
        *,
        user_id: int,
        invoice_id: str,
        subscription_id: str | None,
        customer_id: str | None,
        amount: int,
        currency: str,
        status: PaymentStatus,
        metadata: dict,
    ) -> PaymentModel:
        """Idempotently persist renewal invoice as a payment record."""
        existing_result = await self.db.execute(
            select(PaymentModel)
            .where(
                PaymentModel.user_id == user_id,
                PaymentModel.order_id == invoice_id,
            )
            .limit(1)
        )
        payment = existing_result.scalar_one_or_none()
        if payment:
            payment.subscription_id = subscription_id
            payment.customer_id = customer_id
            payment.amount = amount
            payment.currency = currency
            payment.status = status
            payment.payment_type = PaymentType.SUBSCRIPTION
            payment.metadata_ = metadata
            await self.db.flush()
            await self.db.refresh(payment)
            return payment

        payment_in = PaymentCreateSchema(
            user_id=user_id,
            order_id=invoice_id,
            subscription_id=subscription_id,
            customer_id=customer_id,
            status=status,
            payment_type=PaymentType.SUBSCRIPTION,
            amount=amount,
            currency=currency,
            metadata_=metadata,
        )
        return await self.create(payment_in)

    async def mark_renewal_failed(
        self,
        *,
        user: UserModel,
        invoice_id: str,
        subscription_id: str | None,
        customer_id: str | None,
        amount: int,
        currency: str,
        metadata: dict,
    ) -> tuple[datetime, bool]:
        """Persist renewal failure and initialize grace period on first failure."""
        await self.create_or_update_renewal_payment(
            user_id=user.id,
            invoice_id=invoice_id,
            subscription_id=subscription_id,
            customer_id=customer_id,
            amount=amount,
            currency=currency,
            status=PaymentStatus.FAILED,
            metadata=metadata,
        )

        now = datetime.now(UTC)
        first_failure = user.renewal_failed_at is None
        if first_failure:
            user.renewal_failed_at = now
            user.renewal_grace_ends_at = now + timedelta(
                minutes=settings.RENEWAL_GRACE_PERIOD_MINUTES
            )

        await self.db.flush()
        if user.renewal_grace_ends_at is None:
            user.renewal_grace_ends_at = now + timedelta(
                minutes=settings.RENEWAL_GRACE_PERIOD_MINUTES
            )
            await self.db.flush()
        return user.renewal_grace_ends_at, first_failure

    async def mark_renewal_paid(
        self,
        *,
        user: UserModel,
        invoice_id: str,
        subscription_id: str | None,
        customer_id: str | None,
        amount: int,
        currency: str,
        metadata: dict,
    ) -> bool:
        """Persist renewal success and clear suspension/failure state."""
        await self.create_or_update_renewal_payment(
            user_id=user.id,
            invoice_id=invoice_id,
            subscription_id=subscription_id,
            customer_id=customer_id,
            amount=amount,
            currency=currency,
            status=PaymentStatus.COMPLETED,
            metadata=metadata,
        )

        was_suspended = bool(user.canto_access_suspended)
        user.renewal_failed_at = None
        user.renewal_grace_ends_at = None
        user.canto_access_suspended = False
        await self.db.flush()
        return was_suspended

    async def get_payment_details_for_user(self, user: UserModel) -> dict[str, object]:
        """
        Fetch payment details and Stripe customer portal URL for the user.

        Returns:
            Dict containing payment details, subscription info, and customer_portal_url.
        """
        result = await self.db.execute(
            select(PaymentModel)
            .where(
                PaymentModel.user_id == user.id,
                PaymentModel.payment_type == PaymentType.SUBSCRIPTION,
                PaymentModel.customer_id.is_not(None),
            )
            .order_by(PaymentModel.created_at.desc())
        )
        payment = result.scalars().first()
        if not payment:
            raise PaymentNotFound()

        if not payment.customer_id:
            raise PaymentNotFound(message="Payment customer not found")

        stripe_customer_id = await self._resolve_stripe_customer_id(
            payment_customer_id=payment.customer_id,
            user_email=user.email,
        )
        portal_url, subscription_details = await asyncio.gather(
            self._create_customer_portal_url(customer_id=stripe_customer_id),
            self._get_subscription_details(
                subscription_id=payment.subscription_id,
                customer_id=stripe_customer_id,
            ),
        )

        return {
            "payment": {
                "order_id": payment.order_id,
                "subscription_id": payment.subscription_id,
                "customer_id": payment.customer_id,
                "status": payment.status,
                "payment_type": payment.payment_type,
                "amount": payment.amount,
                "currency": payment.currency,
                "plan_type": payment.plan_type,
                "signature": payment.signature,
                "service_agreement_signed_at": payment.service_agreement_signed_at,
                "metadata": payment.metadata_,
                "created_at": payment.created_at,
                "updated_at": payment.updated_at,
            },
            "subscription": subscription_details,
            "customer_portal_url": portal_url,
            "renewal_failed": user.renewal_failed_at is not None,
            "renewal_grace_ends_at": user.renewal_grace_ends_at,
            "canto_access_suspended": user.canto_access_suspended,
        }

    async def get_user_payment_channels_overview(
        self,
        user: UserModel,
    ) -> dict[str, object]:
        """Fetch current user profile, payment details, and channels in a single payload."""
        payment_details: dict[str, object] | None
        try:
            payment_details = await self.get_payment_details_for_user(user)
        except PaymentNotFound:
            payment_details = None

        channels_result = await self.db.execute(
            select(ChannelModel)
            .where(ChannelModel.user_id == user.id)
            .order_by(ChannelModel.created_at.desc())
        )
        channels = channels_result.scalars().all()

        user_data = UserOutSchema.model_validate(user).model_dump()
        user_data.update(
            {
                "renewal_failed_at": user.renewal_failed_at,
                "renewal_grace_ends_at": user.renewal_grace_ends_at,
                "canto_access_suspended": user.canto_access_suspended,
                "joined_at": user.joined_at,
            }
        )

        return {
            "user": user_data,
            "payment": payment_details,
            "channels": [
                ChannelOutSchema.model_validate(channel).model_dump()
                for channel in channels
            ],
        }

    async def _get_subscription_details(
        self,
        subscription_id: str | None,
        customer_id: str | None,
    ) -> dict[str, object]:
        """
        Fetch subscription details from Stripe.

        Tries to get by subscription_id first, then falls back to customer lookup.

        Returns:
            Dict with subscription status, next_billing_date, cancel_at_period_end, etc.
        """
        subscription: dict = {}

        if subscription_id:
            try:
                subscription = await self.sdk.get_subscription(subscription_id)
            except stripe.InvalidRequestError as exc:
                logger.warning(
                    "Stripe subscription lookup skipped: subscription_id=%s reason=%s",
                    subscription_id,
                    str(exc),
                )
            except Exception:
                logger.warning(
                    "Failed to fetch subscription by ID: %s", subscription_id, exc_info=True
                )

        if not subscription and customer_id:
            try:
                subscription = await self.sdk.get_latest_subscription_for_customer(customer_id)
            except Exception:
                logger.warning(
                    "Failed to fetch subscription for customer: %s", customer_id, exc_info=True
                )

        if not subscription:
            return {}

        current_period_end = subscription.get("current_period_end")
        if not current_period_end:
            items = subscription.get("items")
            if isinstance(items, dict):
                items_data = items.get("data")
                if isinstance(items_data, list) and items_data:
                    current_period_end = items_data[0].get("current_period_end")

        logger.debug(
            "Subscription data for billing date: id=%s, current_period_end=%s",
            subscription.get("id"),
            current_period_end,
        )
        next_billing_date = self.sdk.unix_to_iso8601(current_period_end)

        return {
            "id": subscription.get("id"),
            "status": subscription.get("status"),
            "next_billing_date": next_billing_date,
            "cancel_at_period_end": subscription.get("cancel_at_period_end"),
        }

    async def create_checkout(
        self,
        price_id: str,
        email: str | None = None,
        quantity: int = 1,
        redirect_url: str | None = None,
        return_url: str | None = None,
        embedded: bool = False,
        signature: str | None = None,
        metadata: dict[str, str] | None = None,
    ) -> dict:
        """
        Create a Stripe checkout session.

        Args:
            price_id: Stripe price ID for the selected plan.
            email: Pre-fill the customer email in checkout.
            quantity: Number of items (for quantity-based pricing).
            redirect_url: URL to redirect to after successful payment (hosted mode).
            return_url: URL for embedded mode; Stripe appends ?session_id={CHECKOUT_SESSION_ID}.
            embedded: If True, use ui_mode='embedded' and return_url instead of success_url/cancel_url.
            signature: Signature captured before checkout.
            metadata: Additional metadata returned in webhook event data.object.metadata.

        Returns:
            Stripe checkout response (url for hosted, client_secret for embedded).
        """
        merged_metadata: dict[str, str] = {}
        if metadata:
            merged_metadata.update(metadata)
        if signature:
            merged_metadata["signature"] = signature

        return await self.sdk.create_checkout(
            price_id=price_id,
            email=email,
            quantity=quantity,
            success_url=redirect_url if not embedded else None,
            cancel_url=settings.FRONTEND_URL if not embedded else None,
            return_url=return_url if embedded else None,
            ui_mode="embedded" if embedded else None,
            metadata=merged_metadata or None,
        )

    async def get_price_details(self, price_id: str) -> dict[str, str | int | float | None]:
        normalized_price_id = (price_id or "").strip()
        if not normalized_price_id:
            raise AppError(
                message="price_id is required",
                error_code="invalid_price_id",
                status_code=HTTPStatus.BAD_REQUEST,
            )

        try:
            stripe_price = await self.sdk.get_price(normalized_price_id)
        except stripe.InvalidRequestError as exc:
            raise AppError(
                message=f"Price not found for price_id: {normalized_price_id}",
                error_code="price_not_found",
                status_code=HTTPStatus.NOT_FOUND,
            ) from exc
        except Exception as exc:
            raise PaymentProviderError(details=str(exc)) from exc

        unit_amount = stripe_price.get("unit_amount")
        amount = (
            round(unit_amount / 100, 2)
            if isinstance(unit_amount, int)
            else None
        )
        recurring = stripe_price.get("recurring")
        interval = recurring.get("interval") if isinstance(recurring, dict) else None

        plan = self._resolve_plan_from_interval_or_id(
            interval=interval,
            price_id=normalized_price_id,
        )
        return {"price": amount, "plan": plan}

    @staticmethod
    def _resolve_plan_from_interval_or_id(
        *,
        interval: str | None,
        price_id: str,
    ) -> str:
        normalized_interval = (interval or "").strip().lower()
        if normalized_interval == "month":
            return "monthly"
        if normalized_interval == "year":
            return "yearly"
        if price_id == settings.STRIPE_PRICE_ID_MONTHLY:
            return "monthly"
        if price_id == settings.STRIPE_PRICE_ID_YEARLY:
            return "yearly"
        return "enterprise"
