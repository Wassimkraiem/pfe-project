from enum import Enum


class OnboardingStep(str, Enum):
    PAGES = "pages"
    CHECKOUT = "checkout"
    ACCOUNT = "account"
    COMPLETED = "completed"


class PaymentFlowType(str, Enum):
    """Type of payment flow the user is going through during onboarding."""
    SUBSCRIPTION = "subscription"
    CUSTOM_QUOTE = "custom_quote"


class SubscriptionPlan(str, Enum):
    """Subscription billing cycle selected by the user (uppercase only)."""
    MONTHLY = "MONTHLY"
    YEARLY = "YEARLY"


class CustomQuoteTriggerFlag(str, Enum):
    """Custom quote trigger reasons for individual channels."""
    HIGH_FOLLOWERS = "HIGH_FOLLOWERS"
    UNSUPPORTED_PLATFORM = "UNSUPPORTED_PLATFORM"
    UNKNOWN_FOLLOWER_COUNT = "UNKNOWN_FOLLOWER_COUNT"
    SMS_API_ERROR = "SMS_API_ERROR"
