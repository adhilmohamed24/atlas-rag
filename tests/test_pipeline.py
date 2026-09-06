import os
os.environ["DEMO_MODE"] = "1"
os.environ["ADMIN_TOKEN"] = "test-owner"

import pytest
from fastapi.testclient import TestClient
from app.ingest import chunks, validate_url, pdf_document
from app.store import Store

def test_chunking_preserves_end_and_overlap():
    text = " ".join(f"word{i}" for i in range(900))
    result = chunks(text)
    assert len(result) > 1
    assert result[-1].endswith("word899")
    assert result[0][-200:] == result[1][:200]
    assert max(map(len, result)) <= 1400

@pytest.mark.parametrize("url", ["http://example.com", "https://127.0.0.1", "https://[::1]", "https://user:pass@example.com", "https://example.com:8080"])
def test_private_urls_rejected(url):
    with pytest.raises(ValueError):
        validate_url(url)

def test_non_pdf_rejected():
    with pytest.raises(ValueError):
        pdf_document(b"not a pdf")

def test_index_idempotency_visibility_and_delete(tmp_path):
    store = Store(demo=True, path=str(tmp_path / "qdrant"))
    try:
        public = store.ingest("Public", "sample", [(1, "Oranges citrus fruit are harvested from orange trees in winter.")], public=True)
        private = store.ingest("Private", "pdf", [(2, "Private confidential launch password codename Nebula secret mission.")])
        store.ingest("Private", "pdf", [(2, "Private confidential launch password codename Nebula secret mission.")])
        assert len(store.documents()) == 2
        assert [d["id"] for d in store.documents(True)] == [public["id"]]
        assert all(s["public"] for s in store.search("Private confidential launch password", public_only=True))
        assert store.search("Private confidential launch password", ids=[private["id"]])[0]["page"] == 2
        store.delete(private["id"])
        assert len(store.documents()) == 1
    finally:
        store.client.close()

def test_api_stream_and_auth(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    from app.main import app
    with TestClient(app) as client:
        assert client.get("/").status_code == 200
        assert client.get("/api/health").json()["mode"] == "demo"
        assert client.delete("/api/documents/anything").status_code == 401
        assert client.post("/api/ingest/url", json={"value":"https://example.com"}).status_code == 401
        r = client.post("/api/chat", json={"question":"How does Atlas retrieve and cite evidence?"})
        assert r.status_code == 200
        assert "event: sources" in r.text and "event: token" in r.text and "event: done" in r.text
        assert "no LLM generation" in r.text
        r = client.post("/api/chat", json={"question":"something", "document_ids":["missing"]})
        assert "enough evidence" in r.text
        assert client.post("/api/chat", json={"question":""}).status_code == 422

def test_live_generation_stream_contract(tmp_path, monkeypatch):
    """Exercise the live code path with a fake provider, without claiming model quality."""
    import httpx
    import app.main as main
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("LLM_API_KEY", "fake-provider-key")
    with TestClient(main.app) as client:
        monkeypatch.setattr(main, "DEMO", False)
        assert client.post("/api/chat", json={"question":"Atlas pipeline"}).status_code == 401
        class ProviderResponse:
            async def __aenter__(self): return self
            async def __aexit__(self, *args): pass
            def raise_for_status(self): pass
            async def aiter_lines(self):
                yield 'data: {"choices":[{"delta":{"content":"Evidence-backed answer [1]."}}]}'
                yield 'data: [DONE]'
        class Provider:
            def __init__(self, **kwargs): pass
            async def __aenter__(self): return self
            async def __aexit__(self, *args): pass
            def stream(self, method, url, **kwargs):
                assert kwargs["json"]["stream"] is True
                assert "DOCUMENT EXCERPTS" in kwargs["json"]["messages"][1]["content"]
                return ProviderResponse()
        monkeypatch.setattr(httpx, "AsyncClient", Provider)
        response = client.post("/api/chat", headers={"Authorization":"Bearer test-owner"}, json={"question":"How does Atlas retrieve and cite evidence?"})
        assert "Evidence-backed answer [1]." in response.text
        assert "event: done" in response.text
        assert "event: error" not in response.text
        monkeypatch.setenv("PUBLIC_LLM_DAILY_LIMIT", "1")
        main.guest_budget.update(day="", used=0)
        public = client.post("/api/chat", json={"question":"How does Atlas retrieve and cite evidence?"})
        assert public.status_code == 200
        assert "Evidence-backed answer [1]." in public.text
        assert client.post("/api/chat", json={"question":"another question"}).status_code == 429
