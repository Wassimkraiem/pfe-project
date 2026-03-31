from datetime import datetime
from typing import Annotated
from urllib.parse import urlparse
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, HttpUrl, field_validator, model_validator
from pydantic.functional_validators import BeforeValidator

from app.onboarding_session.enums import OnboardingStep, PaymentFlowType, SubscriptionPlan
from app.payment.enums import PaymentType
from app.user.enums import AccountType


def validate_channel_url_format(value: str) -> str:
    """Validate channel URL format before Pydantic's HttpUrl conversion."""
    if not isinstance(value, str):
        return value

    if not value.startswith(("http://", "https://")):
        raise ValueError(f"URL must start with http:// or https://: {value}")

    parsed = urlparse(value)
    if not parsed.netloc:
        raise ValueError(f"URL must have a valid domain: {value}")

    if "@" in parsed.netloc:
        raise ValueError(f"URL contains invalid characters in domain: {value}")

    return value


ValidatedHttpUrl = Annotated[HttpUrl, BeforeValidator(validate_channel_url_format)]


# ============================================================================
# Session Details Validation Schemas
# ============================================================================


class OnboardingSessionPagesSchema(BaseModel):
    """Pages structure containing list of channel URLs."""
    channels: list[ValidatedHttpUrl] = []


class OnboardingSessionCheckoutSchema(BaseModel):
    """
    Checkout validation schema for session details.
    
    Contains data set during checkout creation and updated by the payment webhook.
    Maps to Stripe checkout/invoice webhook payloads.
    """
    # Set during checkout creation
    payment_flow_type: PaymentFlowType | None = None
    onboarding_session_uuid: str | None = None
    
    # Set by webhook (checkout.session.completed / invoice.payment_succeeded)
    invoice_id: str | None = None  # data.id - used as order_id
    subscription_id: str | None = None  # data.attributes.subscription_id
    customer_id: str | None = None  # data.attributes.customer_id
    price_id: str | None = None
    amount: int | None = None
    currency: str = "USD"
    payment_completed_at: datetime | None = None
    service_agreement_signed_at: datetime | None = None
    billing_reason: str | None = None
    user_email: EmailStr | None = None
    signature: str | None = None


class OnboardingSessionAccountSchema(BaseModel):
    """Account details schema for session details (without email)."""
    first_name: str
    last_name: str
    account_type: AccountType
    company_name: str | None = None
    password: str
    confirm_password: str

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Validate password meets security requirements."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not any(char.isupper() for char in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(char.islower() for char in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(char.isdigit() for char in v):
            raise ValueError("Password must contain at least one digit")
        return v

    @model_validator(mode="after")
    def validate_passwords_match(self) -> "OnboardingSessionAccountSchema":
        """Validate that password and confirm_password match."""
        if self.password != self.confirm_password:
            raise ValueError("Passwords do not match")
        return self

    @model_validator(mode="after")
    def validate_company_name_for_business(self) -> "OnboardingSessionAccountSchema":
        """Validate that company_name is provided for business accounts."""
        if self.account_type == AccountType.BUSINESS:
            if not self.company_name or not self.company_name.strip():
                raise ValueError("Company name is required for business accounts")
        return self


class OnboardingSessionDetailsSchema(BaseModel):
    """Structure for onboarding session details."""
    pages: OnboardingSessionPagesSchema | None = None
    checkout: OnboardingSessionCheckoutSchema | None = None
    account: OnboardingSessionAccountSchema | None = None


# ============================================================================
# API Request/Response Schemas
# ============================================================================


class OnboardingSessionOutSchema(BaseModel):
    """Output schema for onboarding session responses."""
    id: int
    uuid: UUID
    email: EmailStr
    payment_email: EmailStr | None = None
    current_step: OnboardingStep
    payment_received: bool
    last_reminder_sent_at: datetime | None = None
    reminders_count: int = 0
    requires_custom_quote: bool = False
    custom_quote_submitted: bool = False
    price_id: str | None = None
    session_details: dict  # Keep as dict for flexibility in output
    created_at: datetime
    updated_at: datetime | None

    class Config:
        from_attributes = True




class OnboardingSessionByEmailRequestSchema(BaseModel):
    email: EmailStr


