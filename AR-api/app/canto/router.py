from fastapi import APIRouter, Depends, Query

from app.auth.dependencies import get_current_user
from app.canto.enums import CantoDownloadSourceScope
from app.canto.schemas import CantoBasicGroupRemovalRequest
from app.canto.services import CantoService
from app.response import ArResponse
from app.user.models import UserModel
from .schemas import CantoDownloadHistoryQuery, CantoDownloadRequestQuery

router = APIRouter(prefix="/canto", tags=["canto"])
library_router = APIRouter(prefix="/library", tags=["library"])


@router.post("/basic-group/remove")
async def remove_user_from_canto_basic_group(
    payload: CantoBasicGroupRemovalRequest,
    service: CantoService = Depends(),
) -> ArResponse:
    result = await service.remove_user_from_basic_group(
        user_email=str(payload.email),
    )
    return ArResponse(data=result)


@router.get("/videos/{video_id}/download")
async def download_canto_video(
    video_id: str,
    source_scope: CantoDownloadSourceScope = Query(...),
    request_filters: str | None = Query(default=None),
    current_user: UserModel = Depends(get_current_user),
    service: CantoService = Depends(),
) -> ArResponse:
    query = CantoDownloadRequestQuery(
        source_scope=source_scope,
        request_filters=request_filters,
    )
    download_url = await service.download_video(
        video_id=video_id,
        current_user=current_user,
        query=query,
    )
    return ArResponse(data={"download_url": download_url})


@library_router.get("/downloads")
async def list_library_downloads(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=8, ge=1, le=100),
    current_user: UserModel = Depends(get_current_user),
    service: CantoService = Depends(),
) -> ArResponse:
    query = CantoDownloadHistoryQuery(page=page, limit=limit)
    result = await service.list_downloads(current_user=current_user, query=query)
    return ArResponse(data=result.model_dump())
