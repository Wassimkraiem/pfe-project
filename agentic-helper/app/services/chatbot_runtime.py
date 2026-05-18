from dataclasses import dataclass
from typing import Any

from langchain_openai import ChatOpenAI


@dataclass(slots=True)
class ChatbotRuntime:
    llm: ChatOpenAI
    classifier_llm: ChatOpenAI
    video_filter_llm: ChatOpenAI
    system_prompt: str
    rag_classifier_prompt: str
    router_prompt: str
    interest_classifier_prompt: str
    interested_response_prompt: str
    not_interested_response_prompt: str
    video_filter_extractor_prompt: str
    rag_query_rewrite_prompt: str = ""
    rag_chunk_grading_prompt: str = ""
    video_search_query_rewrite_prompt: str = ""
    video_search_agent: Any = None
    video_search_client: Any = None
