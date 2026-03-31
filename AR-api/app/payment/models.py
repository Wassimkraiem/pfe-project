from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base
from app.payment.enums import PaymentStatus, PaymentType, PlanType


class PaymentModel(Base):
    """
    Payment record for tracking Stripe checkout and subscription payments.

    Stores both one-time purchases and recurring subscription payments,
    along with the full webhook payload for audit purposes.
    """

    __tablename__ = "payments"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    order_id: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
        comment="Provider order/invoice ID",
    )

    subscription_id: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
        comment="Stripe subscription ID for recurring payments",
    )

    customer_id: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
        comment="Stripe customer ID",
    )

    status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus, name="paymentstatus"),
        default=PaymentStatus.PENDING,
        nullable=False,
    )

    payment_type: Mapped[PaymentType] = mapped_column(
        Enum(PaymentType, name="paymenttype"),
        nullable=False,
    )

    amount: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Amount in cents",
    )

    currency: Mapped[str] = mapped_column(
        String(3),
        default="USD",
        nullable=False,
    )

    plan_type: Mapped[PlanType | None] = mapped_column(
        Enum(PlanType, name="plantype", create_type=False),
        nullable=True,
        comment="The plan purchased with this payment",
    )

    signature: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        comment="Signature captured before checkout",
    )

    service_agreement_signed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp when service agreement was signed before checkout",
    )

    metadata_: Mapped[dict | None] = mapped_column(
        "metadata",
        JSONB,
        nullable=True,
        comment="Full webhook payload for audit",
    )
