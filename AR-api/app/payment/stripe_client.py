from typing import Any

import stripe

from app.core.config import settings


class StripeClient:
    """Thin async wrapper around the Stripe Python SDK."""

    def __init__(self) -> None:
        stripe.api_key = settings.STRIPE_SECRET_KEY
        if settings.STRIPE_API_VERSION:
            stripe.api_version = settings.STRIPE_API_VERSION

    async def create_checkout_session(self, payload: dict[str, Any]) -> dict[str, Any]:
        session = await stripe.checkout.Session.create_async(**payload)
        return self._convert_stripe_object(session)

    async def create_billing_portal_session(
        self, customer_id: str, return_url: str
    ) -> dict[str, Any]:
        session = await stripe.billing_portal.Session.create_async(
            customer=customer_id,
            return_url=return_url,
        )
        return self._convert_stripe_object(session)

    async def retrieve_subscription(self, subscription_id: str) -> dict[str, Any]:
        subscription = await stripe.Subscription.retrieve_async(subscription_id)
        return self._convert_stripe_object(subscription)

    async def retrieve_price(self, price_id: str) -> dict[str, Any]:
        price = await stripe.Price.retrieve_async(price_id)
        return self._convert_stripe_object(price)

    async def list_customers_by_email(self, email: str, limit: int = 10) -> dict[str, Any]:
        customers = await stripe.Customer.list_async(
            email=email,
            limit=limit,
        )
        return self._convert_stripe_object(customers)

    async def list_subscriptions_for_customer(
        self, customer_id: str, limit: int = 10
    ) -> dict[str, Any]:
        subscriptions = await stripe.Subscription.list_async(
            customer=customer_id,
            limit=limit,
        )
        return self._convert_stripe_object(subscriptions)

    def _convert_stripe_object(self, obj: Any) -> Any:
        """Recursively convert Stripe objects to plain dicts."""
        if hasattr(obj, "to_dict_recursive"):
            return obj.to_dict_recursive()
        if hasattr(obj, "to_dict"):
            return obj.to_dict()
        if hasattr(obj, "_previous") and hasattr(obj, "keys"):
            return {k: self._convert_stripe_object(obj[k]) for k in obj.keys()}
        if isinstance(obj, dict):
            return {k: self._convert_stripe_object(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [self._convert_stripe_object(item) for item in obj]
        return obj

    def construct_webhook_event(self, payload: bytes, signature: str, secret: str) -> dict:
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=signature,
            secret=secret,
        )
        return self._convert_stripe_object(event)
