from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.clerk_client import clerk_client
from app.db.database import get_db
from app.exceptionhandler import logger
from app.user.exceptions import (
    ClerkUserCreationFailed,
    UserAlreadyExists,
    UserCreationFailed,
)
from app.user.models import UserModel
from app.user.schemas import UserCreateSchema
from app.user.utils import extract_clerk_error_message


class UserService:
    """Service for user-related operations."""

    def __init__(self, db: AsyncSession = Depends(get_db)) -> None:
        self.db = db

    async def get_by_email(self, email: str) -> UserModel | None:
        """Get a user by email."""
        result = await self.db.execute(
            select(UserModel).where(UserModel.email == email)
        )
        return result.scalar_one_or_none()

    async def create(self, user_in: UserCreateSchema) -> UserModel:
        """
        Create a new user.
        
        This method:
        1. Creates a user in Clerk
        2. Creates a corresponding user record in the database
        
        Args:
            user_in: UserCreateSchema schema with email, first_name, last_name, password
        
        Returns:
            User object from database
        
        Raises:
            UserAlreadyExists: If user with email already exists
            ClerkUserCreationFailed: If Clerk user creation fails
            UserCreationFailed: If user creation fails for other reasons
        """
        # Check if user already exists by email
        existing_user = await self.get_by_email(user_in.email)
        if existing_user:
            raise UserAlreadyExists(message=f"User with email {user_in.email} already exists")

        # Create user in Clerk first
        # Use the password provided by the user
        try:
            clerk_user = await clerk_client.users.create_async(
                email_address=[user_in.email],
                first_name=user_in.first_name,
                last_name=user_in.last_name,
                password=user_in.password,
            )
            logger.debug("Clerk user created: %s", clerk_user.id if clerk_user else None)

        # Create user in database with Clerk user ID
            if clerk_user:
                user = UserModel(
                    clerk_user_id=clerk_user.id,
                    email=user_in.email,
                    first_name=user_in.first_name,
                    last_name=user_in.last_name,
                    account_type=user_in.account_type,
                    is_active=True,
                )
                self.db.add(user)
                await self.db.flush()
                await self.db.refresh(user)
                logger.info("Created database user: %s (%s)", user.id, user.email)
                return user
            else:
                raise ClerkUserCreationFailed(
                    details=f"Failed to create Clerk user: {clerk_user}"
                )

        except (UserAlreadyExists, ClerkUserCreationFailed):
            raise
        except Exception as e:
            error_message = extract_clerk_error_message(e)
            raise UserCreationFailed(
                message=error_message,
                details=str(e),
            ) from e