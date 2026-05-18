from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Agentic Helper API"
    app_api_key: str = "change-me"
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str = ""
    qdrant_collection_name: str = "agentic_helper_knowledge"
    qdrant_vector_name: str = ""
    qdrant_vector_size: int = 1536
    qdrant_timeout_seconds: float = 10.0

    openai_api_key: str = ""
    openai_chat_model: str = "gpt-4o-mini"
    openai_chat_temperature: float = 0.2
    openai_classifier_model: str = "gpt-4o-mini"
    openai_classifier_temperature: float = 0.0
    openai_embedding_model: str = "text-embedding-3-small"
    openai_transcription_model: str = "gpt-4o-mini-transcribe"
    langsmith_tracing: bool = False
    langsmith_api_key: str = ""
    langsmith_endpoint: str = "https://api.smith.langchain.com"
    langsmith_project: str = "agentic-helper"
    langsmith_workspace_id: str = ""
    chatbot_system_prompt_file: str = "data/prompts/bviral_system_prompt.txt"
    chatbot_system_prompt_langsmith: str = ""
    chatbot_system_prompt: str = (
        "You are a helpful assistant. Use retrieved context when available. "
        "If context is missing, say you are answering from general knowledge."
    )
    chatbot_rag_classifier_prompt_file: str = "data/prompts/rag_classifier_prompt.txt"
    chatbot_rag_classifier_prompt_langsmith: str = ""
    chatbot_rag_classifier_prompt: str = (
        "You are a routing classifier for a chatbot with a document knowledge base. "
        "Return exactly one token: RAG or DIRECT. "
        "Return RAG when the answer likely depends on domain-specific facts, policies, pricing, billing, "
        "product/company details, or previously ingested resources. "
        "If a question is vague but business-contextual (for example: 'should I pay?', "
        "'how does it work?', 'is this covered?'), choose RAG. "
        "Return DIRECT for generic chitchat, rewriting, brainstorming, or questions answerable "
        "without the knowledge base."
    )
    chatbot_router_prompt_file: str = "data/prompts/router_prompt.txt"
    chatbot_router_prompt_langsmith: str = ""
    chatbot_router_prompt: str = (
        "You route user messages for the BVIRAL assistant. "
        "Return one route: CHAT_RAG, VIDEO_SEARCH, DIRECT, OUT_OF_SCOPE, or SUPPORT_HANDOFF. "
        "Use VIDEO_SEARCH when the user wants to find, filter, rank, inspect, or browse videos. "
        "Use CHAT_RAG when the answer depends on BVIRAL licensing, agreements, payment, onboarding, "
        "company policy, or ingested knowledge. "
        "Use SUPPORT_HANDOFF for submitted-video status, account-specific issues, billing failures, "
        "or requests that need a human/support mailbox. "
        "Use OUT_OF_SCOPE for unrelated topics outside BVIRAL, licensing, content creation, competitors, "
        "and video search. Use DIRECT only for simple greetings or generic assistant behavior in scope."
    )
    chatbot_interest_classifier_prompt_file: str = "data/prompts/interest_classifier_prompt.txt"
    chatbot_interest_classifier_prompt_langsmith: str = ""
    chatbot_interest_classifier_prompt: str = (
        "You classify user intent for sales/engagement interest. "
        "Return exactly one token: INTERESTED, NOT_INTERESTED, or UNCLEAR. "
        "INTERESTED: user shows buying/continuation intent, asks onboarding/next steps, asks to proceed, "
        "or asks details that imply willingness. "
        "NOT_INTERESTED: user clearly declines, rejects, stops conversation, or says they do not want to continue. "
        "UNCLEAR: neutral questions or insufficient signal."
    )
    chatbot_interested_response_prompt_file: str = "data/prompts/interested_response_prompt.txt"
    chatbot_interested_response_prompt_langsmith: str = ""
    chatbot_interested_response_prompt: str = (
        "The user is INTERESTED. Respond with momentum, clarity, and next steps. "
        "If appropriate, guide them toward proceeding and include [SUBMISSION_URL] once. "
        "Keep the tone friendly and confident."
    )
    chatbot_not_interested_response_prompt_file: str = "data/prompts/not_interested_response_prompt.txt"
    chatbot_not_interested_response_prompt_langsmith: str = ""
    chatbot_not_interested_response_prompt: str = (
        "The user is NOT_INTERESTED. Respond empathetically and without pressure. "
        "Acknowledge their decision, offer brief help if they have final questions, and keep it concise. "
        "Do not push conversion."
    )
    chatbot_video_filter_extractor_prompt_file: str = (
        "data/prompts/video_search_filter_extractor_prompt.txt"
    )
    chatbot_video_filter_extractor_prompt_langsmith: str = ""
    chatbot_video_filter_extractor_prompt: str = (
        "You are a filter extraction agent for a video search system.\n"
        "Extract only fields explicitly requested or strongly implied.\n"
        "Return JSON following the schema.\n\n"
        "Conversation so far:\n{history_text}\n\n"
        "User request:\n{question}\n"
    )
    video_search_system_prompt_file: str = "data/prompts/video_search_system_prompt.txt"
    video_search_system_prompt_langsmith: str = ""
    video_search_system_prompt: str = (
        "You are a video search assistant. Help users find videos using the available tools. "
        "Present results clearly with video titles, descriptions, and IDs."
    )

    videos_search_api_url: str = "http://localhost:5000"
    videos_search_api_fallback_urls: str = "http://videos-search-api:5000,http://host.docker.internal:5000"
    videos_search_api_key: str = "key1"
    frontend_search_url: str = "http://localhost:3000/search"
    video_search_advanced_enabled: bool = True
    video_search_timeout_seconds: float = 12.0
    video_search_retries: int = 1
    video_search_facet_cache_ttl_seconds: int = 300
    video_search_query_rewriting_enabled: bool = True
    video_search_query_rewrite_prompt_file: str = "data/prompts/video_search_query_rewrite_prompt.txt"
    video_search_query_rewrite_prompt: str = (
        "You are a query-expansion assistant for a video content library.\n"
        "Given an extracted semantic search query, rewrite it into a richer, more descriptive "
        "form optimised for vector similarity search. Add relevant synonyms, visual descriptors, "
        "and contextual terms that would appear in matching video titles, descriptions, or tags. "
        "Keep the result under 20 words. Return only the expanded query string, nothing else.\n\n"
        "Original extracted query: {query}\n"
        "Full user request: {question}\n"
        "Conversation history: {history_text}"
    )

    openai_agent_model: str = "gpt-4o-mini"
    openai_agent_temperature: float = 0.1

    rag_top_k: int = 4
    rag_chunk_size: int = 800
    rag_chunk_overlap: int = 120
    rag_query_rewriting_enabled: bool = True
    rag_relevance_grading_enabled: bool = True
    rag_min_relevant_chunks: int = 2
    rag_query_rewrite_prompt_file: str = "data/prompts/rag_query_rewrite_prompt.txt"
    rag_query_rewrite_prompt: str = (
        "Given the conversation history below, rewrite the user question as a concise, "
        "keyword-rich standalone search query for a vector knowledge base. "
        "Resolve any pronouns or references using the history. "
        "Return only the query string, nothing else.\n\n"
        "Conversation so far:\n{history_text}\n\n"
        "User question: {question}"
    )
    rag_chunk_grading_prompt_file: str = "data/prompts/rag_chunk_grading_prompt.txt"
    rag_chunk_grading_prompt: str = (
        "You are a relevance grader for a retrieval-augmented system. "
        "Given the user question and a retrieved knowledge chunk, decide whether the chunk "
        "contains information that is directly useful for answering the question. "
        "Return JSON with fields `id` (the chunk id) and `relevant` (true or false).\n\n"
        "User question: {question}\n\n"
        "Chunk id: {chunk_id}\n"
        "Chunk content:\n{chunk_content}"
    )
    chat_memory_messages: int = 12
    chat_history_redis_url: str = "redis://videos-redis:6379/0"
    chat_history_ttl_seconds: int = 60 * 60 * 24 * 30

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
