from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.favorites.exceptions import FavoriteNotFound, VideoAlreadyFavorited
from app.favorites.models import UserFavoriteModel
from app.favorites.schemas import FavoriteAddSchema


class FavoritesService:
    def __init__(self, db: AsyncSession = Depends(get_db)) -> None:
        self.db = db

    async def add(self, user_id: int, payload: FavoriteAddSchema) -> UserFavoriteModel:
        existing = await self.db.execute(
            select(UserFavoriteModel).where(
                UserFavoriteModel.user_id == user_id,
                UserFavoriteModel.video_id == payload.video_id,
            )
        )
        if existing.scalar_one_or_none():
            raise VideoAlreadyFavorited()

        favorite = UserFavoriteModel(
            user_id=user_id,
            video_id=payload.video_id,
            video_title=payload.video_title,
            thumbnail_url=payload.thumbnail_url,
        )
        self.db.add(favorite)
        await self.db.flush()
        await self.db.refresh(favorite)
        return favorite

    async def remove(self, user_id: int, video_id: str) -> None:
        result = await self.db.execute(
            select(UserFavoriteModel).where(
                UserFavoriteModel.user_id == user_id,
                UserFavoriteModel.video_id == video_id,
            )
        )
        favorite = result.scalar_one_or_none()
        if not favorite:
            raise FavoriteNotFound()
        await self.db.delete(favorite)
        await self.db.flush()

    async def list_by_user(
        self, user_id: int, skip: int = 0, limit: int = 50
    ) -> list[UserFavoriteModel]:
        result = await self.db.execute(
            select(UserFavoriteModel)
            .where(UserFavoriteModel.user_id == user_id)
            .order_by(UserFavoriteModel.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_status(self, user_id: int, video_id: str) -> bool:
        result = await self.db.execute(
            select(UserFavoriteModel).where(
                UserFavoriteModel.user_id == user_id,
                UserFavoriteModel.video_id == video_id,
            )
        )
        return result.scalar_one_or_none() is not None

    async def get_favorited_ids(self, user_id: int) -> list[str]:
        result = await self.db.execute(
            select(UserFavoriteModel.video_id).where(
                UserFavoriteModel.user_id == user_id
            )
        )
        return list(result.scalars().all())
