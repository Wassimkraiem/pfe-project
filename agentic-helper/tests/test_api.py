from fastapi.testclient import TestClient

from app.api.deps import get_chat_service, get_rag_service
from app.main import app
from app.services.video_search import VideoSearchPlan, VideoSearchService


class DummyChunk:
    def __init__(self, cid: str | int, source: str) -> None:
        self.id = cid
        self.source = source


class FakeChatService:
    async def ask(self, user_id: str, question: str):
        return f"stub answer for {user_id}: {question}", [DummyChunk(1, "faq")], "UNCLEAR"

    async def ask_video_search(self, user_id: str, question: str):
        return (
            f"video search for {user_id}: {question}",
            [{"video_id": "vid-1", "title": "Demo video"}],
            {"query": question, "k": 10},
        )


class FakeRagService:
    def __init__(self) -> None:
        self.items = {
            "vec-1": DummyChunk("vec-1", "faq"),
            "vec-2": DummyChunk("vec-2", "bviral_qas"),
        }
        self.items["vec-1"].content = "hello world"
        self.items["vec-1"].metadata_json = {"row_number": 1}
        self.items["vec-1"].score = 0.91
        self.items["vec-2"].content = "payment answer"
        self.items["vec-2"].metadata_json = {}
        self.items["vec-2"].score = 0.88

    async def ingest_documents(self, docs, replace_source: bool = False):
        return len(docs)

    async def list_chunks(self, limit: int = 20, offset: str | None = None, source: str | None = None):
        items = list(self.items.values())
        if source:
            items = [item for item in items if item.source == source]
        return items[:limit], None

    async def search_chunks(self, *, query: str, limit: int = 20, source: str | None = None):
        items = list(self.items.values())
        if source:
            items = [item for item in items if item.source == source]
        return [item for item in items if query.lower() in item.content.lower()][:limit]

    async def get_chunk(self, point_id: str):
        return self.items.get(point_id)

    async def create_chunk(self, *, source: str, content: str, metadata_json: dict | None = None):
        item = DummyChunk("vec-created", source)
        item.content = content
        item.metadata_json = metadata_json or {}
        item.score = None
        self.items[item.id] = item
        return item

    async def update_chunk(self, point_id: str, *, source=None, content=None, metadata_json=None):
        item = self.items.get(point_id)
        if item is None:
            return None
        if source is not None:
            item.source = source
        if content is not None:
            item.content = content
        if metadata_json is not None:
            item.metadata_json = metadata_json
        return item

    async def delete_chunk(self, point_id: str):
        return self.items.pop(point_id, None) is not None


def test_health():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_requires_api_key():
    client = TestClient(app)
    response = client.post("/api/v1/chat", json={"input_message": "hello"})
    assert response.status_code == 401


def test_chat_and_rag_routes():
    fake_chat = FakeChatService()
    fake_rag = FakeRagService()

    app.dependency_overrides[get_chat_service] = lambda: fake_chat
    app.dependency_overrides[get_rag_service] = lambda: fake_rag

    client = TestClient(app)
    headers = {"x-api-key": "change-me", "x-user-id": "user-123"}

    ingest = client.post(
        "/api/v1/rag/ingest",
        json={"replace_source": False, "documents": [{"source": "faq", "text": "hello"}]},
        headers=headers,
    )
    assert ingest.status_code == 200
    assert ingest.json()["chunks_created"] == 1

    chat = client.post(
        "/api/v1/chat",
        json={"input_message": "hi"},
        headers=headers,
    )
    assert chat.status_code == 200
    assert chat.json()["answer"] == "stub answer for user-123: hi"
    assert chat.json()["interest_label"] == "UNCLEAR"
    assert chat.json()["sources"] == [{"chunk_id": 1, "source": "faq"}]

    video_chat = client.post(
        "/api/v1/chat",
        json={"input_message": "show me football clips", "mode": "video_search"},
        headers=headers,
    )
    assert video_chat.status_code == 200
    assert video_chat.json()["answer"] == ""
    assert video_chat.json()["videos"] == [{"video_id": "vid-1", "title": "Demo video"}]
    assert video_chat.json()["search_filters"] == {"query": "show me football clips", "k": 10}
    assert video_chat.json()["search_url"] == "http://localhost:3000/search?q=show+me+football+clips&k=10"
    assert video_chat.json()["search_action"] == {
        "type": "apply_video_search",
        "auto_apply": True,
        "filters": {"query": "show me football clips", "k": 10},
        "url": "http://localhost:3000/search?q=show+me+football+clips&k=10",
    }

    vectors = client.get("/api/v1/rag/vectors", headers=headers)
    assert vectors.status_code == 200
    assert vectors.json()["items"][0]["id"] == "vec-1"

    search = client.get("/api/v1/rag/vectors/search", params={"query": "payment"}, headers=headers)
    assert search.status_code == 200
    assert search.json()["items"] == [
        {
            "id": "vec-2",
            "source": "bviral_qas",
            "content": "payment answer",
            "metadata_json": {},
            "score": 0.88,
        }
    ]

    get_vector = client.get("/api/v1/rag/vectors/vec-1", headers=headers)
    assert get_vector.status_code == 200
    assert get_vector.json()["content"] == "hello world"

    create_vector = client.post(
        "/api/v1/rag/vectors",
        json={"source": "manual", "content": "new chunk", "metadata_json": {"tag": "x"}},
        headers=headers,
    )
    assert create_vector.status_code == 201
    assert create_vector.json()["id"] == "vec-created"

    update_vector = client.put(
        "/api/v1/rag/vectors/vec-1",
        json={"content": "updated content", "metadata_json": {"tag": "updated"}},
        headers=headers,
    )
    assert update_vector.status_code == 200
    assert update_vector.json()["content"] == "updated content"
    assert update_vector.json()["metadata_json"] == {"tag": "updated"}

    delete_vector = client.delete("/api/v1/rag/vectors/vec-2", headers=headers)
    assert delete_vector.status_code == 200
    assert delete_vector.json() == {"id": "vec-2", "deleted": True}

    app.dependency_overrides.clear()


