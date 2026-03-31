from typing import Sequence

from langchain_openai import OpenAIEmbeddings

from app.core.config import settings


class EmbeddingService:
    def __init__(self) -> None:
        self._client = OpenAIEmbeddings(
            api_key=settings.openai_api_key,
            model=settings.openai_embedding_model,
        )

    async def embed_query(self, text: str) -> list[float]:
        return await self._client.aembed_query(text)

    async def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        return await self._client.aembed_documents(list(texts))
