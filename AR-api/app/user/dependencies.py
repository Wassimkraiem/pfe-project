from fastapi import Depends

from app.user.exceptions import EmailAlreadyExists
from app.user.schemas import UserCreateSchema
from app.user.services import UserService


async def user_email_exists(
    payload: UserCreateSchema,
    service: UserService = Depends(),
) -> UserCreateSchema:
    """Validate that the email doesn't already exist."""
    user = await service.get_by_email(payload.email)
    if user:
        raise EmailAlreadyExists()
    return payload


__all__ = ["user_email_exists"]
