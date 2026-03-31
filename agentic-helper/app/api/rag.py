from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_rag_service, require_api_key
from app.schemas.rag import IngestRequest, IngestResponse
from app.services.rag import RagService

router = APIRouter(prefix="/rag", tags=["rag"], dependencies=[Depends(require_api_key)])


@router.post("/ingest", response_model=IngestResponse)
async def ingest(
    payload: IngestRequest,
    db: AsyncSession = Depends(get_db),
    rag_service: RagService = Depends(get_rag_service),
) -> IngestResponse:
    chunks_created = await rag_service.ingest_documents(
        db,
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
    db: AsyncSession = Depends(get_db),
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

    chunks_created = await rag_service.ingest_documents(db, docs=docs, replace_source=replace_source)
    return IngestResponse(documents_ingested=len(docs), chunks_created=chunks_created)
