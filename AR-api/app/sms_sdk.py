"""SMS API client helpers."""

from __future__ import annotations

import logging
from http import HTTPStatus
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class SMSAPIError(Exception):
    """Raised when SMS API call fails due to network, timeout, or server errors."""

    def __init__(self, message: str, cause: str | None = None) -> None:
        super().__init__(message)
        self.cause = cause


def _build_sms_headers() -> dict[str, str]:
    headers: dict[str, str] = {}
    if settings.SMS_X_API_KEY:
        headers["x-api-key"] = settings.SMS_X_API_KEY
    if settings.SMS_API_KEY:
        headers["Authorization"] = f"Bearer {settings.SMS_API_KEY}"
    return headers


async def _get_user_details(
    endpoint: str,
    params: dict[str, str],
    timeout_seconds: int,
) -> dict[str, Any]:
    """
    Fetch user details from SMS API.

    Returns:
        JSON response dict on success.

    Raises:
        SMSAPIError: When the API call fails due to network issues, timeout,
            HTTP errors, or invalid responses.
    """
    if not settings.SMS_BASE_URL:
        logger.warning("SMS_BASE_URL is not configured; skipping SMS API lookup")
        raise SMSAPIError("SMS_BASE_URL is not configured", cause="config_missing")

    url = f"{settings.SMS_BASE_URL.rstrip('/')}/{endpoint.lstrip('/')}"
    headers = _build_sms_headers()
    try:
        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            response = await client.get(
                url,
                params=params,
                headers=headers or None,
            )
    except httpx.TimeoutException:
        logger.warning("SMS API timeout for %s", url)
        raise SMSAPIError(f"SMS API timeout for {url}", cause="timeout")
    except httpx.HTTPError as exc:
        logger.exception("SMS API lookup failed for %s", url)
        raise SMSAPIError(f"SMS API request failed for {url}", cause="http_error") from exc

    if response.status_code != HTTPStatus.OK:
        logger.warning(
            "SMS API returned status %s for %s",
            response.status_code,
            url,
        )
        raise SMSAPIError(
            f"SMS API returned status {response.status_code} for {url}",
            cause="bad_status",
        )

    try:
        return response.json()
    except ValueError as exc:
        logger.warning("SMS API response is not valid JSON for %s", url)
        raise SMSAPIError(
            f"SMS API response is not valid JSON for {url}",
            cause="invalid_json",
        ) from exc


async def get_instagram_user_details(
    handle: str,
    timeout_seconds: int,
) -> dict[str, Any]:
    """
    Get Instagram user details.

    Raises:
        SMSAPIError: When the SMS API call fails.
    """
    return await _get_user_details(
        endpoint="instagram/user_details",
        params={"handle": handle},
        timeout_seconds=timeout_seconds,
    )


async def get_tiktok_user_details(
    handle: str,
    timeout_seconds: int,
) -> dict[str, Any]:
    """
    Get TikTok user details.

    Raises:
        SMSAPIError: When the SMS API call fails.
    """
    if not handle.startswith("@"):
        handle = f"@{handle}"
    return await _get_user_details(
        endpoint="tiktok/user_details",
        params={"handle": handle, "source": "TOKAPI"},
        timeout_seconds=timeout_seconds,
    )


async def get_youtube_channel_details(
    name: str,
    timeout_seconds: int,
) -> dict[str, Any]:
    """
    Get YouTube channel details.

    Raises:
        SMSAPIError: When the SMS API call fails.
    """
    return await _get_user_details(
        endpoint="youtube/channels/details",
        params={"name": name},
        timeout_seconds=timeout_seconds,
    )


async def get_facebook_page_details(
    url: str,
    timeout_seconds: int,
) -> dict[str, Any]:
    """
    Get Facebook page details.

    Raises:
        SMSAPIError: When the SMS API call fails.
    """
    return await _get_user_details(
        endpoint="facebook/pages/details",
        params={"url": url},
        timeout_seconds=timeout_seconds,
    )


async def get_twitter_user_details(
    handle: str,
    timeout_seconds: int,
) -> dict[str, Any]:
    """
    Get Twitter/X user details.

    Raises:
        SMSAPIError: When the SMS API call fails.
    """
    return await _get_user_details(
        endpoint="twitter/users/details",
        params={"handle": handle},
        timeout_seconds=timeout_seconds,
    )


async def get_snapchat_user_details(
    handle: str,
    timeout_seconds: int,
) -> dict[str, Any]:
    """
    Get Snapchat user details.

    Raises:
        SMSAPIError: When the SMS API call fails.
    """
    return await _get_user_details(
        endpoint="snapchat/users/details",
        params={"handle": handle},
        timeout_seconds=timeout_seconds,
    )
