import pytest
from src.provider_config import answer_provider, jev_api_url, openai_base_url


def test_custom_provider_inferred_from_base_url(monkeypatch):
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.setenv("LLM_MODEL", "router/GLM-test")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://router.example/v1/")
    assert answer_provider() == "openai"
    assert openai_base_url() == "https://router.example/v1"


@pytest.mark.parametrize("url", ["", "file:///tmp/key", "https://user:secret@host/v1", "https://host/v1?key=secret", "https://host/v1#fragment"])
def test_reject_unsafe_endpoint(monkeypatch, url):
    monkeypatch.setenv("OPENAI_BASE_URL", url)
    with pytest.raises(ValueError, match="OPENAI_BASE_URL"):
        openai_base_url()


def test_jev_endpoint_and_model_override(monkeypatch):
    from src.visualization_router import provider_url, request_options
    from src.credentials import current_credentials
    token = current_credentials.set(None)
    try:
        monkeypatch.setenv("JEV_API_URL", "https://router.example/v1/systemone")
        monkeypatch.setenv("JEV_MODEL", "oc/jev-test")
        monkeypatch.setenv("TYPESAFE_API_KEY", "test-jev")
        assert jev_api_url() == provider_url() == "https://router.example/v1/systemone"
        assert request_options([])["json"]["model"] == "oc/jev-test"
        assert request_options([])["json"]["questions"]["visualization"]["type"] == "choice"
    finally:
        current_credentials.reset(token)


def test_server_mode_rejects_visitor_keys(monkeypatch):
    import asyncio
    from src.credentials import CredentialsMiddleware
    monkeypatch.setenv("PROVIDER_KEYS_MODE", "server")
    events = []
    async def inner(scope, receive, send):
        raise AssertionError("Visitor keys must not reach the agent")
    async def receive():
        return {"type": "http.disconnect"}
    async def send(event):
        events.append(event)
    asyncio.run(CredentialsMiddleware(inner)({"type": "http", "path": "/credentials/validate", "headers": [(b"x-openai-api-key", b"visitor"), (b"x-jev-api-key", b"visitor")]}, receive, send))
    assert events[0]["status"] == 400
