"""Server-side provider settings. Never send these secrets to the browser."""
import os
from urllib.parse import urlsplit


def server_provider_mode():
    return os.environ.get("PROVIDER_KEYS_MODE", "byok").strip().lower() == "server"


def answer_model():
    name = os.environ.get("LLM_MODEL", "chat-latest").strip()
    if not name:
        raise ValueError("LLM_MODEL must not be blank.")
    return name


def answer_provider():
    name = answer_model()
    provider = os.environ.get("LLM_PROVIDER", "").strip().lower()
    if provider:
        if provider not in {"openai", "anthropic"}:
            raise ValueError("LLM_PROVIDER must be openai or anthropic.")
        return provider
    if os.environ.get("OPENAI_BASE_URL", "").strip():
        return "openai"
    if name == "chat-latest" or name.startswith("gpt-"):
        return "openai"
    if name.startswith("claude-"):
        return "anthropic"
    raise ValueError("LLM_MODEL needs LLM_PROVIDER=openai for custom OpenAI-compatible models.")


def _endpoint(value, setting):
    value = value.strip().rstrip("/")
    try:
        parsed = urlsplit(value)
        valid = parsed.scheme in {"http", "https"} and parsed.hostname and not (
            parsed.username or parsed.password or parsed.query or parsed.fragment
        )
        parsed.port  # Validate the port without logging the URL.
    except ValueError:
        valid = False
    if not valid:
        raise ValueError(f"{setting} must be an HTTP(S) URL without credentials, query, or fragment.")
    return value


def openai_base_url():
    return _endpoint(os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"), "OPENAI_BASE_URL")


def jev_api_url():
    return _endpoint(os.environ.get("JEV_API_URL", "https://api.typesafe.ai/v1/systemone"), "JEV_API_URL")
