from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.api.deps import get_rag_service, require_api_key
from app.schemas.rag import (
    IngestRequest,
    IngestResponse,
    KnowledgeVectorCreateRequest,
    KnowledgeVectorDeleteResponse,
    KnowledgeVectorItem,
    KnowledgeVectorListResponse,
    KnowledgeVectorUpdateRequest,
)
from app.services.rag import RagService

router = APIRouter(prefix="/rag", tags=["rag"], dependencies=[Depends(require_api_key)])


def _to_vector_item(item) -> KnowledgeVectorItem:
    return KnowledgeVectorItem(
        id=str(item.id),
        source=item.source,
        content=item.content,
        metadata_json=item.metadata_json,
        score=item.score,
    )


@router.post("/ingest", response_model=IngestResponse)
async def ingest(
    payload: IngestRequest,
    rag_service: RagService = Depends(get_rag_service),
) -> IngestResponse:
    chunks_created = await rag_service.ingest_documents(
        docs=payload.documents,
        replace_source=payload.replace_source,
    )
    return IngestResponse(documents_ingested=len(payload.documents), chunks_created=chunks_created)


@router.post("/ingest-excel", response_model=IngestResponse)
async def ingest_excel(
    file: UploadFile = File(...),
    source: str = Form(...),
    question_column: str = Form("question"),
    answer_column: str = Form("answer"),
    sheet_name: str | None = Form(None),
    replace_source: bool = Form(False),
    rag_service: RagService = Depends(get_rag_service),
) -> IngestResponse:
    filename = file.filename or ""
    if not filename.lower().endswith(".xlsx"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only .xlsx files are supported for excel ingestion",
        )

    content = await file.read()
    docs = rag_service.documents_from_excel(
        file_bytes=content,
        source=source,
        question_column=question_column,
        answer_column=answer_column,
        sheet_name=sheet_name,
    )
    if not docs:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No rows found or question/answer columns are missing",
        )

    chunks_created = await rag_service.ingest_documents(docs=docs, replace_source=replace_source)
    return IngestResponse(documents_ingested=len(docs), chunks_created=chunks_created)


@router.get("/vectors", response_model=KnowledgeVectorListResponse)
async def list_vectors(
    limit: int = 20,
    offset: str | None = None,
    source: str | None = None,
    rag_service: RagService = Depends(get_rag_service),
) -> KnowledgeVectorListResponse:
    items, next_offset = await rag_service.list_chunks(limit=limit, offset=offset, source=source)
    return KnowledgeVectorListResponse(
        items=[_to_vector_item(item) for item in items],
        next_offset=next_offset,
    )


@router.get("/vectors/search", response_model=KnowledgeVectorListResponse)
async def search_vectors(
    query: str,
    limit: int = 20,
    source: str | None = None,
    rag_service: RagService = Depends(get_rag_service),
) -> KnowledgeVectorListResponse:
    items = await rag_service.search_chunks(query=query, limit=limit, source=source)
    return KnowledgeVectorListResponse(items=[_to_vector_item(item) for item in items])


@router.get("/vectors/{point_id}", response_model=KnowledgeVectorItem)
async def get_vector(
    point_id: str,
    rag_service: RagService = Depends(get_rag_service),
) -> KnowledgeVectorItem:
    item = await rag_service.get_chunk(point_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="vector not found")
    return _to_vector_item(item)


@router.post("/vectors", response_model=KnowledgeVectorItem, status_code=status.HTTP_201_CREATED)
async def create_vector(
    payload: KnowledgeVectorCreateRequest,
    rag_service: RagService = Depends(get_rag_service),
) -> KnowledgeVectorItem:
    item = await rag_service.create_chunk(
        source=payload.source,
        content=payload.content,
        metadata_json=payload.metadata_json,
    )
    return _to_vector_item(item)


@router.put("/vectors/{point_id}", response_model=KnowledgeVectorItem)
async def update_vector(
    point_id: str,
    payload: KnowledgeVectorUpdateRequest,
    rag_service: RagService = Depends(get_rag_service),
) -> KnowledgeVectorItem:
    if payload.source is None and payload.content is None and payload.metadata_json is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="no update fields provided")

    item = await rag_service.update_chunk(
        point_id,
        source=payload.source,
        content=payload.content,
        metadata_json=payload.metadata_json,
    )
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="vector not found")
    return _to_vector_item(item)


@router.delete("/vectors/{point_id}", response_model=KnowledgeVectorDeleteResponse)
async def delete_vector(
    point_id: str,
    rag_service: RagService = Depends(get_rag_service),
) -> KnowledgeVectorDeleteResponse:
    deleted = await rag_service.delete_chunk(point_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="vector not found")
    return KnowledgeVectorDeleteResponse(id=point_id)
