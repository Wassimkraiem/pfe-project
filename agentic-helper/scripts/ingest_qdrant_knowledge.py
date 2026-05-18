from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from app.core.config import settings
from app.core.qdrant import build_qdrant_client, ensure_qdrant_collection
from app.schemas.rag import IngestDocument
from app.services.embeddings import EmbeddingService
from app.services.rag import RagService


async def _run(file_path: str, source: str, replace_source: bool) -> None:
    path = Path(file_path)
    if not path.exists():
        raise SystemExit(f"Knowledge file not found: {file_path}")

    qdrant_client = build_qdrant_client()
    await ensure_qdrant_collection(qdrant_client)

    try:
        rag = RagService(embeddings=EmbeddingService(), qdrant_client=qdrant_client)
        if path.suffix.lower() == ".xlsx":
            docs = rag.documents_from_excel(
                file_bytes=path.read_bytes(),
                source=source,
                question_column="Question",
                answer_column="Answer",
            )
        else:
            text = path.read_text(encoding="utf-8").strip()
            if not text:
                raise SystemExit(f"Knowledge file is empty: {file_path}")
            docs = [
                IngestDocument(
                    source=source,
                    text=text,
                    metadata={"file_path": str(path)},
                )
            ]

        if not docs:
            raise SystemExit(f"No ingestible documents found in: {file_path}")

        chunks_created = await rag.ingest_documents(
            docs=docs,
            replace_source=replace_source,
        )

        count_result = await qdrant_client.count(
            collection_name=settings.qdrant_collection_name,
        )
        print(f"source={source}")
        print(f"chunks_created={chunks_created}")
        if hasattr(count_result, "count"):
            print(f"collection_count={count_result.count}")
    finally:
        close = getattr(qdrant_client, "close", None)
        if close is not None:
            result = close()
            if hasattr(result, "__await__"):
                await result


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest a text or Excel knowledge file into Qdrant.")
    parser.add_argument(
        "--file",
        default="data/knowledge/bviral.txt",
        help="Path to the text file to ingest.",
    )
    parser.add_argument(
        "--source",
        default="bviral",
        help="Source name stored with the ingested chunks.",
    )
    parser.add_argument(
        "--replace-source",
        action="store_true",
        help="Delete existing points for the same source before ingesting.",
    )
    args = parser.parse_args()
    asyncio.run(_run(args.file, args.source, args.replace_source))


if __name__ == "__main__":
    main()
