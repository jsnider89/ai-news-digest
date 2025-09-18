import pytest
import requests

from app.ai.client import OpenAIProvider, ProviderError
from app.ai.pipeline import ProviderConfig


class DummyResponse:
    def __init__(self, status_code=200, payload=None, text=""):
        default_payload = {
            "choices": [{"message": {"content": "Hello"}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        }
        self.status_code = status_code
        self._payload = payload or default_payload
        self.text = text

    def raise_for_status(self):
        if 400 <= self.status_code:
            raise requests.exceptions.HTTPError("http error")

    def json(self):
        return self._payload


@pytest.fixture(autouse=True)
def set_openai_key(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")


def test_openai_provider_uses_max_completion_tokens(monkeypatch):
    captured = {}

    def fake_post(url, json, timeout):
        captured.update({"url": url, "json": json, "timeout": timeout})
        return DummyResponse()

    provider = OpenAIProvider(ProviderConfig(provider="openai", model="gpt-5-mini"))
    monkeypatch.setattr(provider._session, "post", fake_post)

    result, usage = provider.generate("Prompt", system_prompt="System")
    assert result == "Hello"
    assert "max_completion_tokens" in captured["json"]
    assert "completion_tokens" not in captured["json"]
    assert usage == {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}


def test_openai_provider_http_error_includes_body(monkeypatch):
    def fake_post(url, json, timeout):
        return DummyResponse(status_code=400, text='{"error": {"message": "bad"}}')

    provider = OpenAIProvider(ProviderConfig(provider="openai", model="gpt-5-mini"))
    monkeypatch.setattr(provider._session, "post", fake_post)

    with pytest.raises(ProviderError) as exc:
        provider.generate("Prompt")

    message = str(exc.value)
    assert "HTTP 400" in message
    assert "bad" in message
