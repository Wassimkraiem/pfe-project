from datetime import datetime
from urllib.parse import urlparse

from pydantic import BaseModel, field_validator

from app.channel.enums import Platform, VerificationStatus


class ChannelCreateSchema(BaseModel):
    user_id: int
    url: str
    platform: Platform | None = None
    username: str | None = None
    follower_count: int | None = None
    verification_status: VerificationStatus | None = None

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate that the URL is properly formatted."""
        if not v:
            raise ValueError("URL cannot be empty")
        
        # Check if URL starts with http:// or https://
        if not v.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        
        # Parse and validate URL structure
        try:
            parsed = urlparse(v)
            if not parsed.netloc:
                raise ValueError("URL must have a valid domain")
            if not parsed.scheme in ("http", "https"):
                raise ValueError("URL must use http or https scheme")
        except Exception as e:
            raise ValueError(f"Invalid URL format: {str(e)}")
        
        return v


class ChannelOutSchema(BaseModel):
    id: int
    user_id: int
    platform: Platform | None
    url: str
    username: str | None
    follower_count: int | None
    verification_status: VerificationStatus
    created_at: datetime
    updated_at: datetime | None

    class Config:
        from_attributes = True


class ChannelUpdateSchema(BaseModel):
    platform: Platform | None = None
    url: str | None = None
    username: str | None = None
    follower_count: int | None = None
    verification_status: VerificationStatus | None = None
