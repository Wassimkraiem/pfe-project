from __future__ import annotations

import logging
from typing import Any

from langchain_openai import ChatOpenAI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.chat import ChatMessage, ChatSession
from app.models.knowledge import KnowledgeChunk
from app.services.agent import run_video_search_agent
from app.services.llm import LLMService
from app.services.rag import RagService

logger = logging.getLogger(__name__)


class ChatService:
    def __init__(
        self,
        rag_service: RagService,
        llm_service: LLMService,
        system_prompt: str,
        rag_classifier_prompt: str,
        interest_classifier_prompt: str,
        interested_response_prompt: str,
        not_interested_response_prompt: str,
        video_filter_extractor_prompt: str,
        video_search_agent: Any = None,
        video_filter_llm: ChatOpenAI | None = None,
    ) -> None:
        self._rag = rag_service
        self._llm = llm_service
        self._system_prompt = system_prompt
        self._rag_classifier_prompt = rag_classifier_prompt
        self._interest_classifier_prompt = interest_classifier_prompt
        self._interested_response_prompt = interested_response_prompt
        self._not_interested_response_prompt = not_interested_response_prompt
        self._video_filter_extractor_prompt = video_filter_extractor_prompt
        self._video_search_agent = video_search_agent
        self._video_filter_llm = video_filter_llm

    async def _get_or_create_session(self, db: AsyncSession, user_id: str) -> ChatSession:
        stmt = select(ChatSession).where(ChatSession.user_id == user_id)
        result = await db.execute(stmt)
        session = result.scalars().first()
        if session is not None:
            return session

        session = ChatSession(user_id=user_id, title=f"{user_id} chat")
        db.add(session)
        await db.commit()
        await db.refresh(session)
        return session

    async def _get_history_text(self, db: AsyncSession, session: ChatSession) -> str:
        history_stmt = (
            select(ChatMessage)
            .where(ChatMessage.session_id == session.id)
            .order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc())
            .limit(settings.chat_memory_messages)
        )
        history_result = await db.execute(history_stmt)
        history = list(reversed(history_result.scalars().all()))
        return "\n".join([f"{msg.role}: {msg.content}" for msg in history])

    async def ask(
        self, db: AsyncSession, user_id: str, question: str
    ) -> tuple[str, list[KnowledgeChunk], str]:
        session = await self._get_or_create_session(db, user_id=user_id)
        history_text = await self._get_history_text(db, session)

        interest_label = await self._llm.classify_interest(
            classifier_prompt=self._interest_classifier_prompt,
            question=question,
            history_text=history_text,
        )
        if interest_label == "INTERESTED":
            use_rag = True
        elif interest_label == "NOT_INTERESTED":
            use_rag = False
        else:
            use_rag = await self._llm.should_use_rag(
                classifier_prompt=self._rag_classifier_prompt,
                question=question,
                history_text=history_text,
            )
        chunks = await self._rag.retrieve(db, question) if use_rag else []
        context = "\n\n".join([f"[{chunk.source}] {chunk.content}" for chunk in chunks])

        if interest_label == "INTERESTED":
            mode_prompt = self._interested_response_prompt
        elif interest_label == "NOT_INTERESTED":
            mode_prompt = self._not_interested_response_prompt
        else:
            mode_prompt = "The user intent is UNCLEAR. Respond helpfully and keep the conversation moving."

        answer = await self._llm.ask_with_context(
            system_prompt=self._system_prompt,
            mode_prompt=mode_prompt,
            history_text=history_text,
            context_text=context,
            question=question,
        )

        db.add(ChatMessage(session_id=session.id, role="user", content=question))
        db.add(ChatMessage(session_id=session.id, role="assistant", content=answer))
        await db.commit()

        return answer, chunks, interest_label

    async def ask_video_search(
        self, db: AsyncSession, user_id: str, question: str
    ) -> tuple[str, list[dict], dict[str, Any]]:
        """Run the video search agent and return (answer, videos, applied_filters)."""
        if self._video_search_agent is None or self._video_filter_llm is None:
            return "Video search agent is not available.", [], {}

        session = await self._get_or_create_session(db, user_id=user_id)
        history_text = await self._get_history_text(db, session)

        answer, videos, filters = await run_video_search_agent(
            agent=self._video_search_agent,
            filter_llm=self._video_filter_llm,
            question=question,
            history_text=history_text,
            filter_prompt=self._video_filter_extractor_prompt,
        )

        db.add(ChatMessage(session_id=session.id, role="user", content=question))
        db.add(ChatMessage(session_id=session.id, role="assistant", content=answer))
        await db.commit()

        return answer, videos, filters
