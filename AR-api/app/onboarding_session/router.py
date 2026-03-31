import logging
from urllib.parse import urlparse
import json
from datetime import UTC, datetime

from fastapi import APIRouter, Depends

from app.auth.dependencies import require_admin_role
from app.core.config import settings
from app.email.tasks import (
    send_custom_quote_created_email_task,
    send_custom_quote_price_submitted_email_task,
    send_custom_quote_team_notification_email_task,
    send_setup_account_email_task,
    send_welcome_email_task,
)
from app.slack.tasks import send_slack_quote_notification_task
from app.email.enums import OnboardingEmailCode
from app.exceptionhandler import AppError
from app.onboarding_session.enums import OnboardingStep
from app.onboarding_session.exceptions import (
    CustomQuoteAlreadySubmitted,
    EmailSentToCompleteProcess,
    OnboardingSessionAlreadyExists,
    OnboardingSessionNotFound,
)
from app.onboarding_session.schemas import (
    AccountUpdateRequestSchema,
    ChannelAddRequestSchema,
    ChannelRemoveRequestSchema,
    CheckoutRequestSchema,
    CustomQuotePriceRequestSchema,
    get_empty_onboarding_session_data,
    OnboardingSessionByEmailRequestSchema,
    OnboardingSessionOutSchema,
)
from app.onboarding_session.services import OnboardingSessionService, serialize_custom_quote_session
from app.payment.services import PaymentService
from app.response import ArResponse
from app.user.services import UserService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/onboarding_sessions", tags=["onboarding_sessions"])


@router.post("/get-session-by-email")
async def get_onboarding_session_by_email(
    payload: OnboardingSessionByEmailRequestSchema,
    service: OnboardingSessionService = Depends(),
    user_service: UserService = Depends(),
):
    """
    Get an onboarding session by email address.

    This endpoint retrieves an existing onboarding session using the user's email.
    Useful for continuing an onboarding flow or checking session status.

    **Request Body:**
    ```json
    {
        "email": "user@example.com"
    }
    ```

    **Response (session exists):**
    ```json
    {
        "status_code": 200,
        "message": "success",
        "data": {
            "id": 1,
            "email": "user@example.com",
            "current_step": "PAGES",
            "payment_received": false,
            "session_details": {
                "pages": {
                    "channels": [
                        "https://instagram.com/wkhdai"
                    ]
                },
                "checkout": null,
                "account": null
            },
            "created_at": "2026-02-02T08:55:19.225957+00:00",
            "updated_at": null
        }
    }
    ```

    **Response (no session found):**
    Same structure as above with null/empty values for all fields except email.

    **Error Responses:**
    - 400: Invalid email format

    **Args:**
        payload: Request containing the email address

    **Returns:**
        ArResponse with OnboardingSession data or null if not found
    """
    user = await user_service.get_by_email(payload.email)
    if user:
        raise OnboardingSessionAlreadyExists()
    session = await service.get_by_email(payload.email)
    if not session:
        return ArResponse(data=get_empty_onboarding_session_data(payload.email))
    
    if session.price_id and session.custom_quote_submitted:
        if session.payment_received and session.current_step == OnboardingStep.ACCOUNT:
            session_details = session.session_details or {}
            account = session_details.get("account") or {}
            first_name = account.get("first_name")
            if not first_name:
                email_prefix = session.email.split("@")[0].split(".")[0]
                first_name = email_prefix.capitalize() if email_prefix else "there"
            recipient_name = (
                f"{account.get('first_name', '')} {account.get('last_name', '')}".strip()
                or None
            )
            parsed = urlparse(settings.FRONTEND_URL)
            base_url = f"{parsed.scheme}://{parsed.netloc}"
            complete_account_link = f"{base_url}/signup/?session_id={session.uuid}"

            try:
                await asyncio.to_thread(
                    send_setup_account_email_task.delay,
                    recipient_email=payload.email,
                    first_name=first_name,
                    complete_account_link=complete_account_link,
                    recipient_name=recipient_name,
                    session_uuid=str(session.uuid),
                    email_code=OnboardingEmailCode.ALREADY_PAID_ONBOARDING.value,
                )
            except Exception:
                logger.exception(
                    "Failed to enqueue setup-account email for session %s",
                    session.uuid,
                )
            raise EmailSentToCompleteProcess()
        return ArResponse(data=OnboardingSessionOutSchema.model_validate(session).model_dump())
    if session.custom_quote_submitted:
        raise CustomQuoteAlreadySubmitted()

    if session.payment_received and session.current_step == OnboardingStep.ACCOUNT:
        session_details = session.session_details or {}
        account = session_details.get("account") or {}
        first_name = account.get("first_name")
        if not first_name:
            email_prefix = session.email.split("@")[0].split(".")[0]
            first_name = email_prefix.capitalize() if email_prefix else "there"
        recipient_name = (
            f"{account.get('first_name', '')} {account.get('last_name', '')}".strip()
            or None
        )
        parsed = urlparse(settings.FRONTEND_URL)
        base_url = f"{parsed.scheme}://{parsed.netloc}"

        complete_account_link = f"{base_url}/signup/?session_id={session.uuid}"

        try:
            send_setup_account_email_task.delay(
                recipient_email=payload.email,
                first_name=first_name,
                complete_account_link=complete_account_link,
                recipient_name=recipient_name,
                session_uuid=str(session.uuid),
                email_code=OnboardingEmailCode.ALREADY_PAID_ONBOARDING.value,
            )
        except Exception:
            logger.exception(
                "Failed to enqueue setup-account email for session %s",
                session.uuid,
            )
        raise EmailSentToCompleteProcess()
        
    return ArResponse(
        data=OnboardingSessionOutSchema.model_validate(session).model_dump()
    )


