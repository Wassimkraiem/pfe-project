from fastapi import APIRouter, Depends

from app.auth.dependencies import get_current_user
from app.channel.dependencies import get_channel_or_404
from app.channel.exceptions import ChannelForbidden
from app.channel.models import ChannelModel
from app.user.models import UserModel
from app.channel.schemas import ChannelCreateSchema, ChannelOutSchema, ChannelUpdateSchema
from app.channel.services import ChannelService
from app.response import ArResponse

router = APIRouter(prefix="/channels", tags=["channels"])



@router.get("/{channel_id}")
async def get_channel(
    channel: ChannelModel = Depends(get_channel_or_404),
    current_user: UserModel = Depends(get_current_user),
):
    if channel.user_id != current_user.id:
        raise ChannelForbidden()
    return ArResponse(
        data=ChannelOutSchema.model_validate(channel).model_dump()
    )


@router.get("")
async def list_channels(
    current_user: UserModel = Depends(get_current_user),
    service: ChannelService = Depends(),
):
    # Only return channels for the authenticated user
    channels = await service.list_all(user_id=current_user.id)
    return ArResponse(
        data=[
            ChannelOutSchema.model_validate(c).model_dump() for c in channels
        ]
    )


@router.post("/{channel_id}")
async def update_channel(
    payload: ChannelUpdateSchema,
    channel: ChannelModel = Depends(get_channel_or_404),
    current_user: UserModel = Depends(get_current_user),
    service: ChannelService = Depends(),
):
    if channel.user_id != current_user.id:
        raise ChannelForbidden()
    updated = await service.update(channel, payload)
    return ArResponse(
        data=ChannelOutSchema.model_validate(updated).model_dump()
    )


@router.delete("/{channel_id}")
async def delete_channel(
    channel: ChannelModel = Depends(get_channel_or_404),
    current_user: UserModel = Depends(get_current_user),
    service: ChannelService = Depends(),
):
    if channel.user_id != current_user.id:
        raise ChannelForbidden()
    await service.delete(channel)
    return ArResponse(
        data={"message": "Channel deleted successfully"}
    )
