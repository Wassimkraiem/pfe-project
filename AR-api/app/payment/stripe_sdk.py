from datetime import UTC, datetime
from typing import Any

from .stripe_client import StripeClient


class StripeSDK:
    """Stripe service layer for checkout, portal, and subscriptions."""

    def __init__(self, client: StripeClient) -> None:
        self.client = client

    async def create_checkout(
        self,
        price_id: str,
        email: str | None = None,
        quantity: int = 1,
        success_url: str | None = None,
        cancel_url: str | None = None,
        return_url: str | None = None,
        ui_mode: str | None = None,
        metadata: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "mode": "subscription",
            "line_items": [
                {
                    "price": price_id,
                    "quantity": quantity,
                }
            ],
            "metadata": metadata or {},
        }
        if email:
            payload["customer_email"] = email
        if ui_mode == "embedded":
            payload["ui_mode"] = "embedded"
            if return_url:
                payload["return_url"] = return_url
        else:
            if success_url:
                payload["success_url"] = success_url
            if cancel_url:
                payload["cancel_url"] = cancel_url
        return await self.client.create_checkout_session(payload)

    async def create_customer_portal_session(
        self, customer_id: str, return_url: str
    ) -> dict[str, Any]:
        return await self.client.create_billing_portal_session(
            customer_id=customer_id, return_url=return_url
        )

    async def get_subscription(self, subscription_id: str | None) -> dict[str, Any]:
        if not subscription_id:
            return {}
        return await self.client.retrieve_subscription(subscription_id)

    async def get_price(self, price_id: str | None) -> dict[str, Any]:
        if not price_id:
            return {}
        return await self.client.retrieve_price(price_id)

    async def get_customer_id_by_email(self, email: str | None) -> str | None:
        if not email:
            return None
        customers = await self.client.list_customers_by_email(email=email, limit=10)
        data = customers.get("data")
        if not isinstance(data, list):
            return None
        for customer in data:
            if isinstance(customer, dict):
                customer_id = customer.get("id")
                if isinstance(customer_id, str) and customer_id.startswith("cus_"):
                    return customer_id
        return None

    async def get_latest_subscription_for_customer(
        self, customer_id: str | None
    ) -> dict[str, Any]:
        if not customer_id:
            return {}
        subscriptions = await self.client.list_subscriptions_for_customer(
            customer_id=customer_id,
            limit=10,
        )
        data = subscriptions.get("data")
        if not isinstance(data, list):
            return {}
        prioritized_statuses = ("active", "trialing", "past_due", "unpaid")
        for status in prioritized_statuses:
            for subscription in data:
                if isinstance(subscription, dict) and subscription.get("status") == status:
                    return subscription
        for subscription in data:
            if isinstance(subscription, dict):
                return subscription
        return {}

    def construct_webhook_event(self, payload: bytes, signature: str, secret: str) -> dict:
        return self.client.construct_webhook_event(
            payload=payload,
            signature=signature,
            secret=secret,
        )

    @staticmethod
    def unix_to_iso8601(timestamp: int | None) -> str | None:
        if not timestamp:
            return None
        return datetime.fromtimestamp(timestamp, tz=UTC).isoformat()
