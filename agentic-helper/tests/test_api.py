from fastapi.testclient import TestClient

from app.api.deps import get_chat_service, get_db, get_rag_service
from app.main import app


class DummyChunk:
    def __init__(self, cid: int, source: str) -> None:
        self.id = cid
        self.source = source


class FakeChatService:
    async def ask(self, _db, user_id: str, question: str):
        return f"stub answer for {user_id}: {question}", [DummyChunk(1, "faq")], "UNCLEAR"

    async def ask_video_search(self, _db, user_id: str, question: str):
        return (
            f"video search for {user_id}: {question}",
            [{"video_id": "vid-1", "title": "Demo video"}],
            {"query": question, "k": 10},
        )


class FakeRagService:
    async def ingest_documents(self, _db, docs, replace_source: bool = False):
        return len(docs)


async def fake_db():
    yield object()


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

    app.dependency_overrides[get_db] = fake_db
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
    assert video_chat.json()["search_url"] == "http://localhost:3000/search?q=show+me+football+clips"
    assert video_chat.json()["search_action"] == {
        "type": "apply_video_search",
        "auto_apply": True,
        "filters": {"query": "show me football clips", "k": 10},
        "url": "http://localhost:3000/search?q=show+me+football+clips",
    }

    app.dependency_overrides.clear()
