from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Agentic Helper API"
    app_api_key: str = "change-me"
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/agentic_helper"

    openai_api_key: str = ""
    openai_chat_model: str = "gpt-4o-mini"
    openai_chat_temperature: float = 0.2
    openai_classifier_model: str = "gpt-4o-mini"
    openai_classifier_temperature: float = 0.0
    openai_embedding_model: str = "text-embedding-3-small"
    chatbot_system_prompt_file: str = "data/prompts/bviral_system_prompt.txt"
    chatbot_system_prompt: str = (
        "You are a helpful assistant. Use retrieved context when available. "
        "If context is missing, say you are answering from general knowledge."
    )
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
    chatbot_interest_classifier_prompt: str = (
        "You classify user intent for sales/engagement interest. "
        "Return exactly one token: INTERESTED, NOT_INTERESTED, or UNCLEAR. "
        "INTERESTED: user shows buying/continuation intent, asks onboarding/next steps, asks to proceed, "
        "or asks details that imply willingness. "
        "NOT_INTERESTED: user clearly declines, rejects, stops conversation, or says they do not want to continue. "
        "UNCLEAR: neutral questions or insufficient signal."
    )
    chatbot_interested_response_prompt: str = (
        "The user is INTERESTED. Respond with momentum, clarity, and next steps. "
        "If appropriate, guide them toward proceeding and include [SUBMISSION_URL] once. "
        "Keep the tone friendly and confident."
    )
    chatbot_not_interested_response_prompt: str = (
        "The user is NOT_INTERESTED. Respond empathetically and without pressure. "
        "Acknowledge their decision, offer brief help if they have final questions, and keep it concise. "
        "Do not push conversion."
    )
    chatbot_video_filter_extractor_prompt_file: str = (
        "data/prompts/video_search_filter_extractor_prompt.txt"
    )
    chatbot_video_filter_extractor_prompt: str = (
        "You are a filter extraction agent for a video search system.\n"
        "Extract only fields explicitly requested or strongly implied.\n"
        "Return JSON following the schema.\n\n"
        "Conversation so far:\n{history_text}\n\n"
        "User request:\n{question}\n"
    )

    videos_search_api_url: str = "http://localhost:5000"
    videos_search_api_fallback_urls: str = "http://videos-search-api:5000,http://host.docker.internal:5000"
    videos_search_api_key: str = "key1"
    frontend_search_url: str = "http://localhost:3000/search"

    openai_agent_model: str = "gpt-4o-mini"
    openai_agent_temperature: float = 0.1

    rag_top_k: int = 4
    rag_chunk_size: int = 800
    rag_chunk_overlap: int = 120
    chat_memory_messages: int = 12

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
