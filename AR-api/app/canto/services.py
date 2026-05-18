import asyncio
import json
import logging
from time import monotonic

import httpx
from fastapi import Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.canto.exceptions import CantoGroupRemovalFailed
from app.canto_sdk import BASIC_PLAN_GROUP, CantoUsers
from app.core.config import settings
from app.db.database import get_db
from app.user.models import UserModel

from .exceptions import (
    CantoDownloadConfigMissing,
    CantoDownloadFailed,
    CantoInvalidDownloadRequest,
    CantoVideoNotFound,
)
from .models import DownloadedVideoModel
from .schemas import (
    CantoDownloadHistoryItemOut,
    CantoDownloadHistoryListOut,
    CantoDownloadHistoryPaginationOut,
    CantoDownloadHistoryQuery,
    CantoDownloadRequestQuery,
)

logger = logging.getLogger(__name__)
_CANTO_BASE_URL = "https://sdamedia.canto.com"
_CANTO_USER_ID = "wissem@sda.media"
_CANTO_TIMEOUT_SECONDS = 15.0


class CantoService:
    _token_cache: tuple[str, float] | None = None

    def __init__(self, db: AsyncSession = Depends(get_db)) -> None:
        self.db = db

    async def remove_user_from_basic_group(
        self,
        *,
        user_email: str,
    ) -> dict[str, object]:
        normalized_email = user_email.strip().lower()

        if not settings.canto_enabled:
            return {
                "mode": "direct",
                "email": normalized_email,
                "canto_enabled": settings.canto_enabled,
                "removed": False,
                "message": "Canto is disabled for this environment",
            }

        try:
            await asyncio.to_thread(
                CantoUsers().remove_user_from_group,
                BASIC_PLAN_GROUP,
                normalized_email,
            )
        except Exception as exc:
            logger.exception(
                "Manual Canto removal failed: email=%s group_id=%s",
                normalized_email,
                BASIC_PLAN_GROUP,
            )
            raise CantoGroupRemovalFailed(details=str(exc)) from exc

        logger.info(
            "Manual Canto removal succeeded: email=%s group_id=%s",
            normalized_email,
            BASIC_PLAN_GROUP,
        )
        return {
            "mode": "direct",
            "email": normalized_email,
            "group_id": BASIC_PLAN_GROUP,
            "canto_enabled": settings.canto_enabled,
            "removed": True,
        }

    async def download_video(
        self,
        *,
        video_id: str,
        current_user: UserModel,
        query: CantoDownloadRequestQuery,
    ) -> str:
        self._ensure_download_configured()
        request_filters = self._parse_request_filters(query.request_filters)
        raw_asset = await self._get_video_asset(video_id=video_id)
        signed_download_url = await self._resolve_signed_download_url(raw_asset=raw_asset)

        url_data = raw_asset.get("url") if isinstance(raw_asset.get("url"), dict) else {}
        self.db.add(
            DownloadedVideoModel(
                user_id=current_user.id,
                video_id=str(raw_asset.get("id") or video_id).strip(),
                video_title=str(raw_asset.get("name") or video_id).strip(),
                thumbnail_url=str(url_data.get("directUrlPreview") or "").strip() or None,
                source_scope=query.source_scope,
                request_filters=request_filters,
            )
        )
        await self.db.flush()
        logger.info(
            "Canto download URL generated: user_id=%s video_id=%s source_scope=%s",
            current_user.id,
            video_id,
            query.source_scope.value,
        )
        return signed_download_url

    async def list_downloads(
        self,
        *,
        current_user: UserModel,
        query: CantoDownloadHistoryQuery,
    ) -> CantoDownloadHistoryListOut:
        count_query = select(func.count()).select_from(DownloadedVideoModel).where(
            DownloadedVideoModel.user_id == current_user.id
        )
        total = int((await self.db.execute(count_query)).scalar_one())

        items_query = (
            select(DownloadedVideoModel)
            .where(DownloadedVideoModel.user_id == current_user.id)
            .order_by(DownloadedVideoModel.downloaded_at.desc(), DownloadedVideoModel.id.desc())
            .offset((query.page - 1) * query.limit)
            .limit(query.limit)
        )
        rows = (await self.db.execute(items_query)).scalars().all()
        items = [
            CantoDownloadHistoryItemOut(
                id=row.id,
                video_id=row.video_id,
                video_title=row.video_title,
                thumbnail_url=row.thumbnail_url or "",
                source_scope=row.source_scope,
                request_filters={str(key): str(value) for key, value in (row.request_filters or {}).items()},
                downloaded_at=row.downloaded_at,
            )
            for row in rows
        ]
        pagination = CantoDownloadHistoryPaginationOut.from_values(
            page=query.page,
            page_size=query.limit,
            total=total,
        )
        return CantoDownloadHistoryListOut(items=items, pagination=pagination)

    @staticmethod
    def _ensure_download_configured() -> None:
        missing_keys = [
            key
            for key, value in (
                ("CANTO_AUTH_URL", settings.CANTO_AUTH_URL),
                ("CANTO_APP_ID", settings.CANTO_APP_ID),
                ("CANTO_APP_SECRET", settings.CANTO_APP_SECRET),
            )
            if not str(value).strip()
        ]
        if missing_keys:
            raise CantoDownloadConfigMissing(details={"missing": missing_keys})

    async def _get_video_asset(self, *, video_id: str) -> dict:
        normalized_video_id = video_id.strip()
        payload = await self._request(
            method="GET",
            url=f"{_CANTO_BASE_URL}/api/v1/video/{normalized_video_id}",
        )
        response_video_id = str(payload.get("id") or "").strip()
        if not response_video_id:
            raise CantoVideoNotFound(details={"video_id": normalized_video_id})
        return payload

    async def _resolve_signed_download_url(self, *, raw_asset: dict) -> str:
        url_data = raw_asset.get("url") if isinstance(raw_asset.get("url"), dict) else {}
        api_binary_url = str(url_data.get("download") or "").strip()
        asset_id = str(raw_asset.get("id") or "").strip()
        if not api_binary_url:
            raise CantoDownloadFailed(
                message="Canto video does not include a download URL",
                details={"video_id": asset_id},
            )

        token = await self._get_token()
        try:
            async with httpx.AsyncClient(timeout=_CANTO_TIMEOUT_SECONDS) as client:
                response = await client.get(
                    api_binary_url,
                    headers={"Authorization": f"Bearer {token}"},
                    follow_redirects=False,
                )
        except httpx.HTTPError as exc:
            raise CantoDownloadFailed(
                message="Failed to reach Canto download endpoint",
                details={"video_id": asset_id, "error": str(exc)},
            ) from exc

        location = response.headers.get("location", "").strip()
        if not location:
            raise CantoDownloadFailed(
                message="Canto did not return a signed download URL",
                details={"video_id": asset_id, "status_code": response.status_code},
            )
        return location

    async def _request(
        self,
        *,
        method: str,
        url: str,
    ) -> dict:
        token = await self._get_token()
        try:
            async with httpx.AsyncClient(timeout=_CANTO_TIMEOUT_SECONDS) as client:
                response = await client.request(
                    method=method,
                    url=url,
                    headers={"Authorization": f"Bearer {token}"},
                )
        except httpx.HTTPError as exc:
            raise CantoDownloadFailed(
                message="Canto provider request failed",
                details={"url": url, "error": str(exc)},
            ) from exc

        if response.status_code == 404:
            raise CantoVideoNotFound(details={"url": url})
        if response.status_code >= 400:
            raise CantoDownloadFailed(
                message="Canto provider request failed",
                details={"url": url, "status_code": response.status_code, "body": response.text},
            )

        payload = response.json()
        if not isinstance(payload, dict):
            raise CantoDownloadFailed(
                message="Unexpected Canto response format",
                details={"url": url, "response_type": type(payload).__name__},
            )
        return payload

    async def _get_token(self) -> str:
        cached = self.__class__._token_cache
        if cached is not None and cached[1] > monotonic():
            return cached[0]

        try:
            async with httpx.AsyncClient(timeout=_CANTO_TIMEOUT_SECONDS) as client:
                response = await client.post(
                    settings.CANTO_AUTH_URL,
                    params={
                        "app_id": settings.CANTO_APP_ID,
                        "app_secret": settings.CANTO_APP_SECRET,
                        "grant_type": "client_credentials",
                        "user_id": _CANTO_USER_ID,
                    },
                )
        except httpx.HTTPError as exc:
            raise CantoDownloadFailed(
                message="Failed to reach Canto auth endpoint",
                details={"error": str(exc)},
            ) from exc

        if response.status_code != 200:
            raise CantoDownloadFailed(
                message="Failed to authenticate with Canto",
                details={"status_code": response.status_code, "body": response.text},
            )

        payload = response.json()
        token = str(payload.get("accessToken") or "").strip()
        if not token:
            raise CantoDownloadFailed(
                message="Canto authentication did not return access token",
                details=payload,
            )
        expires_in = int(payload.get("expiresIn") or 300)
        self.__class__._token_cache = (token, monotonic() + max(expires_in - 30, 60))
        return token

    @staticmethod
    def _parse_request_filters(raw_filters: str | None) -> dict[str, str]:
        if raw_filters is None:
            return {}
        try:
            payload = json.loads(raw_filters)
        except json.JSONDecodeError as exc:
            raise CantoInvalidDownloadRequest(
                message="request_filters must be valid JSON",
                details={"request_filters": raw_filters},
            ) from exc
        if not isinstance(payload, dict):
            raise CantoInvalidDownloadRequest(
                message="request_filters must be a JSON object",
                details={"request_filters": payload},
            )
        return {
            str(key): str(value)
            for key, value in payload.items()
            if value is not None and str(value).strip()
        }
