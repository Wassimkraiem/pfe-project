from fastapi import APIRouter, Depends, Query

from app.auth.dependencies import get_current_user
from app.recommendation.schemas import (
    RecommendationClickEventSchema,
    RecommendationSearchEventSchema,
)
from app.recommendation.services import RecommendationService
from app.response import ArResponse
from app.user.models import UserModel

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.post("/events/search")
async def ingest_search_event(
    payload: RecommendationSearchEventSchema,
    current_user: UserModel = Depends(get_current_user),
    service: RecommendationService = Depends(),
):
    await service.ingest_search_event(user_id=current_user.id, payload=payload)
    return ArResponse(data={"saved": True})


@router.post("/events/click")
async def ingest_click_event(
    payload: RecommendationClickEventSchema,
    current_user: UserModel = Depends(get_current_user),
    service: RecommendationService = Depends(),
):
    await service.ingest_video_event(user_id=current_user.id, payload=payload)
    return ArResponse(data={"saved": True})


@router.get("")
async def get_recommendations(
    limit: int = Query(12, ge=1, le=100),
    refresh: bool = Query(False),
    current_user: UserModel = Depends(get_current_user),
    service: RecommendationService = Depends(),
):
    data = await service.get_recommendations(
        user_id=current_user.id,
        limit=limit,
        refresh=refresh,
    )
    return ArResponse(data=data.model_dump())
