import httpx
from clerk_backend_api.models.createsessionop import CreateSessionRequestBody
from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.clerk_client import clerk_client
from app.auth.exceptions import ClerkAuthenticationError, InvalidCredentials, UserNotActive
from app.auth.schemas import SignInRequestSchema, SignInResponseSchema
from app.core.config import settings
from app.db.database import get_db
from app.exceptionhandler import logger
from app.user.models import UserModel


class AuthService:
    """Service for authentication operations."""

    def __init__(self, db: AsyncSession = Depends(get_db)) -> None:
        self.db = db

    async def sign_in(self, credentials: SignInRequestSchema) -> SignInResponseSchema:
        """
        Authenticate user with email and password.

        This method:
        1. Finds the user by email in Clerk
        2. Verifies the password with Clerk
        3. Creates a Clerk session and retrieves a session JWT
        4. Returns user data from the database with the JWT (valid as Bearer token)

        Args:
            credentials: SignInRequestSchema with email and password

        Returns:
            SignInResponseSchema with user data and session JWT (Bearer token)

        Raises:
            InvalidCredentials: If email or password is incorrect
            UserNotActive: If user account is deactivated
            ClerkAuthenticationError: If Clerk service fails
        """
        email = credentials.email
        password = credentials.password

        try:
            # Find user in Clerk by email
            clerk_user_id = await self._find_clerk_user_by_email(email)

            if not clerk_user_id:
                logger.debug("No Clerk user found for email: %s", email)
                raise InvalidCredentials()

            # Verify password using Clerk's API
            await self._verify_password(clerk_user_id, password)

            # Get user from database
            user = await self._get_user_from_db(clerk_user_id)

            if not user:
                logger.warning(
                    "Clerk user %s exists but not found in database", clerk_user_id
                )
                raise InvalidCredentials()

            if not user.is_active:
                logger.info("Sign-in attempt for inactive user: %s", user.email)
                raise UserNotActive()

            # Create Clerk session and get JWT for API authentication (Bearer token)
            token = await self._create_session_jwt(clerk_user_id)

            logger.info("User signed in successfully: %s", user.email)

            return SignInResponseSchema(
                id=user.id,
                clerk_user_id=user.clerk_user_id,
                email=user.email,
                first_name=user.first_name,
                last_name=user.last_name,
                account_type=user.account_type,
                is_active=user.is_active,
                token=token,
            )

        except (InvalidCredentials, UserNotActive, ClerkAuthenticationError):
            raise
        except Exception as e:
            logger.exception("Sign-in error for email %s: %s", email, str(e))
            raise ClerkAuthenticationError(
                message="Failed to authenticate user",
                details=str(e),
            )

    async def _find_clerk_user_by_email(self, email: str) -> str | None:
        """
        Find a Clerk user by email address.

        Args:
            email: The email address to search for

        Returns:
            The Clerk user ID if found, None otherwise

        Raises:
            ClerkAuthenticationError: If Clerk API call fails
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.clerk.com/v1/users",
                headers={
                    "Authorization": f"Bearer {settings.CLERK_SECRET_KEY}",
                },
                params=[("email_address", email)],
            )

            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    return data[0].get("id")
                return None
            else:
                logger.error(
                    "Clerk users list failed: %s - %s",
                    response.status_code,
                    response.text,
                )
                raise ClerkAuthenticationError(
                    message="Failed to find user",
                    details=response.text,
                )

    async def _verify_password(self, clerk_user_id: str, password: str) -> bool:
        """
        Verify user password with Clerk's API.

        Args:
            clerk_user_id: The Clerk user ID
            password: The password to verify

        Returns:
            True if password is valid

        Raises:
            InvalidCredentials: If password is incorrect
            ClerkAuthenticationError: If Clerk API call fails
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://api.clerk.com/v1/users/{clerk_user_id}/verify_password",
                headers={
                    "Authorization": f"Bearer {settings.CLERK_SECRET_KEY}",
                    "Content-Type": "application/json",
                },
                json={"password": password},
            )

            if response.status_code == 200:
                data = response.json()
                if data.get("verified"):
                    return True
                raise InvalidCredentials()
            elif response.status_code in (422, 400):
                raise InvalidCredentials()
            else:
                logger.error(
                    "Clerk verify_password failed: %s - %s",
                    response.status_code,
                    response.text,
                )
                raise ClerkAuthenticationError(
                    message="Password verification failed",
                    details=response.text,
                )

    async def _create_session_jwt(self, clerk_user_id: str) -> str:
        """
        Create a Clerk session and return a session JWT for API authentication.

        The returned JWT can be used as Bearer token for protected endpoints.
        It is validated against Clerk's JWKS by fastapi_clerk_auth.

        Args:
            clerk_user_id: The Clerk user ID

        Returns:
            The session JWT string (valid Bearer token)

        Raises:
            ClerkAuthenticationError: If session or token creation fails
        """
        try:
            session = await clerk_client.sessions.create_async(
                request=CreateSessionRequestBody(user_id=clerk_user_id),
            )
            if not session or not session.id:
                raise ClerkAuthenticationError(
                    message="Failed to create session",
                    details="No session returned from Clerk",
                )

            token_response = await clerk_client.sessions.create_token_async(
                session_id=session.id,
                expires_in_seconds=settings.CLERK_SESSION_TOKEN_EXPIRES_IN_SECONDS,
            )
            if not token_response or not token_response.jwt:
                raise ClerkAuthenticationError(
                    message="Failed to create session token",
                    details="No JWT in response",
                )

            return token_response.jwt
        except ClerkAuthenticationError:
            raise
        except Exception as e:
            logger.exception(
                "Clerk session/token creation failed for user %s: %s",
                clerk_user_id,
                str(e),
            )
            raise ClerkAuthenticationError(
                message="Failed to create session token",
                details=str(e),
            ) from e

    async def _get_user_from_db(self, clerk_user_id: str) -> UserModel | None:
        """
        Get user from database by Clerk user ID.

        Args:
            clerk_user_id: The Clerk user ID

        Returns:
            UserModel if found, None otherwise
        """
        result = await self.db.execute(
            select(UserModel).where(UserModel.clerk_user_id == clerk_user_id)
        )
        return result.scalar_one_or_none()
