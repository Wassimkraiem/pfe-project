from fastapi import Depends
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.database import get_db
from app.playlist.exceptions import PlaylistForbidden, PlaylistNotFound
from app.playlist.models import PlaylistModel, PlaylistVideoModel
from app.playlist.schemas import (
    PlaylistAddVideosSchema,
    PlaylistCreateSchema,
    PlaylistUpdateSchema,
)


class PlaylistService:
    def __init__(self, db: AsyncSession = Depends(get_db)) -> None:
        self.db = db

    async def _get_owned_playlist(
        self, playlist_id: int, user_id: int, *, load_videos: bool = False
    ) -> PlaylistModel:
        stmt = select(PlaylistModel).where(PlaylistModel.id == playlist_id)
        if load_videos:
            stmt = stmt.options(selectinload(PlaylistModel.videos))
        result = await self.db.execute(stmt)
        playlist = result.scalar_one_or_none()
        if not playlist:
            raise PlaylistNotFound()
        if playlist.user_id != user_id:
            raise PlaylistForbidden()
        return playlist

    async def create(
        self, user_id: int, payload: PlaylistCreateSchema
    ) -> PlaylistModel:
        playlist = PlaylistModel(
            user_id=user_id,
            title=payload.title,
            description=payload.description,
        )
        self.db.add(playlist)
        await self.db.flush()

        for idx, vid in enumerate(payload.video_ids):
            self.db.add(
                PlaylistVideoModel(
                    playlist_id=playlist.id, video_id=vid, position=idx
                )
            )
        await self.db.flush()
        await self.db.refresh(playlist)
        return playlist

    async def list_by_user(
        self, user_id: int, skip: int = 0, limit: int = 20
    ) -> list[dict]:
        count_sub = (
            select(func.count(PlaylistVideoModel.id))
            .where(PlaylistVideoModel.playlist_id == PlaylistModel.id)
            .correlate(PlaylistModel)
            .scalar_subquery()
        )
        stmt = (
            select(PlaylistModel, count_sub.label("video_count"))
            .where(PlaylistModel.user_id == user_id)
            .order_by(PlaylistModel.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        rows = result.all()
        return [
            {
                "id": pl.id,
                "title": pl.title,
                "description": pl.description,
                "created_at": pl.created_at,
                "updated_at": pl.updated_at,
                "video_count": cnt or 0,
            }
            for pl, cnt in rows
        ]

    async def get_with_videos(
        self, playlist_id: int, user_id: int
    ) -> PlaylistModel:
        return await self._get_owned_playlist(
            playlist_id, user_id, load_videos=True
        )

    async def update(
        self, playlist_id: int, user_id: int, payload: PlaylistUpdateSchema
    ) -> PlaylistModel:
        playlist = await self._get_owned_playlist(playlist_id, user_id)
        if payload.title is not None:
            playlist.title = payload.title
        if payload.description is not None:
            playlist.description = payload.description
        await self.db.flush()
        await self.db.refresh(playlist)
        return playlist

    async def delete(self, playlist_id: int, user_id: int) -> None:
        playlist = await self._get_owned_playlist(playlist_id, user_id)
        await self.db.delete(playlist)
        await self.db.flush()

    async def add_videos(
        self, playlist_id: int, user_id: int, payload: PlaylistAddVideosSchema
    ) -> PlaylistModel:
        playlist = await self._get_owned_playlist(
            playlist_id, user_id, load_videos=True
        )
        existing_ids = {v.video_id for v in playlist.videos}
        max_pos = max((v.position for v in playlist.videos), default=-1)

        for vid in payload.video_ids:
            if vid not in existing_ids:
                max_pos += 1
                self.db.add(
                    PlaylistVideoModel(
                        playlist_id=playlist.id, video_id=vid, position=max_pos
                    )
                )
                existing_ids.add(vid)

        await self.db.flush()
        result = await self.db.execute(
            select(PlaylistModel)
            .options(selectinload(PlaylistModel.videos))
            .where(PlaylistModel.id == playlist.id)
        )
        return result.scalar_one()

    async def remove_video(
        self, playlist_id: int, user_id: int, video_id: str
    ) -> None:
        await self._get_owned_playlist(playlist_id, user_id)
        await self.db.execute(
            delete(PlaylistVideoModel).where(
                PlaylistVideoModel.playlist_id == playlist_id,
                PlaylistVideoModel.video_id == video_id,
            )
        )
        await self.db.flush()
