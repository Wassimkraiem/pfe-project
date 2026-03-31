import asyncio
from typing import Optional

from fastapi import Depends, HTTPException, Request
from fastapi_clerk_auth import ClerkConfig, ClerkHTTPBearer, HTTPAuthorizationCredentials
from fastapi.security.utils import get_authorization_scheme_param
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.status import HTTP_403_FORBIDDEN

from app.core.config import settings
from app.auth.exceptions import AdminRoleRequired
from app.db.database import get_db
from app.user.exceptions import UserNotFound
from app.user.models import UserModel


class AsyncClerkHTTPBearer(ClerkHTTPBearer):
    """Subclass that moves synchronous JWKS validation off the event loop."""

    async def __call__(self, request: Request) -> Optional[HTTPAuthorizationCredentials]:
        authorization = request.headers.get("Authorization")
        scheme, credentials = get_authorization_scheme_param(authorization)
        if not (authorization and scheme and credentials):
            if self.auto_error:
                raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail="Forbidden")
            return None
        if scheme.lower() != "bearer":
            if self.auto_error:
                raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail="Forbidden")
            return None

        decoded_token = await asyncio.to_thread(self._decode_token, token=credentials)

        if not decoded_token and self.auto_error:
            raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail="Forbidden")
        response = HTTPAuthorizationCredentials(
            scheme=scheme, credentials=credentials, decoded=decoded_token
        )
        if self.add_state:
            request.state.clerk_auth = response
        return response


# Configure Clerk JWT validation
clerk_config = ClerkConfig(jwks_url=settings.CLERK_JWKS_URL)
clerk_auth_guard = AsyncClerkHTTPBearer(config=clerk_config)


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(clerk_auth_guard),
) -> str:
    """Extract and return the Clerk user ID from the validated JWT.

    Args:
        credentials: The validated JWT credentials from Clerk.

    Returns:
        The Clerk user ID (sub claim from the JWT).
    """
    return credentials.decoded.get("sub")


def _extract_role_from_claims(claims: dict) -> str | None:
    """Extract role from Clerk token claims across supported claim layouts."""
    metadata = claims.get("metadata")
    if isinstance(metadata, dict):
        role = metadata.get("role")
        if isinstance(role, str):
            return role

    public_metadata = claims.get("public_metadata")
    if isinstance(public_metadata, dict):
        role = public_metadata.get("role")
        if isinstance(role, str):
            return role

    role = claims.get("role")
    if isinstance(role, str):
        return role

    return None


async def require_admin_role(
    credentials: HTTPAuthorizationCredentials = Depends(clerk_auth_guard),
) -> None:
    """Ensure the authenticated Clerk session belongs to an admin user."""
    role = _extract_role_from_claims(credentials.decoded)
    if role != "admin":
        raise AdminRoleRequired()


async def get_current_user(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> UserModel:
    """Load the full user from database using Clerk user ID.

    Args:
        user_id: The Clerk user ID extracted from JWT.
        db: Async database session.

    Returns:
        The UserModel instance for the authenticated user.

    Raises:
        UserNotFound: If user not found in database.
    """
    result = await db.execute(
        select(UserModel).where(UserModel.clerk_user_id == user_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise UserNotFound(message="User not found")
    return user
