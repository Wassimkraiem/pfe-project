from fastapi import APIRouter, Depends, Query

from app.auth.dependencies import get_current_user
from app.playlist.schemas import (
    PlaylistAddVideosSchema,
    PlaylistCreateSchema,
    PlaylistDetailSchema,
    PlaylistOutSchema,
    PlaylistUpdateSchema,
    PlaylistVideoOutSchema,
)
from app.playlist.services import PlaylistService
from app.response import ArResponse
from app.user.models import UserModel

router = APIRouter(prefix="/playlists", tags=["playlists"])


@router.post("")
async def create_playlist(
    payload: PlaylistCreateSchema,
    current_user: UserModel = Depends(get_current_user),
    service: PlaylistService = Depends(),
):
    playlist = await service.create(current_user.id, payload)
    return ArResponse(
        data=PlaylistOutSchema.model_validate(playlist).model_dump(),
        status_code=201,
    )


@router.get("")
async def list_playlists(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: UserModel = Depends(get_current_user),
    service: PlaylistService = Depends(),
):
    playlists = await service.list_by_user(current_user.id, skip=skip, limit=limit)
    return ArResponse(data=playlists)


@router.get("/{playlist_id}")
async def get_playlist(
    playlist_id: int,
    current_user: UserModel = Depends(get_current_user),
    service: PlaylistService = Depends(),
):
    playlist = await service.get_with_videos(playlist_id, current_user.id)
    return ArResponse(
        data=PlaylistDetailSchema.model_validate(playlist).model_dump()
    )


@router.patch("/{playlist_id}")
async def update_playlist(
    playlist_id: int,
    payload: PlaylistUpdateSchema,
    current_user: UserModel = Depends(get_current_user),
    service: PlaylistService = Depends(),
):
    playlist = await service.update(playlist_id, current_user.id, payload)
    return ArResponse(
        data=PlaylistOutSchema.model_validate(playlist).model_dump()
    )


@router.delete("/{playlist_id}")
async def delete_playlist(
    playlist_id: int,
    current_user: UserModel = Depends(get_current_user),
    service: PlaylistService = Depends(),
):
    await service.delete(playlist_id, current_user.id)
    return ArResponse(data={"message": "Playlist deleted successfully"})


@router.post("/{playlist_id}/videos")
async def add_videos_to_playlist(
    playlist_id: int,
    payload: PlaylistAddVideosSchema,
    current_user: UserModel = Depends(get_current_user),
    service: PlaylistService = Depends(),
):
    playlist = await service.add_videos(playlist_id, current_user.id, payload)
    return ArResponse(
        data=PlaylistDetailSchema.model_validate(playlist).model_dump()
    )


@router.delete("/{playlist_id}/videos/{video_id}")
async def remove_video_from_playlist(
    playlist_id: int,
    video_id: str,
    current_user: UserModel = Depends(get_current_user),
    service: PlaylistService = Depends(),
):
    await service.remove_video(playlist_id, current_user.id, video_id)
    return ArResponse(data={"message": "Video removed from playlist"})
