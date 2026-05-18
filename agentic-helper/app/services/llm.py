from typing import TYPE_CHECKING, Literal

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

if TYPE_CHECKING:
    from app.models.knowledge import KnowledgeChunk


class RagRoute(BaseModel):
    route: Literal["RAG", "DIRECT"]


class ChunkGrade(BaseModel):
    id: str
    relevant: bool


class InterestRoute(BaseModel):
    interest: Literal["INTERESTED", "NOT_INTERESTED", "UNCLEAR"]


class ConversationRoute(BaseModel):
    route: Literal["CHAT_RAG", "VIDEO_SEARCH", "DIRECT", "OUT_OF_SCOPE", "SUPPORT_HANDOFF"]
    confidence: float = 0.0
    interest: Literal["INTERESTED", "NOT_INTERESTED", "UNCLEAR"] = "UNCLEAR"
    reason: str = ""


class LLMService:
    def __init__(self, model: ChatOpenAI, classifier_model: ChatOpenAI) -> None:
        self._model = model
        self._classifier_model = classifier_model

    async def ask_with_context(
        self,
        system_prompt: str,
        mode_prompt: str,
        history_text: str,
        context_text: str,
        question: str,
    ) -> str:
        prompt = ChatPromptTemplate.from_template(
            "{system_prompt}\n\n"
            "Mode instruction:\n{mode_prompt}\n\n"
            "Conversation so far:\n{history_text}\n\n"
            "Retrieved context:\n{context_text}\n\n"
            "User question: {question}\n"
            "Answer clearly and cite sources by source name when applicable."
        )
        chain = prompt | self._model | StrOutputParser()
        return await chain.ainvoke(
            {
                "system_prompt": system_prompt,
                "mode_prompt": mode_prompt,
                "history_text": history_text or "No prior messages.",
                "context_text": context_text or "No relevant context found.",
                "question": question,
            }
        )

    async def should_use_rag(
        self,
        classifier_prompt: str,
        question: str,
        history_text: str,
    ) -> bool:
        prompt = ChatPromptTemplate.from_template(
            "{classifier_prompt}\n\n"
            "Conversation so far:\n{history_text}\n\n"
            "User question:\n{question}\n\n"
            "Return JSON with one field `route` and value RAG or DIRECT."
        )
        structured_model = self._classifier_model.with_structured_output(RagRoute)
        chain = prompt | structured_model
        result = await chain.ainvoke(
            {
                "classifier_prompt": classifier_prompt,
                "history_text": history_text or "No prior messages.",
                "question": question,
            }
        )
        return result.route == "RAG"

    async def classify_interest(
        self,
        classifier_prompt: str,
        question: str,
        history_text: str,
    ) -> str:
        prompt = ChatPromptTemplate.from_template(
            "{classifier_prompt}\n\n"
            "Conversation so far:\n{history_text}\n\n"
            "User question:\n{question}\n\n"
            "Return JSON with one field `interest` and value INTERESTED, NOT_INTERESTED, or UNCLEAR."
        )
        structured_model = self._classifier_model.with_structured_output(InterestRoute)
        chain = prompt | structured_model
        result = await chain.ainvoke(
            {
                "classifier_prompt": classifier_prompt,
                "history_text": history_text or "No prior messages.",
                "question": question,
            }
        )
        return result.interest

    async def classify_conversation_route(
        self,
        router_prompt: str,
        question: str,
        history_text: str,
    ) -> ConversationRoute:
        prompt = ChatPromptTemplate.from_template(
            "{router_prompt}\n\n"
            "Conversation so far:\n{history_text}\n\n"
            "User question:\n{question}\n\n"
            "Return JSON with fields route, confidence, interest, and reason."
        )
        structured_model = self._classifier_model.with_structured_output(ConversationRoute)
        chain = prompt | structured_model
        result = await chain.ainvoke(
            {
                "router_prompt": router_prompt,
                "history_text": history_text or "No prior messages.",
                "question": question,
            }
        )
        result.confidence = max(0.0, min(1.0, float(result.confidence or 0.0)))
        return result

    async def rewrite_rag_query(
        self,
        rewrite_prompt: str,
        question: str,
        history_text: str,
    ) -> str:
        """Rewrite a conversational question into a retrieval-optimized standalone query."""
        prompt = ChatPromptTemplate.from_template(rewrite_prompt)
        chain = prompt | self._classifier_model | StrOutputParser()
        result = await chain.ainvoke(
            {
                "history_text": history_text or "No prior messages.",
                "question": question,
            }
        )
        return result.strip() or question

    async def rewrite_video_search_query(
        self,
        rewrite_prompt: str,
        query: str,
        question: str,
        history_text: str,
    ) -> str:
        """Expand an extracted video search query for better vector similarity over the video library."""
        prompt = ChatPromptTemplate.from_template(rewrite_prompt)
        chain = prompt | self._classifier_model | StrOutputParser()
        result = await chain.ainvoke(
            {
                "query": query,
                "question": question,
                "history_text": history_text or "No prior messages.",
            }
        )
        return result.strip() or query

    async def grade_chunks(
        self,
        grading_prompt: str,
        question: str,
        chunks: "list[KnowledgeChunk]",
    ) -> "list[KnowledgeChunk]":
        """Return only the chunks that are relevant to the question."""
        import asyncio

        structured_model = self._classifier_model.with_structured_output(ChunkGrade)

        async def _grade_one(chunk: "KnowledgeChunk") -> "KnowledgeChunk | None":
            prompt = ChatPromptTemplate.from_template(grading_prompt)
            chain = prompt | structured_model
            grade = await chain.ainvoke(
                {
                    "question": question,
                    "chunk_id": chunk.id,
                    "chunk_content": chunk.content,
                }
            )
            return chunk if grade.relevant else None

        results = await asyncio.gather(*[_grade_one(c) for c in chunks])
        return [c for c in results if c is not None]
