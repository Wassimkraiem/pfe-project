from pydantic import BaseModel, EmailStr

from app.user.enums import AccountType


class SignInRequestSchema(BaseModel):
    """Schema for user sign-in request."""

    email: EmailStr
    password: str


class SignInResponseSchema(BaseModel):
    """Schema for sign-in response with user data and token."""

    id: int
    clerk_user_id: str | None
    email: str
    first_name: str
    last_name: str
    account_type: AccountType
    is_active: bool
    token: str

    class Config:
        from_attributes = True
