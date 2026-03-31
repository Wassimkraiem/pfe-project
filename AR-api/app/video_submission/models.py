from sqlalchemy import Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base
from app.video_submission.enums import SubmissionStatus


class VideoSubmissionModel(Base):
    __tablename__ = "video_submissions"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)

    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    video_url: Mapped[str] = mapped_column(String(2048), nullable=False)

    tags: Mapped[list | None] = mapped_column(JSONB, nullable=True, default=list)

    category: Mapped[str | None] = mapped_column(String(255), nullable=True)

    status: Mapped[SubmissionStatus] = mapped_column(
        Enum(
            SubmissionStatus,
            name="submissionstatus",
            values_callable=lambda enum: [e.value for e in enum],
        ),
        nullable=False,
        default=SubmissionStatus.PENDING,
        server_default="pending",
    )

    admin_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
