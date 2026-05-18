from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class RecommendationSearchEventSchema(BaseModel):
    query: str = Field(min_length=1)
    parsed_intent: dict[str, Any] = Field(default_factory=dict)


class RecommendationClickEventSchema(BaseModel):
    video_id: str = Field(min_length=1)
    event_type: str = Field(default="click", min_length=1)
    event_context: dict[str, Any] = Field(default_factory=dict)


class RecommendationItemSchema(BaseModel):
    video_id: str
    document: dict[str, Any]
    recommendation_score: float
    source: list[str]


class RecommendationResolvedEntitySchema(BaseModel):
    video_id: str
    title: str
    categories: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class RecommendationSeedSchema(BaseModel):
    categories: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    entities: list[str] = Field(default_factory=list)
    query_terms: list[str] = Field(default_factory=list)
    resolved_entities: list[RecommendationResolvedEntitySchema] = Field(default_factory=list)


class RecommendationResponseSchema(BaseModel):
    items: list[RecommendationItemSchema]
    total: int
    generated_at: datetime
    seed: RecommendationSeedSchema