@router.post("/create-custom-quote")
async def create_custom_quote(
    payload: OnboardingSessionByEmailRequestSchema,
    service: OnboardingSessionService = Depends(),
):
    session = await service.mark_custom_quote_submitted(payload.email)
    try:
        first_name = payload.email.split("@")[0]
        send_custom_quote_created_email_task.delay(
            recipient_email=payload.email,
            first_name=first_name,
            recipient_name=None,
            session_uuid=str(session.uuid),
        )
        session_details = session.session_details if isinstance(session.session_details, dict) else {}
        pages_data = session_details.get("pages", {}) if isinstance(session_details, dict) else {}
        channels = pages_data.get("channels", []) if isinstance(pages_data, dict) else []
        triggers = pages_data.get("custom_quote_triggers", []) if isinstance(pages_data, dict) else []
        send_custom_quote_team_notification_email_task.delay(
            submitter_email=payload.email,
            channels=list(channels) if isinstance(channels, list) else [],
            triggers=list(triggers) if isinstance(triggers, list) else [],
        )
        if settings.slack_enabled:
            send_slack_quote_notification_task.delay(
                email=payload.email,
                channels=list(channels) if isinstance(channels, list) else [],
                triggers=list(triggers) if isinstance(triggers, list) else [],
            )
    except Exception:
        logger.exception(
            "Failed to enqueue custom quote notifications for %s",
            payload.email,
        )
    return ArResponse(
        data=OnboardingSessionOutSchema.model_validate(session).model_dump()
    )


