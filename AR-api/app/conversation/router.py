from fastapi import APIRouter, Depends, Query

from app.auth.dependencies import get_current_user
from app.conversation.schemas import (
    ConversationCreateSchema,
    ConversationDetailSchema,
    ConversationOutSchema,
    ConversationUpdateSchema,
    MessagePairSchema,
)
from app.conversation.services import ConversationService
from app.response import ArResponse
from app.user.models import UserModel

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.post("")
async def create_conversation(
    payload: ConversationCreateSchema,
    current_user: UserModel = Depends(get_current_user),
    service: ConversationService = Depends(),
):
    conversation = await service.create(current_user.id, payload)
    return ArResponse(
        data=ConversationOutSchema.model_validate(conversation).model_dump(),
        status_code=201,
    )


@router.get("")
async def list_conversations(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: UserModel = Depends(get_current_user),
    service: ConversationService = Depends(),
):
    conversations = await service.list_by_user(current_user.id, skip=skip, limit=limit)
    return ArResponse(
        data=[
            ConversationOutSchema.model_validate(c).model_dump()
            for c in conversations
        ]
    )


@router.get("/{conversation_id}")
async def get_conversation(
    conversation_id: int,
    current_user: UserModel = Depends(get_current_user),
    service: ConversationService = Depends(),
):
    conversation = await service.get_with_messages(conversation_id, current_user.id)
    return ArResponse(
        data=ConversationDetailSchema.model_validate(conversation).model_dump()
    )


@router.post("/{conversation_id}/messages")
async def add_messages(
    conversation_id: int,
    payload: MessagePairSchema,
    current_user: UserModel = Depends(get_current_user),
    service: ConversationService = Depends(),
):
    conversation = await service.add_messages(
        conversation_id, current_user.id, payload
    )
    return ArResponse(
        data=ConversationDetailSchema.model_validate(conversation).model_dump()
    )


@router.patch("/{conversation_id}")
async def update_conversation(
    conversation_id: int,
    payload: ConversationUpdateSchema,
    current_user: UserModel = Depends(get_current_user),
    service: ConversationService = Depends(),
):
    conversation = await service.update_title(
        conversation_id, current_user.id, payload
    )
    return ArResponse(
        data=ConversationOutSchema.model_validate(conversation).model_dump()
    )


@router.delete("/{conversation_id}")
async def delete_conversation(
    conversation_id: int,
    current_user: UserModel = Depends(get_current_user),
    service: ConversationService = Depends(),
):
    await service.delete(conversation_id, current_user.id)
    return ArResponse(data={"message": "Conversation deleted successfully"})
