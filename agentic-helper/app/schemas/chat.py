from typing import Any, Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    input_message: str = Field(min_length=1, max_length=8000)
    mode: str = Field(default="default", description="'default' for RAG chatbot, 'video_search' for video search agent")


class SourceItem(BaseModel):
    chunk_id: int
    source: str


class ChatResponse(BaseModel):
    answer: str
    interest_label: str = ""
    sources: list[SourceItem] = Field(default_factory=list)
    videos: Optional[list[dict[str, Any]]] = None
    search_filters: Optional[dict[str, Any]] = None
    search_action: Optional[dict[str, Any]] = None
    search_url: Optional[str] = None
