from datetime import datetime

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class PlaylistModel(Base):
    __tablename__ = "playlists"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)

    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    videos: Mapped[list["PlaylistVideoModel"]] = relationship(
        back_populates="playlist",
        cascade="all, delete-orphan",
        order_by="PlaylistVideoModel.position.asc()",
    )


class PlaylistVideoModel(Base):
    __tablename__ = "playlist_videos"
    __table_args__ = (
        UniqueConstraint("playlist_id", "video_id", name="uq_playlist_video"),
    )

    playlist_id: Mapped[int] = mapped_column(
        ForeignKey("playlists.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    video_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    playlist: Mapped["PlaylistModel"] = relationship(back_populates="videos")
