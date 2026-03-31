from fastapi import Depends

from app.channel.exceptions import ChannelNotFound
from app.channel.models import ChannelModel
from app.channel.services import ChannelService


async def get_channel_or_404(
    channel_id: int,
    service: ChannelService = Depends(),
) -> ChannelModel:
    """Get a channel by ID or raise 404."""
    channel = await service.get_by_id(channel_id)
    if channel is None:
        raise ChannelNotFound()
    return channel


__all__ = ["get_channel_or_404"]
