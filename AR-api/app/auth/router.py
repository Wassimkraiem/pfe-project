from fastapi import APIRouter, Depends

from app.auth.schemas import SignInRequestSchema, SignInResponseSchema
from app.auth.services import AuthService
from app.response import ArResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signin", response_model=SignInResponseSchema)
async def sign_in(
    payload: SignInRequestSchema,
    service: AuthService = Depends(),
) -> ArResponse:
    """
    Sign in a user with email and password.

    This endpoint:
    1. Verifies the user's credentials with Clerk
    2. Returns user data and an authentication token

    **Request Body:**
    ```json
    {
        "email": "user@example.com",
        "password": "SecurePassword123!"
    }
    ```

    **Response:**
    ```json
    {
        "status_code": 200,
        "message": "success",
        "data": {
            "id": 1,
            "clerk_user_id": "user_xxx",
            "email": "user@example.com",
            "first_name": "John",
            "last_name": "Doe",
            "account_type": "individual",
            "is_active": true,
            "token": "eyJhbGciOiJSUzI1NiIs..." 
        }
    }
    ```

    The `token` is a Clerk session JWT. Use it as Bearer token for protected endpoints:
    `Authorization: Bearer <token>`

    **Error Responses:**
    - 401: Invalid email or password
    - 403: User account is not active
    - 500: Authentication service error
    """
    user_data = await service.sign_in(payload)
    return ArResponse(data=user_data)
