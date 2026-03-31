from sqlalchemy import Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.conversation.enums import MessageRole
from app.db.database import Base


class ConversationModel(Base):
    __tablename__ = "conversations"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    title: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    messages: Mapped[list["ConversationMessageModel"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="ConversationMessageModel.created_at.asc()",
    )


class ConversationMessageModel(Base):
    __tablename__ = "conversation_messages"

    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    role: Mapped[MessageRole] = mapped_column(
        Enum(MessageRole, name="messagerole"),
        nullable=False,
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    payload: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    conversation: Mapped["ConversationModel"] = relationship(
        back_populates="messages",
    )
