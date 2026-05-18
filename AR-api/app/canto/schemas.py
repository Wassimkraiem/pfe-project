from datetime import datetime
from math import ceil

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.canto.enums import CantoDownloadSourceScope


class CantoBasicGroupRemovalRequest(BaseModel):
    email: EmailStr


class CantoDownloadRequestQuery(BaseModel):
    source_scope: CantoDownloadSourceScope
    request_filters: str | None = None

    @field_validator("request_filters", mode="before")
    @classmethod
    def _strip_request_filters(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class CantoDownloadHistoryQuery(BaseModel):
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=8, ge=1, le=100)


class CantoDownloadHistoryItemOut(BaseModel):
    id: int
    video_id: str
    video_title: str
    thumbnail_url: str
    source_scope: CantoDownloadSourceScope
    request_filters: dict[str, str]
    downloaded_at: datetime


class CantoDownloadHistoryPaginationOut(BaseModel):
    page: int
    page_size: int
    total: int
    total_pages: int

    @classmethod
    def from_values(
        cls,
        *,
        page: int,
        page_size: int,
        total: int,
    ) -> "CantoDownloadHistoryPaginationOut":
        total_pages = ceil(total / page_size) if total > 0 else 0
        return cls(
            page=page,
            page_size=page_size,
            total=total,
            total_pages=total_pages,
        )


class CantoDownloadHistoryListOut(BaseModel):
    items: list[CantoDownloadHistoryItemOut]
    pagination: CantoDownloadHistoryPaginationOut
