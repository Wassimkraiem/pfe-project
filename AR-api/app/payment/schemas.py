from datetime import datetime
from typing import Any

from pydantic import BaseModel, EmailStr

from app.payment.enums import PaymentStatus, PaymentType, PlanType


class CheckoutRequestSchema(BaseModel):
    """Request schema for creating a checkout session."""

    email: EmailStr | None = None


class PaymentCreateSchema(BaseModel):
    """Schema for creating a payment record."""

    user_id: int
    order_id: str
    subscription_id: str | None = None
    customer_id: str | None = None
    status: PaymentStatus = PaymentStatus.PENDING
    payment_type: PaymentType
    amount: int = 0
    currency: str = "USD"
    plan_type: PlanType | None = None
    signature: str | None = None
    service_agreement_signed_at: datetime | None = None
    metadata_: dict[str, Any] | None = None


class PaymentSubscriptionOutSchema(BaseModel):
    id: str | None = None
    status: str | None = None
    status_formatted: str | None = None
    product_name: str | None = None
    variant_name: str | None = None
    renews_at: str | None = None
    ends_at: str | None = None
    trial_ends_at: str | None = None
    card_brand: str | None = None
    card_last_four: str | None = None
    update_payment_method_url: str | None = None
    customer_portal_url: str | None = None


class PaymentInvoiceOutSchema(BaseModel):
    id: str | None = None
    status: str | None = None
    status_formatted: str | None = None
    billing_reason: str | None = None
    currency: str | None = None
    total: int | None = None
    total_formatted: str | None = None
    card_brand: str | None = None
    card_last_four: str | None = None
    invoice_url: str | None = None
    created_at: str | None = None


class PaymentDetailsOutSchema(BaseModel):
    subscription: PaymentSubscriptionOutSchema
    invoices: list[PaymentInvoiceOutSchema]
