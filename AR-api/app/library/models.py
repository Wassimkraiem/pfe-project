from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base
from app.library.enums import LibraryDownloadSourceScope


class LibraryDownloadEventModel(Base):
    __tablename__ = "library_download_events"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    asset_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    thumbnail_url: Mapped[str | None] = mapped_column(String, nullable=True)
    category: Mapped[str] = mapped_column(String, nullable=False)
    source_scope: Mapped[LibraryDownloadSourceScope] = mapped_column(
        Enum(
            LibraryDownloadSourceScope,
            name="librarydownloadsourcescope",
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
    )
    request_filters: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default="{}",
    )
    downloaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    
        server_default=func.now(),
    )
