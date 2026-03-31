from datetime import datetime

from pydantic import BaseModel, Field, HttpUrl

from app.video_submission.enums import SubmissionStatus


class VideoSubmissionCreateSchema(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    video_url: str = Field(min_length=1, max_length=2048)
    tags: list[str] = Field(default_factory=list)
    category: str | None = None


class VideoSubmissionAdminUpdateSchema(BaseModel):
    status: SubmissionStatus
    admin_notes: str | None = None


class VideoSubmissionOutSchema(BaseModel):
    id: int
    title: str
    description: str | None
    video_url: str
    tags: list[str] | None
    category: str | None
    status: SubmissionStatus
    admin_notes: str | None
    created_at: datetime
    updated_at: datetime | None

    class Config:
        from_attributes = True
