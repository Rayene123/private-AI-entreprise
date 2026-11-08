import httpx
import pytest

from app.core.config import Settings
from app.core.exceptions import IntegrationUnavailableError
from app.integrations.ollama import OllamaChatProvider


class Client:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.calls = []

    def post(self, url, json):
        self.calls.append((url, json))
        if self.error:
            raise self.error
        return self.response


def test_chat_provider_returns_message_content() -> None:
    client = Client(
        httpx.Response(
            200,
            json={"message": {"content": '{"answer":"ok"}'}},
            request=httpx.Request("POST", "http://ollama.test/api/chat"),
        )
    )
    provider = OllamaChatProvider(
        Settings(embedding_url="http://ollama.test"),
        client=client,
    )

    assert provider.generate("system", "question") == '{"answer":"ok"}'
    assert client.calls[0][1]["format"] == "json"


def test_chat_provider_sends_json_schema_when_supplied() -> None:
    schema = {
        "type": "object",
        "properties": {"answer": {"type": "string"}},
        "required": ["answer"],
        "additionalProperties": False,
    }
    client = Client(
        httpx.Response(
            200,
            json={"message": {"content": '{"answer":"ok"}'}},
            request=httpx.Request("POST", "http://ollama.test/api/chat"),
        )
    )
    provider = OllamaChatProvider(
        Settings(embedding_url="http://ollama.test"),
        client=client,
    )

    provider.generate("system", "question", response_schema=schema)

    assert client.calls[0][1]["format"] == schema


@pytest.mark.parametrize("error", [httpx.TimeoutException("timeout"), ValueError("bad")])
def test_chat_provider_failures_are_safe(error) -> None:
    provider = OllamaChatProvider(
        Settings(embedding_url="http://ollama.test"),
        client=Client(error=error),
    )

    with pytest.raises(IntegrationUnavailableError) as raised:
        provider.generate("system", "question")
    assert raised.value.code in {"chat_provider_unavailable", "chat_response_invalid"}


def test_chat_timeout_and_connection_failures_are_classified() -> None:
    for error, category in [
        (httpx.TimeoutException("timeout"), "timeout"),
        (httpx.ConnectError("connection"), "connection_error"),
    ]:
        provider = OllamaChatProvider(
            Settings(embedding_url="http://ollama.test"),
            client=Client(error=error),
        )

        with pytest.raises(IntegrationUnavailableError) as raised:
            provider.generate("system", "question")

        assert raised.value.code == "chat_provider_unavailable"
        assert raised.value.provider_failure_category == category


def test_chat_http_and_invalid_response_failures_are_classified() -> None:
    http_client = Client(
        httpx.Response(
            503,
            json={"error": "unavailable"},
            request=httpx.Request("POST", "http://ollama.test/api/chat"),
        )
    )
    with pytest.raises(IntegrationUnavailableError) as raised:
        OllamaChatProvider(
            Settings(embedding_url="http://ollama.test"),
            client=http_client,
        ).generate("system", "question")
    assert raised.value.provider_failure_category == "http_provider_error"
    assert raised.value.provider_status_code == 503

    invalid_client = Client(
        httpx.Response(
            200,
            json={"message": {}},
            request=httpx.Request("POST", "http://ollama.test/api/chat"),
        )
    )
    with pytest.raises(IntegrationUnavailableError) as raised:
        OllamaChatProvider(
            Settings(embedding_url="http://ollama.test"),
            client=invalid_client,
        ).generate("system", "question")
    assert raised.value.provider_failure_category == "invalid_provider_response"
