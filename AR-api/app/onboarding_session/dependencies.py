from fastapi import Depends

from app.onboarding_session.exceptions import OnboardingSessionNotFound
from app.onboarding_session.models import OnboardingSessionModel
from app.onboarding_session.services import OnboardingSessionService


async def get_onboarding_session_or_404(
    session_id: int,
    service: OnboardingSessionService = Depends(),
) -> OnboardingSessionModel:
    """Get an onboarding session by ID or raise 404."""
    session = await service.get_by_id(session_id)
    if session is None:
        raise OnboardingSessionNotFound()
    return session


async def get_onboarding_session_by_email_or_404(
    email: str,
    service: OnboardingSessionService = Depends(),
) -> OnboardingSessionModel:
    """Get an onboarding session by email or raise 404."""
    session = await service.get_by_email(email)
    if session is None:
        raise OnboardingSessionNotFound()
    
    return session


__all__ = ["get_onboarding_session_or_404", "get_onboarding_session_by_email_or_404"]