@router.post("/custom-quote/price")
async def set_custom_quote_price(
    payload: CustomQuotePriceRequestSchema,
    service: OnboardingSessionService = Depends(),
    _admin_guard: None = Depends(require_admin_role),
):
    """
    Set a Stripe price ID for a custom quote onboarding session.

    **Prerequisites:**
    - Session must exist for the provided email
    - custom_quote_submitted must be true
    - payment_received must be false

    Sends an email to the user notifying them that a price has been submitted.
    """
    session = await service.set_custom_quote_price_by_email(
        email=payload.email,
        price_id=payload.price_id,
    )
    first_name = payload.email.split("@")[0].split(".")[0].capitalize() or "there"
    finish_link = f"{settings.FRONTEND_URL}/signup"
    try:
        send_custom_quote_price_submitted_email_task.delay(
            recipient_email=payload.email,
            first_name=first_name,
            finish_link=finish_link,
            recipient_name=None,
            session_uuid=str(session.uuid),
        )
    except Exception:
        logger.exception(
            "Failed to enqueue custom quote price submitted email for %s",
            payload.email,
        )
    return ArResponse(
        data=OnboardingSessionOutSchema.model_validate(session).model_dump()
    )


@router.get("/custom-quotes/pending")
async def get_pending_custom_quotes(
    service: OnboardingSessionService = Depends(),
    _admin_guard: None = Depends(require_admin_role),
):
    """
    List onboarding sessions that submitted a custom quote and are not yet paid.
    Each item includes channel URLs and custom_quote_triggers at the top level.
    """
    sessions = await service.get_pending_custom_quotes()
    items = []
    for session in sessions:
        items.append(serialize_custom_quote_session(session))
    return ArResponse(data=items)


@router.get("/custom-quotes/status")
async def get_custom_quotes_status(
    service: OnboardingSessionService = Depends(),
    _admin_guard: None = Depends(require_admin_role),
):
    """
    List custom quote sessions by payment status.

    Returns two groups:
    - **pending_payment**: Price ID submitted by admin, user has not paid yet
    - **paid**: User has completed payment

    Each item includes channel URLs and custom_quote_triggers at the top level.
    """
    pending_payment_sessions = await service.get_custom_quotes_pending_payment()
    paid_sessions = await service.get_custom_quotes_paid()

    return ArResponse(
        data={
            "pending_payment": [
                serialize_custom_quote_session(s) for s in pending_payment_sessions
            ],
            "paid": [serialize_custom_quote_session(s) for s in paid_sessions],
        }
    )


@router.get("/{session_uuid}")
async def get_onboarding_session_by_uuid(
    session_uuid: str,
    service: OnboardingSessionService = Depends(),
):
    # to verify
    """
    Get an onboarding session by UUID.

    This endpoint retrieves an existing onboarding session using its UUID.
    Used by the frontend to load the account creation step after payment.

    **Request:**
    - Path parameter: `session_uuid` - UUID of the onboarding session

    **Response:**
    ```json
    {
        "status_code": 200,
        "message": "success",
        "data": {
            "id": 1,
            "uuid": "550e8400-e29b-41d4-a716-446655440000",
            "email": "user@example.com",
            "current_step": "account",
            "payment_received": true,
            "session_details": {
                "pages": {
                    "channels": [
                        "https://instagram.com/username"
                    ]
                },
                "checkout": {
                    "subscription_id": "sub_123",
                    "price_id": "price_456"
                },
                "account": null
            },
            "created_at": "2026-02-02T08:55:19.225957+00:00",
            "updated_at": "2026-02-02T09:00:00.000000+00:00"
        }
    }
    ```

    **Error Responses:**
    - **404 Not Found**: No session exists with the provided UUID

    **Args:**
        session_uuid: UUID of the onboarding session

    **Returns:**
        ArResponse with OnboardingSession data
    """
    session = await service.get_by_uuid(session_uuid)
    if not session:
        raise OnboardingSessionNotFound(
            message=f"No onboarding session found with UUID: {session_uuid}"
        )
    
    return ArResponse(
        data=OnboardingSessionOutSchema.model_validate(session).model_dump()
    )


