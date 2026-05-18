from fastapi import APIRouter, Depends, Query

from app.auth.dependencies import get_current_user
from app.favorites.schemas import FavoriteAddSchema, FavoriteOutSchema, FavoriteStatusSchema
from app.favorites.services import FavoritesService
from app.response import ArResponse
from app.user.models import UserModel

router = APIRouter(prefix="/favorites", tags=["favorites"])


@router.get("/ids")
async def get_favorited_ids(
    current_user: UserModel = Depends(get_current_user),
    service: FavoritesService = Depends(),
):
    ids = await service.get_favorited_ids(current_user.id)
    return ArResponse(data={"video_ids": ids})


@router.get("")
async def list_favorites(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: UserModel = Depends(get_current_user),
    service: FavoritesService = Depends(),
):
    favorites = await service.list_by_user(current_user.id, skip=skip, limit=limit)
    return ArResponse(
        data=[FavoriteOutSchema.model_validate(f).model_dump() for f in favorites]
    )


@router.post("")
async def add_favorite(
    payload: FavoriteAddSchema,
    current_user: UserModel = Depends(get_current_user),
    service: FavoritesService = Depends(),
):
    favorite = await service.add(current_user.id, payload)
    return ArResponse(
        data=FavoriteOutSchema.model_validate(favorite).model_dump(),
        status_code=201,
    )


@router.get("/{video_id}/status")
async def get_favorite_status(
    video_id: str,
    current_user: UserModel = Depends(get_current_user),
    service: FavoritesService = Depends(),
):
    is_favorited = await service.get_status(current_user.id, video_id)
    return ArResponse(
        data=FavoriteStatusSchema(video_id=video_id, is_favorited=is_favorited).model_dump()
    )


@router.delete("/{video_id}")
async def remove_favorite(
    video_id: str,
    current_user: UserModel = Depends(get_current_user),
    service: FavoritesService = Depends(),
):
    await service.remove(current_user.id, video_id)
    return ArResponse(data={"removed": True})
