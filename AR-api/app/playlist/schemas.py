from datetime import datetime

from pydantic import BaseModel, Field


class PlaylistCreateSchema(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    video_ids: list[str] = Field(default_factory=list)


class PlaylistUpdateSchema(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None


class PlaylistAddVideosSchema(BaseModel):
    video_ids: list[str] = Field(min_length=1)


class PlaylistVideoOutSchema(BaseModel):
    id: int
    video_id: str
    position: int
    created_at: datetime

    class Config:
        from_attributes = True


class PlaylistOutSchema(BaseModel):
    id: int
    title: str
    description: str | None
    created_at: datetime
    updated_at: datetime | None
    video_count: int = 0

    class Config:
        from_attributes = True


class PlaylistDetailSchema(PlaylistOutSchema):
    videos: list[PlaylistVideoOutSchema] = []
