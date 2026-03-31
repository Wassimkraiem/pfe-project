from collections import defaultdict
from io import BytesIO

from langchain_text_splitters import RecursiveCharacterTextSplitter
from openpyxl import load_workbook
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.knowledge import KnowledgeChunk
from app.schemas.rag import IngestDocument
from app.services.embeddings import EmbeddingService


class RagService:
    def __init__(self, embeddings: EmbeddingService) -> None:
        self._embeddings = embeddings
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.rag_chunk_size,
            chunk_overlap=settings.rag_chunk_overlap,
        )

    async def ingest_documents(
        self, db: AsyncSession, docs: list[IngestDocument], replace_source: bool = False
    ) -> int:
        if replace_source:
            by_source = defaultdict(list)
            for doc in docs:
                by_source[doc.source].append(doc)
            for source in by_source:
                await db.execute(delete(KnowledgeChunk).where(KnowledgeChunk.source == source))

        pending: list[KnowledgeChunk] = []
        chunks_created = 0

        for doc in docs:
            chunks = self._splitter.split_text(doc.text)
            if not chunks:
                continue
            vectors = await self._embeddings.embed_documents(chunks)
            for i, chunk in enumerate(chunks):
                pending.append(
                    KnowledgeChunk(
                        source=doc.source,
                        content=chunk,
                        metadata_json={**doc.metadata, "chunk_index": i},
                        embedding=vectors[i],
                    )
                )
            chunks_created += len(chunks)

        db.add_all(pending)
        await db.commit()
        return chunks_created

    async def retrieve(self, db: AsyncSession, query: str) -> list[KnowledgeChunk]:
        query_vector = await self._embeddings.embed_query(query)
        stmt = (
            select(KnowledgeChunk)
            .order_by(KnowledgeChunk.embedding.cosine_distance(query_vector))
            .limit(settings.rag_top_k)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    def documents_from_excel(
        self,
        file_bytes: bytes,
        source: str,
        question_column: str = "question",
        answer_column: str = "answer",
        sheet_name: str | None = None,
    ) -> list[IngestDocument]:
        wb = load_workbook(filename=BytesIO(file_bytes), read_only=True, data_only=True)
        ws = wb[sheet_name] if sheet_name else wb.active
        rows = ws.iter_rows(values_only=True)
        headers_row = next(rows, None)
        if headers_row is None:
            return []

        header_map: dict[str, int] = {}
        for i, value in enumerate(headers_row):
            if value is None:
                continue
            name = str(value).strip().lower()
            if name:
                header_map[name] = i

        q_col = question_column.strip().lower()
        a_col = answer_column.strip().lower()
        if q_col not in header_map or a_col not in header_map:
            return []

        q_idx = header_map[q_col]
        a_idx = header_map[a_col]

        docs: list[IngestDocument] = []
        for row_number, row in enumerate(rows, start=2):
            question = str(row[q_idx]).strip() if q_idx < len(row) and row[q_idx] is not None else ""
            answer = str(row[a_idx]).strip() if a_idx < len(row) and row[a_idx] is not None else ""
            if not question and not answer:
                continue
            text = f"Question: {question}\nAnswer: {answer}"
            docs.append(
                IngestDocument(
                    source=source,
                    text=text,
                    metadata={"row_number": row_number, "question": question},
                )
            )
        return docs
