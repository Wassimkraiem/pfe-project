from fastapi import APIRouter, Depends, Query

from app.auth.dependencies import get_current_user, require_admin_role
from app.response import ArResponse
from app.user.models import UserModel
from app.video_submission.schemas import (
    VideoSubmissionAdminUpdateSchema,
    VideoSubmissionCreateSchema,
    VideoSubmissionOutSchema,
)
from app.video_submission.services import VideoSubmissionService

router = APIRouter(prefix="/video-submissions", tags=["video-submissions"])


@router.post("")
async def submit_video(
    payload: VideoSubmissionCreateSchema,
    current_user: UserModel = Depends(get_current_user),
    service: VideoSubmissionService = Depends(),
):
    submission = await service.create(current_user.id, payload)
    return ArResponse(
        data=VideoSubmissionOutSchema.model_validate(submission).model_dump(),
        status_code=201,
    )


@router.get("")
async def list_my_submissions(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: UserModel = Depends(get_current_user),
    service: VideoSubmissionService = Depends(),
):
    submissions = await service.list_by_user(
        current_user.id, skip=skip, limit=limit
    )
    return ArResponse(
        data=[
            VideoSubmissionOutSchema.model_validate(s).model_dump()
            for s in submissions
        ]
    )


@router.get("/{submission_id}")
async def get_submission(
    submission_id: int,
    current_user: UserModel = Depends(get_current_user),
    service: VideoSubmissionService = Depends(),
):
    submission = await service.get_by_id(submission_id, current_user.id)
    return ArResponse(
        data=VideoSubmissionOutSchema.model_validate(submission).model_dump()
    )


@router.get("/admin/all")
async def admin_list_submissions(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    _: None = Depends(require_admin_role),
    service: VideoSubmissionService = Depends(),
):
    submissions = await service.list_all(skip=skip, limit=limit)
    return ArResponse(
        data=[
            VideoSubmissionOutSchema.model_validate(s).model_dump()
            for s in submissions
        ]
    )


@router.patch("/admin/{submission_id}")
async def admin_update_submission(
    submission_id: int,
    payload: VideoSubmissionAdminUpdateSchema,
    _: None = Depends(require_admin_role),
    service: VideoSubmissionService = Depends(),
):
    submission = await service.admin_update(submission_id, payload)
    return ArResponse(
        data=VideoSubmissionOutSchema.model_validate(submission).model_dump()
    )
