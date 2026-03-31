from enum import Enum


class PaymentStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


class PaymentProvider(str, Enum):
    STRIPE = "stripe"


class PaymentType(str, Enum):
    CUSTOM_QUOTE = "custom_quote"
    SUBSCRIPTION = "subscription"


class PlanType(str, Enum):
    MONTHLY = "monthly"
    ANNUAL = "annual"
    ENTERPRISE = "enterprise"