from pydantic import BaseModel, Field


class IngestDocument(BaseModel):
    source: str = Field(min_length=1, max_length=255)
    text: str = Field(min_length=1)
    metadata: dict = Field(default_factory=dict)


class IngestRequest(BaseModel):
    documents: list[IngestDocument] = Field(min_length=1)
    replace_source: bool = False


class IngestResponse(BaseModel):
    documents_ingested: int
    chunks_created: int


class KnowledgeVectorItem(BaseModel):
    id: str
    source: str
    content: str
    metadata_json: dict = Field(default_factory=dict)
    score: float | None = None


class KnowledgeVectorListResponse(BaseModel):
    items: list[KnowledgeVectorItem] = Field(default_factory=list)
    next_offset: str | int | None = None


class KnowledgeVectorCreateRequest(BaseModel):
    source: str = Field(min_length=1, max_length=255)
    content: str = Field(min_length=1)
    metadata_json: dict = Field(default_factory=dict)


class KnowledgeVectorUpdateRequest(BaseModel):
    source: str | None = Field(default=None, min_length=1, max_length=255)
    content: str | None = Field(default=None, min_length=1)
    metadata_json: dict | None = None


class KnowledgeVectorDeleteResponse(BaseModel):
    id: str
    deleted: bool = True
