from __future__ import annotations

from collections.abc import Iterable
from datetime import date, datetime, timezone
from math import gcd
from pathlib import Path
from time import monotonic

import httpx

from app.core.config import settings
from app.library.exceptions import (
    LibraryCategoryNotFound,
    LibraryProviderError,
    LibraryVideoNotFound,
)
from app.library.schemas import LibraryVideoOut

_CANTO_BASE_URL: str = "https://sdamedia.canto.com"
_CANTO_USER_ID: str = "wissem@sda.media"
_LICENSED_VIDEOS_FOLDER_URL: str = f"{_CANTO_BASE_URL}/api/v1/folder/UCAQO"
_LIBRARY_ROOT_PATH: str = "Licensed Content"
_LIBRARY_TIMEOUT_SECONDS: float = 15.0

def _strip_extension(filename: str) -> str:
    suffix = Path(filename).suffix
    return filename[: -len(suffix)] if suffix else filename


def _normalized_key(key: str) -> str:
    return "".join(ch for ch in key.lower() if ch.isalnum())


def _lookup_nested_value(payload: dict | None, *candidates: str) -> str | None:
    if not isinstance(payload, dict):
        return None
    normalized = {_normalized_key(key): value for key, value in payload.items()}
    for candidate in candidates:
        value = normalized.get(_normalized_key(candidate))
        if value is None:
            continue
        if isinstance(value, list):
            joined = ", ".join(str(item).strip() for item in value if str(item).strip())
            return joined or None
        stringified = str(value).strip()
        if stringified:
            return stringified
    return None


def _parse_int(value: object, default: int = 0) -> int:
    if value is None:
        return default
    if isinstance(value, int):
        return value
    try:
        return int(float(str(value).strip()))
    except (TypeError, ValueError):
        return default


