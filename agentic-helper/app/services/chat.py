from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from langchain_openai import ChatOpenAI

from app.core.config import settings
from app.models.knowledge import KnowledgeChunk
from app.services.agent import run_video_search_agent
from app.services.chat_history import ChatHistoryStore
from app.services.llm import LLMService
from app.services.rag import RagService
from app.services.video_search import VideoSearchResult, VideoSearchService

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class AutoChatResult:
    answer: str
    route: str
    confidence: float | None = None
    interest_label: str = ""
    chunks: list[KnowledgeChunk] | None = None
    video_result: VideoSearchResult | None = None


class ChatService:
    def __init__(
        self,
        rag_service: RagService,
        history_store: ChatHistoryStore,
        llm_service: LLMService,
        system_prompt: str,
        rag_classifier_prompt: str,
        router_prompt: str,
        interest_classifier_prompt: str,
        interested_response_prompt: str,
        not_interested_response_prompt: str,
        video_filter_extractor_prompt: str,
        video_search_agent: Any = None,
        video_filter_llm: ChatOpenAI | None = None,
        video_search_service: VideoSearchService | None = None,
        rag_query_rewrite_prompt: str = "",
        rag_chunk_grading_prompt: str = "",
    ) -> None:
        self._rag = rag_service
        self._history_store = history_store
        self._llm = llm_service
        self._system_prompt = system_prompt
        self._rag_classifier_prompt = rag_classifier_prompt
        self._router_prompt = router_prompt
        self._interest_classifier_prompt = interest_classifier_prompt
        self._interested_response_prompt = interested_response_prompt
        self._not_interested_response_prompt = not_interested_response_prompt
        self._video_filter_extractor_prompt = video_filter_extractor_prompt
        self._video_search_agent = video_search_agent
        self._video_filter_llm = video_filter_llm
        self._video_search_service = video_search_service
        self._rag_query_rewrite_prompt = rag_query_rewrite_prompt or settings.rag_query_rewrite_prompt
        self._rag_chunk_grading_prompt = rag_chunk_grading_prompt or settings.rag_chunk_grading_prompt

    async def ask(self, user_id: str, question: str) -> tuple[str, list[KnowledgeChunk], str]:
        history_text = await self._history_store.get_history_text(user_id)

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

        chunks: list[KnowledgeChunk] = []
        if use_rag:
            # Step 1: rewrite the conversational question into a retrieval-optimized query
            if settings.rag_query_rewriting_enabled:
                retrieval_query = await self._llm.rewrite_rag_query(
                    rewrite_prompt=self._rag_query_rewrite_prompt,
                    question=question,
                    history_text=history_text,
                )
                print("\n" + "=" * 60)
                print("[RAG] Step 1 — Query Rewriting")
                print(f"  Original question : {question!r}")
                print(f"  Rewritten query   : {retrieval_query!r}")
                print("=" * 60)
            else:
                retrieval_query = question

            chunks = await self._rag.retrieve(retrieval_query)
            print(f"\n[RAG] Retrieved {len(chunks)} chunk(s) for query {retrieval_query!r}")
            for i, c in enumerate(chunks, 1):
                score_str = f"{c.score:.4f}" if c.score is not None else "n/a"
                print(f"  [{i}] source={c.source!r}  score={score_str}  excerpt={c.content[:80]!r}")

            # Step 2: grade chunks for relevance; re-retrieve on original question if too few pass
            if settings.rag_relevance_grading_enabled and chunks:
                graded = await self._llm.grade_chunks(
                    grading_prompt=self._rag_chunk_grading_prompt,
                    question=question,
                    chunks=chunks,
                )
                relevant_sources = [c.source for c in graded]
                dropped_sources = [c.source for c in chunks if c not in graded]
                print(f"\n[RAG] Step 2 — Relevance Grading ({len(graded)}/{len(chunks)} relevant)")
                print(f"  Relevant : {relevant_sources}")
                if dropped_sources:
                    print(f"  Dropped  : {dropped_sources}")
                if len(graded) < settings.rag_min_relevant_chunks:
                    print(
                        f"  ⚠ Below threshold ({settings.rag_min_relevant_chunks}) — "
                        "triggering corrective re-retrieval on original question"
                    )
                    fallback_chunks = await self._rag.retrieve(question)
                    seen_ids = {c.id for c in graded}
                    merged = graded + [c for c in fallback_chunks if c.id not in seen_ids]
                    chunks = merged[: settings.rag_top_k]
                    print(f"  Merged pool: {len(chunks)} chunk(s) after deduplication")
                else:
                    chunks = graded
            print(f"[RAG] Final context: {len(chunks)} chunk(s) passed to answer model\n")

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

        await self._history_store.append_turn(user_id, question, answer)

        return answer, chunks, interest_label

    async def ask_video_search(self, user_id: str, question: str) -> tuple[str, list[dict], dict[str, Any]]:
        """Run the video search agent and return (answer, videos, applied_filters)."""
        result = await self.ask_video_search_detailed(user_id=user_id, question=question)
        return result.answer, result.videos, result.filters

    async def ask_video_search_detailed(
        self,
        user_id: str,
        question: str,
        *,
        debug: bool = False,
    ) -> VideoSearchResult:
        """Run deterministic advanced search, falling back to the legacy LangGraph agent."""
        history_text = await self._history_store.get_history_text(user_id)
        previous_plan = await self._history_store.get_state(user_id, "last_video_search_plan")

        if self._video_search_service is not None:
            result = await self._video_search_service.search(
                question=question,
                history_text=history_text,
                previous_plan=previous_plan,
                debug=debug,
            )
            await self._history_store.set_state(user_id, "last_video_search_plan", result.filters)
            await self._history_store.append_turn(user_id, question, result.answer)
            return result

        if self._video_search_agent is None or self._video_filter_llm is None:
            return VideoSearchResult(
                answer="Video search is not available.",
                videos=[],
                filters={},
                search_payload={},
                fallbacks_used=["video_search_unavailable"],
            )

        answer, videos, filters = await run_video_search_agent(
            agent=self._video_search_agent,
            filter_llm=self._video_filter_llm,
            question=question,
            history_text=history_text,
            filter_prompt=self._video_filter_extractor_prompt,
        )

        await self._history_store.append_turn(user_id, question, answer)

        return VideoSearchResult(
            answer=answer,
            videos=videos,
            filters=filters,
            search_payload={},
            total=len(videos),
            fallbacks_used=["legacy_langgraph_agent"],
        )

    async def ask_auto(
        self,
        user_id: str,
        question: str,
        *,
        include_answer: bool = False,
        debug: bool = False,
    ) -> AutoChatResult:
        history_text = await self._history_store.get_history_text(user_id)
        try:
            route = await self._llm.classify_conversation_route(
                router_prompt=self._router_prompt,
                question=question,
                history_text=history_text,
            )
        except Exception:
            logger.exception("Conversation routing failed; falling back to CHAT_RAG")
            route = None

        route_name = route.route if route is not None else "CHAT_RAG"
        confidence = route.confidence if route is not None else None
        interest_label = route.interest if route is not None else "UNCLEAR"

        if route_name == "VIDEO_SEARCH":
            video_result = await self.ask_video_search_detailed(
                user_id=user_id,
                question=question,
                debug=debug,
            )
            return AutoChatResult(
                answer=video_result.answer if include_answer else "",
                route=route_name,
                confidence=confidence,
                interest_label=interest_label,
                video_result=video_result,
            )

        if route_name == "OUT_OF_SCOPE":
            answer = (
                "I can help with BVIRAL licensing, content creation, competitor questions, "
                "and video search. For this topic, I need to redirect back to BVIRAL-related help."
            )
            await self._history_store.append_turn(user_id, question, answer)
            return AutoChatResult(answer=answer, route=route_name, confidence=confidence, interest_label=interest_label)

        if route_name == "SUPPORT_HANDOFF":
            answer = "For account-specific or submitted-video status questions, please contact support@bviral.com."
            await self._history_store.append_turn(user_id, question, answer)
            return AutoChatResult(answer=answer, route=route_name, confidence=confidence, interest_label=interest_label)

        if route_name == "DIRECT":
            answer = await self._llm.ask_with_context(
                system_prompt=self._system_prompt,
                mode_prompt="Answer directly, stay within BVIRAL scope, and keep the response concise.",
                history_text=history_text,
                context_text="",
                question=question,
            )
            await self._history_store.append_turn(user_id, question, answer)
            return AutoChatResult(answer=answer, route=route_name, confidence=confidence, interest_label=interest_label)

        answer, chunks, inferred_interest = await self.ask(user_id=user_id, question=question)
        return AutoChatResult(
            answer=answer,
            route="CHAT_RAG",
            confidence=confidence,
            interest_label=interest_label or inferred_interest,
            chunks=chunks,
        )
