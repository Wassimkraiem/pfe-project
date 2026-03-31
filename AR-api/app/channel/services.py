from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.channel.exceptions import ChannelAlreadyExists
from app.db.database import get_db
from app.channel.models import ChannelModel
from app.channel.schemas import ChannelCreateSchema, ChannelUpdateSchema


class ChannelService:
    """Service for channel operations."""

    def __init__(self, db: AsyncSession = Depends(get_db)) -> None:
        self.db = db

    async def create(self, channel_in: ChannelCreateSchema) -> ChannelModel:
        """Create a new channel."""
        # Check if URL already exists
        existing_channel = await self.get_by_url(channel_in.url)
        if existing_channel:
            raise ChannelAlreadyExists(
                message=f"Channel with URL '{channel_in.url}' already exists"
            )

        channel = ChannelModel(**channel_in.model_dump())
        self.db.add(channel)
        await self.db.flush()
        await self.db.refresh(channel)
        return channel

    async def get_by_id(self, channel_id: int) -> ChannelModel | None:
        """Get a channel by ID."""
        result = await self.db.execute(
            select(ChannelModel).where(ChannelModel.id == channel_id)
        )
        return result.scalar_one_or_none()

    async def get_by_url(self, url: str) -> ChannelModel | None:
        """Get a channel by URL."""
        result = await self.db.execute(
            select(ChannelModel).where(ChannelModel.url == url)
        )
        return result.scalar_one_or_none()

    async def list_all(self, user_id: int | None = None) -> list[ChannelModel]:
        """List all channels, optionally filtered by user ID."""
        query = select(ChannelModel).order_by(ChannelModel.created_at.desc())
        if user_id is not None:
            query = query.where(ChannelModel.user_id == user_id)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update(
        self,
        channel: ChannelModel,
        update_data: ChannelUpdateSchema,
    ) -> ChannelModel:
        """Update a channel."""
        update_dict = update_data.model_dump(exclude_unset=True)
        for field, value in update_dict.items():
            setattr(channel, field, value)
        await self.db.flush()
        await self.db.refresh(channel)
        return channel

    async def delete(self, channel: ChannelModel) -> None:
        """Delete a channel."""
        await self.db.delete(channel)
        await self.db.flush()
