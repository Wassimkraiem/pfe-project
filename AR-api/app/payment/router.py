from fastapi import APIRouter, Depends

from app.auth.dependencies import get_current_user
from app.payment.services import PaymentService
from app.response import ArResponse
from app.user.models import UserModel

router = APIRouter(prefix="/payments", tags=["payments"])


@router.get("/me")
async def get_my_payment_details(
    current_user: UserModel = Depends(get_current_user),
    service: PaymentService = Depends(),
):
    details = await service.get_payment_details_for_user(current_user)
    return ArResponse(data=details)


@router.get("/prices/{price_id}")
async def get_price_details_by_price_id(
    price_id: str,
    service: PaymentService = Depends(),
):
    details = await service.get_price_details(price_id=price_id)
    return ArResponse(data=details)
