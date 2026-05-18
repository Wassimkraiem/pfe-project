from datetime import datetime

from pydantic import BaseModel, Field


class FavoriteAddSchema(BaseModel):
    video_id: str = Field(min_length=1)
    video_title: str | None = None
    thumbnail_url: str | None = None


class FavoriteOutSchema(BaseModel):
    id: int
    video_id: str
    video_title: str | None
    thumbnail_url: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class FavoriteStatusSchema(BaseModel):
    video_id: str
    is_favorited: bool