def _parse_provider_datetime(value: object) -> datetime | None:
    if value is None:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    if len(raw) >= 14 and raw[:14].isdigit():
        return datetime.strptime(raw[:14], "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            parsed = datetime.strptime(raw, fmt)
            return parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _parse_provider_date(value: object) -> date | None:
    timestamp = _parse_provider_datetime(value)
    if timestamp is not None:
        return timestamp.date()
    raw = str(value).strip() if value is not None else ""
    if not raw:
        return None
    try:
        return date.fromisoformat(raw[:10])
    except ValueError:
        return None


def _to_iso_datetime(value: object) -> str:
    parsed = _parse_provider_datetime(value)
    if parsed is None:
        return ""
    return parsed.isoformat().replace("+00:00", "Z")


def _to_iso_date(value: object) -> str:
    parsed = _parse_provider_date(value)
    return parsed.isoformat() if parsed is not None else ""


def _normalize_tags(raw_tags: object) -> list[str]:
    values: Iterable[object]
    if raw_tags is None:
        values = []
    elif isinstance(raw_tags, list):
        values = raw_tags
    else:
        values = str(raw_tags).split(",")
    normalized: list[str] = []
    seen: set[str] = set()
    for tag in values:
        text = str(tag).strip().lower()
        if not text or text in seen:
            continue
        seen.add(text)
        normalized.append(text)
    return normalized


def _derive_category(raw_asset: dict, requested_category: str | None, root_path: str) -> str:
    related_albums = raw_asset.get("relatedAlbums")
    if isinstance(related_albums, list):
        for album in related_albums:
            if not isinstance(album, dict):
                continue
            name_path = str(album.get("namePath") or "").strip()
            if not name_path:
                continue
            if root_path and name_path.startswith(f"{root_path}/"):
                return name_path.split("/")[-1]
            return name_path.split("/")[-1]
    if requested_category:
        return requested_category
    return "Uncategorised"


def normalize_video_asset(raw_asset: dict, *, requested_category: str | None = None) -> LibraryVideoOut:
    additional = raw_asset.get("additional") if isinstance(raw_asset.get("additional"), dict) else {}
    default = raw_asset.get("default") if isinstance(raw_asset.get("default"), dict) else {}
    url = raw_asset.get("url") if isinstance(raw_asset.get("url"), dict) else {}

    filename = str(raw_asset.get("name") or "").strip()
    title = (
        _lookup_nested_value(additional, "Title")
        or _strip_extension(filename)
        or str(raw_asset.get("id") or "").strip()
    )
    description = (
        str(raw_asset.get("description") or "").strip()
        or _lookup_nested_value(additional, "Description")
        or ""
    )
    width = _parse_int(raw_asset.get("width"))
    height = _parse_int(raw_asset.get("height"))
    if width > 0 and height > 0:
        ratio_divisor = gcd(width, height)
        aspect_ratio = f"{width // ratio_divisor}:{height // ratio_divisor}"
    else:
        aspect_ratio = ""
    if width > height:
        orientation = "landscape"
    elif height > width:
        orientation = "portrait"
    else:
        orientation = "square"

    uploaded_value = (
        _lookup_nested_value(default, "Date uploaded", "Date_uploaded", "DateUploaded")
        or raw_asset.get("time")
    )
    mime_type = (
        _lookup_nested_value(default, "Content Type", "Content_Type", "ContentType")
        or _lookup_nested_value(additional, "Content Type", "Content_Type", "ContentType")
        or ""
    )

    return LibraryVideoOut(
        id=str(raw_asset.get("id") or "").strip(),
        title=title,
        filename=filename,
        description=description,
        thumbnail_url=str(url.get("directUrlPreview") or "").strip(),
        preview_url=str(url.get("directUrlPreviewPlay") or "").strip(),
        width=width,
        height=height,
        aspect_ratio=aspect_ratio,
        orientation=orientation,
        duration_seconds=_parse_int(
            _lookup_nested_value(default, "Time", "DurationTime", "Duration time")
        ),
        file_size=_parse_int(raw_asset.get("size") or _lookup_nested_value(default, "Size")),
        mime_type=mime_type,
        published_at=_to_iso_datetime(raw_asset.get("time")),
        uploaded_at=_to_iso_datetime(uploaded_value),
        filmed_on=_to_iso_date(_lookup_nested_value(additional, "Filmed On", "Filmed_On")),
        location=_lookup_nested_value(additional, "Location") or "",
        credit=_lookup_nested_value(additional, "Credit") or "",
        tags=_normalize_tags(raw_asset.get("tag")),
        category=_derive_category(raw_asset, requested_category, _LIBRARY_ROOT_PATH),
    )


class CantoLibraryClient:
    _token_cache: tuple[str, float] | None = None
    _category_album_cache: dict[str, str] = {}

    def __init__(self) -> None:
        self.base_url = _CANTO_BASE_URL
        self.timeout = _LIBRARY_TIMEOUT_SECONDS

    async def _get_token(self) -> str:
        cached = self.__class__._token_cache
        if cached is not None and cached[1] > monotonic():
            return cached[0]

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
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
            raise LibraryProviderError(
                message="Failed to reach Canto auth endpoint",
                details={"error": str(exc)},
            ) from exc
        if response.status_code != 200:
            raise LibraryProviderError(
                message="Failed to authenticate with Canto",
                details=response.text,
            )
        payload = response.json()
        token = str(payload.get("accessToken") or "").strip()
        if not token:
            raise LibraryProviderError(
                message="Canto authentication response did not include an access token",
                details=payload,
            )
        expires_in = int(payload.get("expiresIn") or 300)
        self.__class__._token_cache = (token, monotonic() + max(expires_in - 30, 60))
        return token

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, str | int] | None = None,
        json_body: object | None = None,
    ) -> dict:
        token = await self._get_token()
        headers = {"Authorization": f"Bearer {token}"}
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.request(
                    method=method,
                    url=f"{self.base_url}{path}",
                    params=params,
                    json=json_body,
                    headers=headers,
                )
        except httpx.HTTPError as exc:
            raise LibraryProviderError(
                message="Canto request failed",
                details={"path": path, "error": str(exc)},
            ) from exc
        if response.status_code >= 400:
            raise LibraryProviderError(
                details={
                    "status_code": response.status_code,
                    "path": path,
                    "params": params,
                    "body": response.text,
                }
            )
        data = response.json()
        if isinstance(data, dict):
            return data
        raise LibraryProviderError(
            message="Unexpected Canto response shape",
            details={"path": path, "response_type": type(data).__name__},
        )

    async def resolve_category_album_id(self, category: str) -> str:
        cached = self.__class__._category_album_cache.get(category)
        if cached:
            return cached

        folder_listing = await self._request(
            "GET",
            _LICENSED_VIDEOS_FOLDER_URL.removeprefix(self.base_url),
            params={"layer": 1},
        )
        for item in folder_listing.get("results", []):
            if not isinstance(item, dict):
                continue
            if str(item.get("name") or "").strip().lower() != category.lower():
                continue
            album_id = str(item.get("id") or "").strip()
            if album_id:
                self.__class__._category_album_cache[category] = album_id
                return album_id
        raise LibraryCategoryNotFound(details={"category": category})

    async def search_assets(
        self,
        *,
        limit: int,
        start: int,
        sort_by: str,
        sort_direction: str,
        search_keyword: str | None = None,
        tags: str | None = None,
        duration_range: str | None = None,
        uploaded_time_range: str | None = None,
        category_album_id: str | None = None,
    ) -> dict:
        params: dict[str, str | int] = {
            "limit": limit,
            "start": start,
            "sortBy": sort_by,
            "sortDirection": sort_direction,
            "scheme": "video",
            "approval": "approved",
        }
        if search_keyword:
            params["keyword"] = search_keyword
        if tags:
            params["tags"] = tags
        if duration_range:
            params["duration"] = duration_range
        if uploaded_time_range:
            params["uploadedTime"] = uploaded_time_range
        if category_album_id:
            return await self._request("GET", f"/api/v1/album/{category_album_id}", params=params)
        return await self._request(
            "GET",
            _LICENSED_VIDEOS_FOLDER_URL.removeprefix(self.base_url),
            params=params,
        )

    async def get_asset(self, asset_id: str) -> dict:
        payload = await self._request("GET", f"/api/v1/video/{asset_id}")
        if payload.get("id") == asset_id:
            return payload
        raise LibraryVideoNotFound(details={"asset_id": asset_id})

    @staticmethod
    def original_url_for_asset(raw_asset: dict) -> str:
        url = raw_asset.get("url") if isinstance(raw_asset.get("url"), dict) else {}
        original = str(url.get("directUrlOriginal") or "").strip()
        if original:
            return original
        raise LibraryProviderError(
            message="Library asset did not include a direct download URL",
            details={"asset_id": raw_asset.get("id")},
        )

    async def download_url_for_asset(self, raw_asset: dict) -> str:
        url = raw_asset.get("url") if isinstance(raw_asset.get("url"), dict) else {}
        api_binary_url = str(url.get("download") or "").strip()
        if not api_binary_url:
            raise LibraryProviderError(
                message="Library asset did not include a Canto download URL",
                details={"asset_id": raw_asset.get("id")},
            )
        token = await self._get_token()
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    api_binary_url,
                    headers={"Authorization": f"Bearer {token}"},
                    follow_redirects=False,
                )
        except httpx.HTTPError as exc:
            raise LibraryProviderError(
                message="Failed to reach Canto download endpoint",
                details={"asset_id": raw_asset.get("id"), "error": str(exc)},
            ) from exc
        location = response.headers.get("location", "").strip()
        if not location:
            raise LibraryProviderError(
                message="Canto did not return a signed download URL",
                details={"asset_id": raw_asset.get("id"), "status_code": response.status_code},
            )
        return location
