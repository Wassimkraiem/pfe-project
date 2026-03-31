from pydantic import BaseModel, EmailStr

from app.user.enums import AccountType


class UserCreateSchema(BaseModel):
    """Schema for creating a new user."""
    email: EmailStr
    first_name: str
    last_name: str
    password: str  # User-provided password
    account_type: AccountType = AccountType.INDIVIDUAL


class UserOutSchema(BaseModel):
    id: int
    clerk_user_id: str | None
    email: str
    first_name: str
    last_name: str
    account_type: AccountType
    is_active: bool

    class Config:
        from_attributes = True