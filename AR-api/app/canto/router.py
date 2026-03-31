from fastapi import APIRouter, Depends

from app.canto.schemas import CantoBasicGroupRemovalRequest
from app.canto.services import CantoService
from app.response import ArResponse

router = APIRouter(prefix="/canto", tags=["canto"])


@router.post("/basic-group/remove")
async def remove_user_from_canto_basic_group(
    payload: CantoBasicGroupRemovalRequest,
    service: CantoService = Depends(),
):
    result = await service.remove_user_from_basic_group(
        user_email=str(payload.email),
    )
    return ArResponse(data=result)