@router.post("/channels/add")
async def add_channels_to_session(
    payload: ChannelAddRequestSchema,
    service: OnboardingSessionService = Depends(),
):
    """
    Add channel URLs to an onboarding session (creates session if it doesn't exist).

    This is the **first step** of the onboarding flow. If no session exists for the
    provided email, a new onboarding session is created with the channels.
    If a session already exists, the channels are added to the existing session.

    **Request Body:**
    ```json
    {
        "email": "user@example.com",
        "channels": [
            "https://instagram.com/username",
            "https://youtube.com/@channel"
        ]
    }
    ```

    **Response (new session created):**
    ```json
    {
        "status_code": 200,
        "message": "success",
        "data": {
            "id": 1,
            "email": "user@example.com",
            "current_step": "PAGES",
            "payment_received": false,
            "session_details": {
                "pages": {
                    "channels": [
                        "https://instagram.com/username",
                        "https://youtube.com/@channel"
                    ]
                },
                "checkout": null,
                "account": null
            },
            "created_at": "2026-02-02T08:55:19.225957+00:00",
            "updated_at": null
        }
    }
    ```

    **Error Responses:**
    - **400 Bad Request**: Session exists but is not in PAGES step
    - **409 Conflict**: One or more URLs already exist in the session

    **Typical Onboarding Flow:**
    1. **Add channels** (this endpoint) - Initialize session with email + channels
    2. **Payment** - User selects plan and completes payment (via checkout URL)
    3. **Webhook** - Payment confirmed, session moves to ACCOUNT step
    4. **Account setup** - User provides account details
    5. **Complete** - Finalize onboarding, create user/channel/payment records

    **Args:**
        payload: ChannelAddRequestSchema containing email and list of channel URLs

    **Returns:**
        ArResponse with created or updated OnboardingSession data
    """
    session = await service.add_channels(payload.email, payload.channels)
    return ArResponse(
        data=OnboardingSessionOutSchema.model_validate(session).model_dump()
    )


@router.post("/channels/remove")
async def remove_channel_from_session(
    payload: ChannelRemoveRequestSchema,
    service: OnboardingSessionService = Depends(),
):
    """
    Remove a single channel URL from an onboarding session.

    This endpoint removes a specific channel URL from the session during the
    PAGES step. Used when clicking the remove button on a channel in the UI.

    **Prerequisites:**
    - Session must exist for the provided email
    - Session must be in PAGES step
    - The channel URL must exist in the session

    **Request Body:**
    ```json
    {
        "email": "user@example.com",
        "channel": "https://instagram.com/username"
    }
    ```

    **Response:**
    ```json
    {
        "status_code": 200,
        "message": "success",
        "data": {
            "id": 1,
            "email": "user@example.com",
            "current_step": "PAGES",
            "payment_received": false,
            "session_details": {
                "pages": {
                    "channels": [
                        "https://youtube.com/@channel"
                    ]
                },
                "checkout": null,
                "account": null
            },
            "created_at": "2026-02-02T08:55:19.225957+00:00",
            "updated_at": "2026-02-02T09:05:00.000000+00:00"
        }
    }
    ```

    **Error Responses:**
    - **404 Not Found**: No session exists for email or channel URL not found
    - **400 Bad Request**: Session is not in PAGES step

    **Args:**
        payload: ChannelRemoveRequestSchema containing email and channel URL to remove

    **Returns:**
        ArResponse with updated OnboardingSession data
    """
    session = await service.remove_channel(payload.email, payload.channel)
    return ArResponse(
        data=OnboardingSessionOutSchema.model_validate(session).model_dump()
    )


