from datetime import time as time_value
from datetime import date, datetime, timezone
from math import ceil

from pydantic import BaseModel, Field, field_validator, model_validator

from app.library.enums import (
    LibraryDownloadSourceScope,
    LibrarySortBy,
    LibrarySortDirection,
)
from app.library.exceptions import LibraryInvalidFilter

VIDEO_LIBRARY_CATEGORIES = (
    "Animals",
    "Beauty",
    "Boozy",
    "Comedy",
    "Cool",
    "Crafty",
    "DIY",
    "Fails",
    "Feels",
    "Food",
    "Gaming",
    "Gym",
    "Kids",
    "Music",
    "News and Culture",
    "Paranormal",
    "Razors",
    "Sports",
    "Travel & Hotel",
    "Weather",
    "ZoomCalls",
)


class LibraryVideoOut(BaseModel):
    id: str
    title: str
    filename: str
    description: str
    thumbnail_url: str
    preview_url: str
    width: int
    height: int
    aspect_ratio: str
    orientation: str
    duration_seconds: int
    file_size: int
    mime_type: str
    published_at: str
    uploaded_at: str
    filmed_on: str
    location: str
    credit: str
    tags: list[str]
    category: str


class LibraryVideoListPaginationOut(BaseModel):
    page: int
    page_size: int
    total: int
    total_pages: int
    has_more: bool

    @classmethod
    def from_values(cls, *, page: int, page_size: int, total: int) -> "LibraryVideoListPaginationOut":
        total_pages = ceil(total / page_size) if total > 0 else 0
        return cls(
            page=page,
            page_size=page_size,
            total=total,
            total_pages=total_pages,
            has_more=page * page_size < total,
        )


class LibraryVideoListOut(BaseModel):
    items: list[LibraryVideoOut]
    pagination: LibraryVideoListPaginationOut


class LibraryDownloadEventOut(BaseModel):
    id: int
    asset_id: str
    title: str
    thumbnail_url: str
    category: str
    source_scope: LibraryDownloadSourceScope
    request_filters: dict[str, str]
    downloaded_at: datetime


class LibraryDownloadPaginationOut(BaseModel):
    page: int
    page_size: int
    total: int
    total_pages: int


class LibraryDownloadListOut(BaseModel):
    items: list[LibraryDownloadEventOut]
    pagination: LibraryDownloadPaginationOut


class LibraryVideoSearchParams(BaseModel):
    search_keyword: str | None = None
    category: str | None = None
    tags: str | None = None
    uploaded_from: date | None = None
    uploaded_to: date | None = None
    duration_min: int | None = Field(default=None, ge=0)
    duration_max: int | None = Field(default=None, ge=0)
    filmed_on: str | None = None
    limit: int = Field(default=24, ge=1, le=100)
    page: int = Field(default=1, ge=1)
    sort_by: LibrarySortBy = LibrarySortBy.TIME
    sort_direction: LibrarySortDirection = LibrarySortDirection.DESCENDING

    @field_validator("search_keyword", "tags", mode="before")
    @classmethod
    def _strip_optional_string(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None

    @field_validator("category")
    @classmethod
    def _validate_category(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip()
        if not trimmed:
            return None
        if trimmed not in VIDEO_LIBRARY_CATEGORIES:
            raise LibraryInvalidFilter(
                message="Unknown library category",
                error_code="library_category_not_found",
            )
        return trimmed

    @model_validator(mode="after")
    def _validate_ranges(self) -> "LibraryVideoSearchParams":
        if (
            self.duration_min is not None
            and self.duration_max is not None
            and self.duration_min > self.duration_max
        ):
            raise LibraryInvalidFilter(
                message="duration_min must be less than or equal to duration_max",
                details={"duration_min": self.duration_min, "duration_max": self.duration_max},
            )
        if (
            self.uploaded_from is not None
            and self.uploaded_to is not None
            and self.uploaded_from > self.uploaded_to
        ):
            raise LibraryInvalidFilter(
                message="uploaded_from must be less than or equal to uploaded_to",
                details={
                    "uploaded_from": self.uploaded_from.isoformat(),
                    "uploaded_to": self.uploaded_to.isoformat(),
                },
            )
        if self.filmed_on is not None:
            self.filmed_on_range()
        return self

    def provider_start(self) -> int:
        return (self.page - 1) * self.limit

    def provider_keyword(self) -> str | None:
        return self.search_keyword

    def provider_tags(self) -> str | None:
        if not self.tags:
            return None
        tokens = [
            token.strip()
            for token in self.tags.split(",")
            if token.strip()
        ]
        return ",".join(tokens) or None

    def provider_duration_range(self) -> str | None:
        if self.duration_min is None and self.duration_max is None:
            return None
        minimum = 0 if self.duration_min is None else self.duration_min
        maximum = "" if self.duration_max is None else self.duration_max
        return f"{minimum}..{maximum}"

    def provider_uploaded_time_range(self) -> str | None:
        if self.uploaded_from is None and self.uploaded_to is None:
            return None
        start = ""
        end = ""
        if self.uploaded_from is not None:
            start_dt = datetime.combine(self.uploaded_from, time_value.min, tzinfo=timezone.utc)
            start = str(int(start_dt.timestamp()))
        if self.uploaded_to is not None:
            end_dt = datetime.combine(
                self.uploaded_to,
                time_value.max.replace(microsecond=0),
                tzinfo=timezone.utc,
            )
            end = str(int(end_dt.timestamp()))
        return f"{start}..{end}"

    def filmed_on_range(self) -> tuple[date | None, date | None]:
        if not self.filmed_on:
            return (None, None)
        parts = self.filmed_on.split("..", maxsplit=1)
        if len(parts) != 2:
            raise LibraryInvalidFilter(
                message="filmed_on must use the YYYY-MM-DD..YYYY-MM-DD range format",
                details={"filmed_on": self.filmed_on},
            )
        start_raw, end_raw = parts
        start = date.fromisoformat(start_raw) if start_raw else None
        end = date.fromisoformat(end_raw) if end_raw else None
        if start and end and start > end:
            raise LibraryInvalidFilter(
                message="filmed_on start must be less than or equal to filmed_on end",
                details={"filmed_on": self.filmed_on},
            )
        return (start, end)

    def requires_local_scan(self) -> bool:
        return self.filmed_on is not None

    def request_filters(self) -> dict[str, str]:
        filters: dict[str, str] = {}
        for key in (
            "search_keyword",
            "category",
            "tags",
            "uploaded_from",
            "uploaded_to",
            "duration_min",
            "duration_max",
            "filmed_on",
            "sort_by",
            "sort_direction",
        ):
            value = getattr(self, key)
            if value is None:
                continue
            if isinstance(value, date):
                filters[key] = value.isoformat()
            else:
                filters[key] = str(value)
        return filters


class LibraryDownloadsQuery(BaseModel):
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=8, ge=1, le=100)


class LibraryDownloadRequestQuery(BaseModel):
    source_scope: LibraryDownloadSourceScope
    request_filters: str | None = None

    @field_validator("request_filters", mode="before")
    @classmethod
    def _strip_request_filters(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None
