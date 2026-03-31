from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base
from app.user.enums import AccountType

if TYPE_CHECKING:
    from app.channel.models import ChannelModel


class UserModel(Base):
    __tablename__ = "users"

    clerk_user_id: Mapped[str | None] = mapped_column(String, unique=True, index=True, nullable=True)
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    first_name: Mapped[str] = mapped_column(String, nullable=False)
    last_name: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    renewal_failed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    renewal_grace_ends_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    canto_access_suspended: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    account_type: Mapped[AccountType] = mapped_column(
        Enum(
            AccountType,
            name="accounttype",
        ),
        nullable=False,
    )

    channels: Mapped[list["ChannelModel"]] = relationship(
        foreign_keys="[ChannelModel.user_id]",
        cascade="all, delete-orphan"
    )
    joined_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=True,
    )
