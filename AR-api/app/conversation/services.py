from fastapi import Depends
from sqlalchemy import func, select
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
from app.user.models import UserModel


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

    async def admin_list_all(
        self, skip: int = 0, limit: int = 50
    ) -> list[dict]:
        message_stats = (
            select(
                ConversationMessageModel.conversation_id.label("conversation_id"),
                func.count(ConversationMessageModel.id).label("message_count"),
                func.max(ConversationMessageModel.created_at).label("last_message_at"),
            )
            .group_by(ConversationMessageModel.conversation_id)
            .subquery()
        )

        result = await self.db.execute(
            select(
                ConversationModel,
                UserModel,
                message_stats.c.message_count,
                message_stats.c.last_message_at,
            )
            .join(UserModel, UserModel.id == ConversationModel.user_id)
            .outerjoin(
                message_stats,
                message_stats.c.conversation_id == ConversationModel.id,
            )
            .order_by(
                ConversationModel.updated_at.desc().nullslast(),
                ConversationModel.created_at.desc(),
            )
            .offset(skip)
            .limit(limit)
        )

        rows: list[dict] = []
        for conversation, user, message_count, last_message_at in result.all():
            rows.append(
                {
                    "id": conversation.id,
                    "title": conversation.title,
                    "created_at": conversation.created_at,
                    "updated_at": conversation.updated_at,
                    "message_count": int(message_count or 0),
                    "last_message_at": last_message_at,
                    "user": {
                        "id": user.id,
                        "email": user.email,
                        "first_name": user.first_name,
                        "last_name": user.last_name,
                        "clerk_user_id": user.clerk_user_id,
                    },
                }
            )
        return rows

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

    async def admin_get_with_messages(self, conversation_id: int) -> dict:
        result = await self.db.execute(
            select(ConversationModel)
            .options(selectinload(ConversationModel.messages))
            .where(ConversationModel.id == conversation_id)
        )
        conversation = result.scalar_one_or_none()
        if not conversation:
            raise ConversationNotFound()

        user_result = await self.db.execute(
            select(UserModel).where(UserModel.id == conversation.user_id)
        )
        user = user_result.scalar_one_or_none()
        if not user:
            raise ConversationNotFound(message="Conversation owner not found")

        return {
            "id": conversation.id,
            "title": conversation.title,
            "created_at": conversation.created_at,
            "updated_at": conversation.updated_at,
            "message_count": len(conversation.messages),
            "last_message_at": conversation.messages[-1].created_at if conversation.messages else None,
            "messages": conversation.messages,
            "user": {
                "id": user.id,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "clerk_user_id": user.clerk_user_id,
            },
        }

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
