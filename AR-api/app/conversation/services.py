from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.conversation.enums import MessageRole
from app.conversation.exceptions import ConversationForbidden, ConversationNotFound
from app.conversation.models import ConversationMessageModel, ConversationModel
from app.conversation.schemas import (
    ConversationCreateSchema,
    ConversationUpdateSchema,
    MessagePairSchema,
)
from app.db.database import get_db


class ConversationService:

    def __init__(self, db: AsyncSession = Depends(get_db)) -> None:
        self.db = db

    async def create(
        self, user_id: int, payload: ConversationCreateSchema
    ) -> ConversationModel:
        title = payload.title or payload.user_message[:80]
        conversation = ConversationModel(user_id=user_id, title=title)
        self.db.add(conversation)
        await self.db.flush()

        self.db.add(
            ConversationMessageModel(
                conversation_id=conversation.id,
                role=MessageRole.USER,
                content=payload.user_message,
            )
        )
        self.db.add(
            ConversationMessageModel(
                conversation_id=conversation.id,
                role=MessageRole.ASSISTANT,
                content=payload.assistant_message,
                payload=payload.assistant_payload,
            )
        )
        await self.db.flush()
        await self.db.refresh(conversation)
        return conversation

    async def list_by_user(
        self, user_id: int, skip: int = 0, limit: int = 20
    ) -> list[ConversationModel]:
        result = await self.db.execute(
            select(ConversationModel)
            .where(ConversationModel.user_id == user_id)
            .order_by(ConversationModel.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_with_messages(
        self, conversation_id: int, user_id: int
    ) -> ConversationModel:
        result = await self.db.execute(
            select(ConversationModel)
            .options(selectinload(ConversationModel.messages))
            .where(ConversationModel.id == conversation_id)
        )
        conversation = result.scalar_one_or_none()
        if not conversation:
            raise ConversationNotFound()
        if conversation.user_id != user_id:
            raise ConversationForbidden()
        return conversation

    async def add_messages(
        self, conversation_id: int, user_id: int, payload: MessagePairSchema
    ) -> ConversationModel:
        conversation = await self.get_with_messages(conversation_id, user_id)
        self.db.add(
            ConversationMessageModel(
                conversation_id=conversation.id,
                role=MessageRole.USER,
                content=payload.user_message,
            )
        )
        self.db.add(
            ConversationMessageModel(
                conversation_id=conversation.id,
                role=MessageRole.ASSISTANT,
                content=payload.assistant_message,
                payload=payload.assistant_payload,
            )
        )
        await self.db.flush()
        await self.db.refresh(conversation)
        result = await self.db.execute(
            select(ConversationModel)
            .options(selectinload(ConversationModel.messages))
            .where(ConversationModel.id == conversation.id)
        )
        return result.scalar_one()

    async def update_title(
        self, conversation_id: int, user_id: int, payload: ConversationUpdateSchema
    ) -> ConversationModel:
        result = await self.db.execute(
            select(ConversationModel).where(
                ConversationModel.id == conversation_id
            )
        )
        conversation = result.scalar_one_or_none()
        if not conversation:
            raise ConversationNotFound()
        if conversation.user_id != user_id:
            raise ConversationForbidden()
        conversation.title = payload.title
        await self.db.flush()
        await self.db.refresh(conversation)
        return conversation

    async def delete(self, conversation_id: int, user_id: int) -> None:
        result = await self.db.execute(
            select(ConversationModel).where(
                ConversationModel.id == conversation_id
            )
        )
        conversation = result.scalar_one_or_none()
        if not conversation:
            raise ConversationNotFound()
        if conversation.user_id != user_id:
            raise ConversationForbidden()
        await self.db.delete(conversation)
        await self.db.flush()
