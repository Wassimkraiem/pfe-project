from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.canto.enums import CantoDownloadSourceScope
from app.db.database import Base


class DownloadedVideoModel(Base):
    __tablename__ = "downloaded_videos"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    video_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    video_title: Mapped[str] = mapped_column(String, nullable=False)
    thumbnail_url: Mapped[str | None] = mapped_column(String, nullable=True)
    source_scope: Mapped[CantoDownloadSourceScope] = mapped_column(
        Enum(
            CantoDownloadSourceScope,
            name="cantodownloadsourcescope",
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
    )
    request_filters: Mapped[dict[str, str]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default="{}",
    )
    downloaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )
