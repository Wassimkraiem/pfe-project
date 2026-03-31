import pytest
from videosearch_sdk import VideoSearchSDK
import uuid
import os

API_URL = "http://http://localhost:5000"
API_KEY = os.getenv("API_KEY", "local-dev-key")


def unique_video_id():
    return f"pytest_{uuid.uuid4().hex[:8]}"


@pytest.fixture
def sdk():
    return VideoSearchSDK(API_URL, api_key=API_KEY)


def test_full_video_flow(sdk):
    video_id = unique_video_id()
    video_data = {
        "video_id": video_id,
        "service_identifier": "rms",
        "video_data": {"title": "Pytest Video", "views": 1},
    }

    # Create video
    create_resp = sdk.create_video(video_data)
    assert "error" not in create_resp, f"Create error: {create_resp}"

    # Get video
    get_resp = sdk.get_video(video_id)
    assert "error" not in get_resp, f"Get error: {get_resp}"
    assert get_resp["data"]["videos"][0]["video_id"] == video_id
    assert get_resp["data"]["videos"][0]["rms"]["data"]["title"] == "Pytest Video"

    # Search video
    search_resp = sdk.search_videos({"video_id": video_id})
    assert "error" not in search_resp, f"Search error: {search_resp}"
    found = any(v["video_id"] == video_id for v in search_resp["data"]["videos"])
    assert found, f"Video {video_id} not found in search results"

    # Delete video
    delete_resp = sdk.delete_video(video_id)
    assert "error" not in delete_resp, f"Delete error: {delete_resp}"
    assert (
        "successfully" in delete_resp.get("message", "")
        or "deleted" in str(delete_resp).lower()
    )

    # Confirm deletion
    get_after_delete = sdk.get_video(video_id)
    assert (
        get_after_delete["data"]["videos"] == []
        or get_after_delete["data"]["videos"] is None
    )