def test_video_search_plan_normalization_for_ranking_and_filters():
    service = VideoSearchService(client=None, filter_llm=None, filter_prompt="")
    plan = VideoSearchPlan(query="animal videos", k=5)

    normalized = service.normalize_plan(
        plan,
        question="top animal videos under 20 seconds vertical 1080x1920",
    )

    assert normalized["sort_by"] == "views"
    assert normalized["sort_order"] == "desc"
    assert normalized["k"] == 5
    assert normalized["limit"] == 5
    assert normalized["categories"] == ["Animals"]
    assert normalized["duration_max"] == 20.0
    assert normalized["orientation"] == ["Portrait"]
    assert normalized["resolutions"] == ["1080x1920"]


def test_video_search_plan_followup_show_more_uses_previous_page():
    service = VideoSearchService(client=None, filter_llm=None, filter_prompt="")
    plan = VideoSearchPlan(query="", k=10)

    normalized = service.normalize_plan(
        plan,
        question="show more",
        previous_plan={"query": "funny dogs", "offset": 10, "limit": 10, "categories": ["Animals"]},
    )

    assert normalized["query"] == "funny dogs"
    assert normalized["offset"] == 20
    assert normalized["limit"] == 10
    assert normalized["categories"] == ["Animals"]


def test_video_search_plan_top_count_overrides_default_limit():
    service = VideoSearchService(client=None, filter_llm=None, filter_prompt="")
    plan = VideoSearchPlan(query="", k=10, limit=10)

    normalized = service.normalize_plan(plan, question="top 5 videos")
    payload = service.to_advanced_search_payload(normalized)

    assert normalized["sort_by"] == "views"
    assert normalized["sort_order"] == "desc"
    assert normalized["k"] == 5
    assert normalized["limit"] == 5
    assert payload["pagination"] == {"offset": 0, "limit": 5}


def test_video_search_plan_caps_requested_count_to_ten():
    service = VideoSearchService(client=None, filter_llm=None, filter_prompt="")
    plan = VideoSearchPlan(query="", k=10, limit=10)

    normalized = service.normalize_plan(plan, question="top 50 animal videos")
    payload = service.to_advanced_search_payload(normalized)

    assert normalized["k"] == 10
    assert normalized["limit"] == 10
    assert payload["pagination"] == {"offset": 0, "limit": 10}


def test_video_search_answer_uses_returned_count_not_total_matches():
    service = VideoSearchService(client=None, filter_llm=None, filter_prompt="")

    answer = service._build_answer(
        videos=[{"video_id": "v1"}, {"video_id": "v2"}, {"video_id": "v3"}],
        total=93,
    )

    assert answer.startswith("I found 3 matching videos.")


def test_video_search_plan_detects_count_for_animals_phrase():
    service = VideoSearchService(client=None, filter_llm=None, filter_prompt="")
    plan = VideoSearchPlan(query="", k=10, limit=10)

    normalized = service.normalize_plan(plan, question="get me 5 animals videos")
    payload = service.to_advanced_search_payload(normalized)

    assert normalized["k"] == 5
    assert normalized["limit"] == 5
    assert payload["pagination"] == {"offset": 0, "limit": 5}


def test_video_search_plan_requested_count_resets_offset_for_non_show_more_followup():
    service = VideoSearchService(client=None, filter_llm=None, filter_prompt="")
    plan = VideoSearchPlan(query="", k=10, limit=10, offset=0)

    normalized = service.normalize_plan(
        plan,
        question="again give me 5 videos",
        previous_plan={"query": "animals", "offset": 30, "limit": 10, "categories": ["Animals"]},
    )

    assert normalized["query"] == "animals"
    assert normalized["k"] == 5
    assert normalized["limit"] == 5
    assert normalized["offset"] == 0
