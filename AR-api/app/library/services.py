import json
from datetime import date, datetime

from fastapi import Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.library.exceptions import LibraryInvalidFilter
from app.library.models import LibraryDownloadEventModel
from app.library.provider import CantoLibraryClient, normalize_video_asset
from app.library.schemas import (
    LibraryDownloadEventOut,
    LibraryDownloadListOut,
    LibraryDownloadPaginationOut,
    LibraryDownloadRequestQuery,
    LibraryDownloadsQuery,
    LibraryVideoListOut,
    LibraryVideoListPaginationOut,
    LibraryVideoOut,
    LibraryVideoSearchParams,
)
from app.user.models import UserModel

_MAX_LOCAL_FILTER_SCAN_RESULTS: int = 25_000


class LibraryService:
    def __init__(
        self,
        db: AsyncSession = Depends(get_db),
        client: CantoLibraryClient = Depends(),
    ) -> None:
        self.db = db
        self.client = client

    async def list_videos(self, params: LibraryVideoSearchParams) -> LibraryVideoListOut:
        category_album_id = None
        if params.category:
            category_album_id = await self.client.resolve_category_album_id(params.category)

        if not params.requires_local_scan():
            provider_response = await self.client.search_assets(
                limit=params.limit,
                start=params.provider_start(),
                sort_by=params.sort_by.value,
                sort_direction=params.sort_direction.value,
                search_keyword=params.provider_keyword(),
                tags=params.provider_tags(),
                duration_range=params.provider_duration_range(),
                uploaded_time_range=params.provider_uploaded_time_range(),
                category_album_id=category_album_id,
            )
            items = [
                normalize_video_asset(raw_item, requested_category=params.category)
                for raw_item in provider_response.get("results", [])
                if isinstance(raw_item, dict) and str(raw_item.get("scheme") or "video") == "video"
            ]
            total = provider_response.get("found")
            if total is None:
                total = len(items)
            pagination = LibraryVideoListPaginationOut.from_values(
                page=params.page,
                page_size=params.limit,
                total=int(total),
            )
            return LibraryVideoListOut(items=items, pagination=pagination)

        return await self._scan_videos_with_local_filters(
            params=params,
            category_album_id=category_album_id,
        )

    async def get_video(self, video_id: str) -> LibraryVideoOut:
        raw_asset = await self.client.get_asset(video_id)
        return normalize_video_asset(raw_asset)

    async def download_video(
        self,
        *,
        video_id: str,
        current_user: UserModel,
        query: LibraryDownloadRequestQuery,
    ) -> str:
        request_filters = self._parse_request_filters(query.request_filters)
        raw_asset = await self.client.get_asset(video_id)
        normalized = normalize_video_asset(raw_asset)
        original_url = await self.client.download_url_for_asset(raw_asset)

        self.db.add(
            LibraryDownloadEventModel(
                user_id=current_user.id,
                asset_id=normalized.id,
                title=normalized.title,
                thumbnail_url=normalized.thumbnail_url,
                category=normalized.category,
                source_scope=query.source_scope,
                request_filters=request_filters,
            )
        )
        await self.db.flush()
        return original_url

    async def list_downloads(
        self,
        *,
        current_user: UserModel,
        query: LibraryDownloadsQuery,
    ) -> LibraryDownloadListOut:
        count_query = select(func.count()).select_from(LibraryDownloadEventModel).where(
            LibraryDownloadEventModel.user_id == current_user.id
        )
        total = int((await self.db.execute(count_query)).scalar_one())

        items_query = (
            select(LibraryDownloadEventModel)
            .where(LibraryDownloadEventModel.user_id == current_user.id)
            .order_by(
                LibraryDownloadEventModel.downloaded_at.desc(),
                LibraryDownloadEventModel.id.desc(),
            )
            .offset((query.page - 1) * query.limit)
            .limit(query.limit)
        )
        rows = (await self.db.execute(items_query)).scalars().all()
        items = [
            LibraryDownloadEventOut(
                id=row.id,
                asset_id=row.asset_id,
                title=row.title,
                thumbnail_url=row.thumbnail_url or "",
                category=row.category,
                source_scope=row.source_scope,
                request_filters={str(key): str(value) for key, value in (row.request_filters or {}).items()},
                downloaded_at=row.downloaded_at,
            )
            for row in rows
        ]
        pagination = LibraryDownloadPaginationOut(
            page=query.page,
            page_size=query.limit,
            total=total,
            total_pages=(total + query.limit - 1) // query.limit if total > 0 else 0,
        )
        return LibraryDownloadListOut(items=items, pagination=pagination)

    async def _scan_videos_with_local_filters(
        self,
        *,
        params: LibraryVideoSearchParams,
        category_album_id: str | None,
    ) -> LibraryVideoListOut:
        scan_limit = max(params.limit, 100)
        matched_items: list[LibraryVideoOut] = []
        total_matches = 0
        start = 0
        provider_found = None
        fully_scanned = False

        while True:
            provider_response = await self.client.search_assets(
                limit=scan_limit,
                start=start,
                sort_by=params.sort_by.value,
                sort_direction=params.sort_direction.value,
                search_keyword=params.provider_keyword(),
                tags=params.provider_tags(),
                duration_range=params.provider_duration_range(),
                uploaded_time_range=params.provider_uploaded_time_range(),
                category_album_id=category_album_id,
            )
            provider_found = int(provider_response.get("found") or 0)
            raw_results = provider_response.get("results", [])
            if not raw_results:
                fully_scanned = True
                break

            normalized_batch = [
                normalize_video_asset(raw_item, requested_category=params.category)
                for raw_item in raw_results
                if isinstance(raw_item, dict) and str(raw_item.get("scheme") or "video") == "video"
            ]
            filtered_batch = [item for item in normalized_batch if self._matches_local_filters(item, params)]
            total_matches += len(filtered_batch)
            matched_items.extend(filtered_batch)

            start += scan_limit
            if provider_found is not None and start >= provider_found:
                fully_scanned = True
                break
            if start >= _MAX_LOCAL_FILTER_SCAN_RESULTS:
                break

        if not fully_scanned and provider_found and provider_found > _MAX_LOCAL_FILTER_SCAN_RESULTS:
            raise LibraryInvalidFilter(
                message="This filter combination is too broad to evaluate safely. Narrow the search or choose a category.",
                error_code="library_filter_scope_too_broad",
                details={"max_scan_results": _MAX_LOCAL_FILTER_SCAN_RESULTS},
            )

        page_start = params.provider_start()
        page_end = page_start + params.limit
        page_items = matched_items[page_start:page_end]
        pagination = LibraryVideoListPaginationOut.from_values(
            page=params.page,
            page_size=params.limit,
            total=total_matches,
        )
        return LibraryVideoListOut(items=page_items, pagination=pagination)

    def _matches_local_filters(
        self,
        item: LibraryVideoOut,
        params: LibraryVideoSearchParams,
    ) -> bool:
        filmed_from, filmed_to = params.filmed_on_range()
        item_filmed_on = self._safe_parse_date(item.filmed_on)
        if filmed_from and item_filmed_on and item_filmed_on < filmed_from:
            return False
        if filmed_to and item_filmed_on and item_filmed_on > filmed_to:
            return False
        if (filmed_from or filmed_to) and item_filmed_on is None:
            return False
        return True

    @staticmethod
    def _safe_parse_date(value: str) -> date | None:
        if not value:
            return None
        try:
            return datetime.fromisoformat(f"{value}T00:00:00+00:00").date()
        except ValueError:
            return None

    @staticmethod
    def _parse_request_filters(raw_filters: str | None) -> dict[str, str]:
        if raw_filters is None:
            return {}
        try:
            payload = json.loads(raw_filters)
        except json.JSONDecodeError as exc:
            raise LibraryInvalidFilter(
                message="request_filters must be valid JSON",
                details={"request_filters": raw_filters},
            ) from exc
        if not isinstance(payload, dict):
            raise LibraryInvalidFilter(
                message="request_filters must be a JSON object",
                details={"request_filters": payload},
            )
        return {
            str(key): str(value)
            for key, value in payload.items()
            if value is not None and str(value).strip()
        }