@router.post("/checkout")
async def create_checkout_for_session(
    payload: CheckoutRequestSchema,
    onboarding_service: OnboardingSessionService = Depends(),
    payment_service: PaymentService = Depends(),
):
    """
    Create a checkout link for an onboarding session.

    This endpoint creates a Stripe checkout link with the quantity
    set to the number of channels added to the session. Stripe
    automatically calculates the total price (variant_price * quantity).

    The payment flow type is stored in the session to track whether the user
    is going through a regular subscription or a custom quote flow.

    **Prerequisites:**
    - Session must exist for the provided email
    - Session must be in PAGES step
    - Session must have at least one channel

    **Request Body:**
    ```json
    {
        "email": "user@example.com",
        "plan": "MONTHLY",
        "payment_flow_type": "subscription",
        "signature": "<string>",
        "embedded": true
    }
    ```

    **Fields:**
    - `plan`: `MONTHLY` or `YEARLY` - mapped to Stripe price ID
    - `payment_flow_type`: `subscription` (standard) or `custom_quote` (custom quote flow)
    - `signature`: Signature captured before checkout
    - `embedded`: If true (default), use Stripe embedded checkout; response includes `client_secret` instead of `checkout_url`

    **Response (hosted):**
    ```json
    {
        "data": {
            "checkout_url": "https://checkout.stripe.com/...",
            "channels_count": 3,
            "payment_flow_type": "subscription"
        }
    }
    ```

    **Response (embedded):**
    ```json
    {
        "data": {
            "client_secret": "cs_...",
            "channels_count": 3,
            "payment_flow_type": "subscription"
        }
    }
    ```

    **Error Responses:**
    - **404 Not Found**: No session exists for the provided email
    - **400 Bad Request**: Session is not in PAGES step or has no channels

    **Args:**
        payload: CheckoutRequestSchema containing email and payment flow type

    **Returns:**
        ArResponse with checkout URL, channels count, and payment flow type
    """
    from http import HTTPStatus

    session = await onboarding_service.get_by_email(payload.email)
    if not session:
        raise OnboardingSessionNotFound(
            message=f"No onboarding session found for email: {payload.email}"
        )

    if session.current_step != OnboardingStep.PAGES:
        raise AppError(
            message="Checkout can only be created during the PAGES step",
            error_code="invalid_step_for_checkout",
            status_code=HTTPStatus.BAD_REQUEST,
        )

    session_details = session.session_details or {}
    pages_data = session_details.get("pages", {})
    channels = pages_data.get("channels", [])

    if not channels:
        raise AppError(
            message="At least one channel is required before checkout",
            error_code="no_channels",
            status_code=HTTPStatus.BAD_REQUEST,
        )

    channels_count = len(channels)
    session_price_id = (session.price_id or "").strip()
    service_agreement_signed_at = datetime.now(UTC).isoformat()

    # Prefer a session-specific Stripe price id when available.
    # Fall back to plan-based defaults for standard onboarding.nro
    price_id = session_price_id
    if not price_id:
        price_id = (
            settings.STRIPE_PRICE_ID_YEARLY
            if payload.plan.value == "YEARLY"
            else settings.STRIPE_PRICE_ID_MONTHLY
        )
        if not price_id:
            price_id = settings.STRIPE_PRICE_ID_MONTHLY


    # Store payment flow type and price_id in checkout section
    await onboarding_service.set_checkout_payment_flow_type(
        email=payload.email,
        payment_flow_type=payload.payment_flow_type,
        price_id=price_id,
        signature=payload.signature,
        service_agreement_signed_at=service_agreement_signed_at,
    )

    # Build redirect URL with session UUID for post-payment account creation
    redirect_url = f"{settings.FRONTEND_URL}/signup/?session_id={session.uuid}"

    # For embedded mode: return_url where Stripe redirects after checkout.
    # Stripe replaces {CHECKOUT_SESSION_ID}; we add onboarding_session for frontend routing.
    return_url = (
        f"{settings.FRONTEND_URL}/return?session_id={{CHECKOUT_SESSION_ID}}&onboarding_session={session.uuid}"
        if payload.embedded
        else None
    )

    # Persist onboarding session UUID and channels for webhook reconciliation.
    checkout_custom_data = {
        "onboarding_session_uuid": str(session.uuid),
        "channels": json.dumps(channels),
        "service_agreement_signed_at": service_agreement_signed_at,
    }

    # Locked session pricing should not be multiplied by channel count.
    checkout_quantity = 1 if session_price_id else channels_count

    # Create checkout with quantity based on pricing mode.
    checkout_response = await payment_service.create_checkout(
        price_id=price_id,
        email=payload.email,
        quantity=checkout_quantity,
        redirect_url=redirect_url,
        return_url=return_url,
        embedded=payload.embedded,
        signature=payload.signature,
        metadata=checkout_custom_data,
    )

    response_data: dict[str, str | int] = {
        "channels_count": channels_count,
        "plan": payload.plan.value,
        "payment_flow_type": payload.payment_flow_type.value,
        "service_agreement_signed_at": service_agreement_signed_at,
    }
    if payload.embedded:
        response_data["client_secret"] = checkout_response.get("client_secret", "")
    else:
        response_data["checkout_url"] = checkout_response.get("url", "")

    return ArResponse(data=response_data)