class CustomQuotePriceRequestSchema(BaseModel):
    email: EmailStr
    price_id: str = Field(..., min_length=1)


class CheckoutRequestSchema(BaseModel):
    """Schema for creating a checkout session."""

    email: EmailStr
    plan: SubscriptionPlan = SubscriptionPlan.MONTHLY
    payment_flow_type: PaymentFlowType = PaymentFlowType.SUBSCRIPTION
    signature: str
    embedded: bool = True

    @field_validator("plan", mode="before")
    @classmethod
    def validate_plan(cls, v: str | SubscriptionPlan) -> str:
        """Accept only MONTHLY or YEARLY (case-insensitive). Reject any other value."""
        if isinstance(v, SubscriptionPlan):
            return v.value
        if isinstance(v, str):
            normalized = v.upper().strip()
            if normalized not in ("MONTHLY", "YEARLY"):
                raise ValueError('plan must be "MONTHLY" or "YEARLY"')
            return normalized
        raise ValueError('plan must be "MONTHLY" or "YEARLY"')


class ChannelAddRequestSchema(BaseModel):
    """Schema for adding channels to an onboarding session."""
    email: EmailStr
    channels: list[ValidatedHttpUrl] = Field(..., min_length=1)

    @field_validator("channels")
    @classmethod
    def validate_unique_channels(cls, v: list[HttpUrl]) -> list[HttpUrl]:
        """Ensure no duplicate URLs in the request."""
        urls_as_str = [str(url) for url in v]
        if len(urls_as_str) != len(set(urls_as_str)):
            raise ValueError("Duplicate channel URLs are not allowed in the same request")
        return v


class ChannelRemoveRequestSchema(BaseModel):
    """Schema for removing a channel from an onboarding session."""
    email: EmailStr
    channel: ValidatedHttpUrl


class AccountUpdateRequestSchema(BaseModel):
    """Schema for updating account details in an onboarding session (UUID from path)."""
    first_name: str
    last_name: str
    account_type: AccountType
    company_name: str | None = None
    password: str
    confirm_password: str

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """
        Validate password meets Clerk's security requirements.
        
        Requirements:
        - At least 8 characters
        - At least one uppercase letter
        - At least one lowercase letter
        - At least one digit
        - At least one special character
        """
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        
        if not any(char.isupper() for char in v):
            raise ValueError("Password must contain at least one uppercase letter")
        
        if not any(char.islower() for char in v):
            raise ValueError("Password must contain at least one lowercase letter")
        
        if not any(char.isdigit() for char in v):
            raise ValueError("Password must contain at least one digit")
        
        special_characters = "!@#$%^&*()_+-=[]{}|;:',.<>?/`~\"\\"
        if not any(char in special_characters for char in v):
            raise ValueError("Password must contain at least one special character (!@#$%^&*()_+-=[]{}|;:',.<>?/`~)")
        
        return v

    @model_validator(mode="after")
    def validate_passwords_match(self) -> "AccountUpdateRequestSchema":
        """Validate that password and confirm_password match."""
        if self.password != self.confirm_password:
            raise ValueError("Passwords do not match")
        return self

    @model_validator(mode="after")
    def validate_company_name_for_business(self) -> "AccountUpdateRequestSchema":
        """Validate that company_name is provided for business accounts."""
        if self.account_type == AccountType.BUSINESS:
            if not self.company_name or not self.company_name.strip():
                raise ValueError("Company name is required for business accounts")
        return self



def get_empty_onboarding_session_data(email: str) -> dict:
    """
    Return empty metadata with the same structure as OnboardingSessionOutSchema.

    Used when no onboarding session exists for the given email so the client
    receives a consistent response shape.

    Args:
        email: The email that was queried.

    Returns:
        Dict with same keys as OnboardingSessionOutSchema and null/empty values.
    """
    return {
        "email": email,
        "payment_email": None,
        "current_step": None,
        "payment_received": False,
        "last_reminder_sent_at": None,
        "reminders_count": 0,
        "requires_custom_quote": False,
        "session_details": {
            "pages": {
                "channels": [],
                "custom_quote_triggers": [],
            },
            "checkout": None,
            "account": None,
        }
    }
