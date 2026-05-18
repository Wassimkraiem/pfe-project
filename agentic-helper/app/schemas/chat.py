from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


ChatMode = Literal["auto", "default", "video_search"]


class ChatRequest(BaseModel):
    input_message: str = Field(min_length=1, max_length=8000)
    mode: ChatMode = Field(
        default="default",
        description="'auto' for routing, 'default' for RAG chatbot, 'video_search' for video search",
    )
    include_answer: bool = Field(
        default=False,
        description="When true, video search mode may return a natural-language answer in addition to UI actions.",
    )
    debug: bool = Field(default=False, description="Include downstream debug metadata when supported.")


class SourceItem(BaseModel):
    chunk_id: str | int
    source: str


class CitationItem(BaseModel):
    chunk_id: str | int
    source: str
    score: float | None = None
    excerpt: str = ""


class ChatResponse(BaseModel):
    answer: str
    interest_label: str = ""
    route: str = ""
    confidence: float | None = None
    sources: list[SourceItem] = Field(default_factory=list)
    citations: list[CitationItem] = Field(default_factory=list)
    videos: Optional[list[dict[str, Any]]] = None
    search_filters: Optional[dict[str, Any]] = None
    search_action: Optional[dict[str, Any]] = None
    search_url: Optional[str] = None
    total: Optional[int] = None
    next_offset: Optional[int] = None
    execution: Optional[dict[str, Any]] = None
    fallbacks_used: Optional[list[str]] = None