@router.post("/{session_uuid}/account")
async def complete_onboarding_session(
    session_uuid: str,
    payload: AccountUpdateRequestSchema,
    service: OnboardingSessionService = Depends(),
):
    """
    Complete an onboarding session by saving account details and creating all records.

    This endpoint performs the final step of onboarding after payment:
    1. Saves account details to the session
    2. Creates Clerk user account
    3. Creates channel records for all provided URLs
    4. Creates payment record from checkout data
    5. Marks onboarding session as completed

    The session is identified by UUID from the URL path (provided after payment redirect).

    **Prerequisites:**
    - Session must exist for the provided UUID
    - Session must be in ACCOUNT step (payment must be received)
    - At least one channel URL must be in the session

    **Path Parameters:**
    - `session_uuid`: UUID of the onboarding session (from payment redirect URL)

    **Request Body:**
    ```json
    {
        "first_name": "John",
        "last_name": "Doe",
        "account_type": "individual",
        "company_name": null,
        "password": "SecurePass123!",
        "confirm_password": "SecurePass123!"
    }
    ```

    For business accounts:
    ```json
    {
        "first_name": "John",
        "last_name": "Doe",
        "account_type": "business",
        "company_name": "Acme Corp",
        "password": "SecurePass123!",
        "confirm_password": "SecurePass123!"
    }
    ```

    **Password Requirements:**
    - Minimum 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - At least one special character

    **Response:**
    ```json
    {
        "status_code": 200,
        "message": "success",
        "data": {
            "message": "Onboarding completed successfully",
            "user_id": 1,
            "channels_created": 2,
            "payment_id": 1
        }
    }
    ```

    **Error Responses:**
    - **404 Not Found**: No session exists for the provided UUID
    - **400 Bad Request**: Session is not in ACCOUNT step, missing channels, or payment not received
    - **422 Validation Error**: Password requirements not met or passwords don't match
    - **409 Conflict**: User already exists or channel URL already exists

    **Args:**
        session_uuid: UUID of the onboarding session from URL path
        payload: AccountUpdateRequestSchema with account details

    **Returns:**
        ArResponse with completion details including user_id, channels_created, payment_id
    """
    # First, save the account details
    await service.update_account_details_by_uuid(session_uuid, payload)

    # Then complete the onboarding (create user, channels, payment)
    result = await service.complete_onboarding_session_by_uuid(session_uuid)

    # Send welcome email
    session = await service.get_by_uuid(session_uuid)
    if session:
        recipient_name = f"{payload.first_name} {payload.last_name}".strip() or None
        try:
            send_welcome_email_task.delay(
                recipient_email=session.email,
                first_name=payload.first_name,
                recipient_name=recipient_name,
            )
        except Exception:
            logger.exception(
                "Failed to enqueue welcome email for session %s",
                session_uuid,
            )
    return ArResponse(
        data={
            "message": "Onboarding completed successfully",
            **result,
        }
    )
