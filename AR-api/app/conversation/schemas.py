from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.conversation.enums import MessageRole


class ConversationCreateSchema(BaseModel):
    title: str | None = None
    user_message: str = Field(min_length=1)
    assistant_message: str = Field(min_length=1)
    assistant_payload: dict[str, Any] | None = None


class ConversationUpdateSchema(BaseModel):
    title: str = Field(min_length=1)


class MessagePairSchema(BaseModel):
    user_message: str = Field(min_length=1)
    assistant_message: str = Field(min_length=1)
    assistant_payload: dict[str, Any] | None = None


class MessageOutSchema(BaseModel):
    id: int
    role: MessageRole
    content: str
    payload: dict[str, Any] | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class ConversationOutSchema(BaseModel):
    id: int
    title: str | None
    created_at: datetime
    updated_at: datetime | None

    class Config:
        from_attributes = True


class ConversationDetailSchema(ConversationOutSchema):
    messages: list[MessageOutSchema] = []
