from fastapi import APIRouter, Depends, Query
# from fastapi.responses import RedirectResponse

from app.auth.dependencies import get_current_user
from app.library.schemas import (
    LibraryDownloadRequestQuery,
    LibraryDownloadsQuery,
    LibraryVideoSearchParams,
)
from app.library.services import LibraryService
from app.response import ArResponse
from app.user.models import UserModel

router = APIRouter(prefix="/library", tags=["library"])


@router.get("/videos")
async def list_library_videos(
    search_keyword: str | None = Query(default=None),
    category: str | None = Query(default=None),
    tags: str | None = Query(default=None),
    uploaded_from: str | None = Query(default=None),
    uploaded_to: str | None = Query(default=None),
    duration_min: int | None = Query(default=None, ge=0),
    duration_max: int | None = Query(default=None, ge=0),
    filmed_on: str | None = Query(default=None),
    limit: int = Query(default=24, ge=1, le=100),
    page: int = Query(default=1, ge=1),
    sort_by: str = Query(default="time"),
    sort_direction: str = Query(default="descending"),
    current_user: UserModel = Depends(get_current_user),
    service: LibraryService = Depends(),
) -> ArResponse:
    _ = current_user
    params = LibraryVideoSearchParams(
        search_keyword=search_keyword,
        category=category,
        tags=tags,
        uploaded_from=uploaded_from,
        uploaded_to=uploaded_to,
        duration_min=duration_min,
        duration_max=duration_max,
        filmed_on=filmed_on,
        limit=limit,
        page=page,
        sort_by=sort_by,
        sort_direction=sort_direction,
    )
    result = await service.list_videos(params)
    return ArResponse(data=result.model_dump())


@router.get("/videos/{video_id}")
async def get_library_video(
    video_id: str,
    current_user: UserModel = Depends(get_current_user),
    service: LibraryService = Depends(),
) -> ArResponse:
    _ = current_user
    result = await service.get_video(video_id)
    return ArResponse(data=result.model_dump())


@router.get("/videos/{video_id}/download")
async def download_library_video(
    video_id: str,
    source_scope: str = Query(...),
    request_filters: str | None = Query(default=None),
    current_user: UserModel = Depends(get_current_user),
    service: LibraryService = Depends(),
) -> ArResponse:  # ) -> RedirectResponse:
    query = LibraryDownloadRequestQuery(
        source_scope=source_scope,
        request_filters=request_filters,
    )
    download_url = await service.download_video(  # location = await service.download_video(
        video_id=video_id,
        current_user=current_user,
        query=query,
    )
    return ArResponse(data={"download_url": download_url})
    # return RedirectResponse(
    #     url=location,
    #     status_code=302,
    #     headers={
    #         "Access-Control-Expose-Headers": "Location",
    #         "Cache-Control": "no-store",
    #     },
    # )


@router.get("/downloads")
async def list_library_downloads(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=8, ge=1, le=100),
    current_user: UserModel = Depends(get_current_user),
    service: LibraryService = Depends(),
) -> ArResponse:
    query = LibraryDownloadsQuery(page=page, limit=limit)
    result = await service.list_downloads(current_user=current_user, query=query)
    return ArResponse(data=result.model_dump())
