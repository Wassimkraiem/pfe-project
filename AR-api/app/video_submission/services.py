from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.video_submission.enums import SubmissionStatus
from app.video_submission.exceptions import SubmissionForbidden, SubmissionNotFound
from app.video_submission.models import VideoSubmissionModel
from app.video_submission.schemas import (
    VideoSubmissionAdminUpdateSchema,
    VideoSubmissionCreateSchema,
)


class VideoSubmissionService:
    def __init__(self, db: AsyncSession = Depends(get_db)) -> None:
        self.db = db

    async def create(
        self, user_id: int, payload: VideoSubmissionCreateSchema
    ) -> VideoSubmissionModel:
        submission = VideoSubmissionModel(
            user_id=user_id,
            title=payload.title,
            description=payload.description,
            video_url=payload.video_url,
            tags=payload.tags,
            category=payload.category,
            status=SubmissionStatus.PENDING,
        )
        self.db.add(submission)
        await self.db.flush()
        await self.db.refresh(submission)
        return submission

    async def list_by_user(
        self, user_id: int, skip: int = 0, limit: int = 20
    ) -> list[VideoSubmissionModel]:
        result = await self.db.execute(
            select(VideoSubmissionModel)
            .where(VideoSubmissionModel.user_id == user_id)
            .order_by(VideoSubmissionModel.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_id(
        self, submission_id: int, user_id: int | None = None
    ) -> VideoSubmissionModel:
        result = await self.db.execute(
            select(VideoSubmissionModel).where(
                VideoSubmissionModel.id == submission_id
            )
        )
        submission = result.scalar_one_or_none()
        if not submission:
            raise SubmissionNotFound()
        if user_id is not None and submission.user_id != user_id:
            raise SubmissionForbidden()
        return submission

    async def list_all(
        self, skip: int = 0, limit: int = 50
    ) -> list[VideoSubmissionModel]:
        """Admin: list all submissions."""
        result = await self.db.execute(
            select(VideoSubmissionModel)
            .order_by(VideoSubmissionModel.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def admin_update(
        self, submission_id: int, payload: VideoSubmissionAdminUpdateSchema
    ) -> VideoSubmissionModel:
        result = await self.db.execute(
            select(VideoSubmissionModel).where(
                VideoSubmissionModel.id == submission_id
            )
        )
        submission = result.scalar_one_or_none()
        if not submission:
            raise SubmissionNotFound()
        submission.status = payload.status
        if payload.admin_notes is not None:
            submission.admin_notes = payload.admin_notes
        await self.db.flush()
        await self.db.refresh(submission)
        return submission
