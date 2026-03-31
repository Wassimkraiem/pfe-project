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
