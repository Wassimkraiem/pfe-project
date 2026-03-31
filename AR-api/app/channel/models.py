from sqlalchemy import BigInteger, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.channel.enums import Platform, VerificationStatus
from app.db.database import Base


class ChannelModel(Base):
    __tablename__ = "channels"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    platform: Mapped[Platform | None] = mapped_column(
        Enum(
            Platform,
            name="platform",
        ),
        nullable=True,
    )

    url: Mapped[str] = mapped_column(
        String,
        unique=True,
        nullable=False,
    )

    username: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    follower_count: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )

    verification_status: Mapped[VerificationStatus] = mapped_column(
        Enum(
            VerificationStatus,
            name="verificationstatus",
        ),
        default=VerificationStatus.PENDING,
        nullable=False,
    )
