from typing import Literal

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel


class RagRoute(BaseModel):
    route: Literal["RAG", "DIRECT"]


class InterestRoute(BaseModel):
    interest: Literal["INTERESTED", "NOT_INTERESTED", "UNCLEAR"]


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
