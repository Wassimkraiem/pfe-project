from __future__ import annotations

from typing import Any

from app.core.config import settings

try:
    from qdrant_client import AsyncQdrantClient, models as qdrant_models
except ImportError:  # pragma: no cover - optional until dependencies are installed
    AsyncQdrantClient = None  # type: ignore[assignment]
    qdrant_models = None  # type: ignore[assignment]


def build_qdrant_client() -> Any:
    if AsyncQdrantClient is None:
        raise RuntimeError("qdrant-client is not installed")

    return AsyncQdrantClient(
        url=settings.qdrant_url,
        api_key=settings.qdrant_api_key or None,
        timeout=settings.qdrant_timeout_seconds,
    )


async def ensure_qdrant_collection(client: Any) -> None:
    if qdrant_models is None:
        raise RuntimeError("qdrant-client is not installed")

    exists = await client.collection_exists(settings.qdrant_collection_name)
    if not exists:
        await client.create_collection(
            collection_name=settings.qdrant_collection_name,
            vectors_config=qdrant_models.VectorParams(
                size=settings.qdrant_vector_size,
                distance=qdrant_models.Distance.COSINE,
            ),
        )

    await client.create_payload_index(
        collection_name=settings.qdrant_collection_name,
        field_name="source",
        field_schema=qdrant_models.PayloadSchemaType.KEYWORD,
        wait=True,
    )
