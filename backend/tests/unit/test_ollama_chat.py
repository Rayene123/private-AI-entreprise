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


@pytest.mark.parametrize("error", [httpx.TimeoutException("timeout"), ValueError("bad")])
def test_chat_provider_failures_are_safe(error) -> None:
    provider = OllamaChatProvider(
        Settings(embedding_url="http://ollama.test"),
        client=Client(error=error),
    )

    with pytest.raises(IntegrationUnavailableError) as raised:
        provider.generate("system", "question")
    assert raised.value.code in {"chat_provider_unavailable", "chat_response_invalid"}
