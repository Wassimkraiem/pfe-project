from fastapi import APIRouter, Depends

from app.auth.dependencies import get_current_user
from app.payment.services import PaymentService
from app.response import ArResponse
from app.user.models import UserModel
from app.user.schemas import UserCreateSchema, UserOutSchema
from app.user.services import UserService

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserOutSchema)
async def get_me(
    current_user: UserModel = Depends(get_current_user),
) -> ArResponse:
    """
    Get the current authenticated user's data.

    This endpoint requires a valid JWT token in the Authorization header.

    **Headers:**
    ```
    Authorization: Bearer <jwt_token>
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
            "is_active": true
        }
    }
    ```

    **Error Responses:**
    - 401: Unauthorized (invalid or missing token)
    - 404: User not found in database
    """
    return ArResponse(data=current_user)




@router.post("", response_model=UserOutSchema)
async def create_user(
    payload: UserCreateSchema,
    service: UserService = Depends(),
) -> ArResponse:
    """
    Create a new user.

    This endpoint:
    1. Creates a user in Clerk
    2. Creates a corresponding user record in the database

    **Request Body:**
    ```json
    {
        "email": "user@example.com",
        "first_name": "John",
        "last_name": "Doe",
        "password": "SecurePassword123!"
    }
    ```

    **Error Responses:**
    - 409: `user_already_exists` - User with this email already exists
    - 400: `clerk_user_creation_failed` - Failed to create user in auth service
    - 400: `user_creation_failed` - Failed to create user
    """
    user = await service.create(payload)
    return ArResponse(data=user)
