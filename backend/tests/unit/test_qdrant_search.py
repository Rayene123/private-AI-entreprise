import httpx

from app.core.config import Settings
from app.integrations.qdrant import QdrantVectorStore


class Client:
    def __init__(self) -> None:
        self.call = None

    def request(self, method, url, **kwargs):
        self.call = (method, url, kwargs)
        return httpx.Response(
            200,
            json={"result": [{"id": "point", "score": 0.8, "payload": {}}]},
            request=httpx.Request(method, url),
        )


def test_qdrant_search_applies_authorized_document_filter() -> None:
    client = Client()
    store = QdrantVectorStore(
        Settings(
            embedding_dimension=2,
            qdrant_url="http://qdrant.test",
            qdrant_collection_name="documents",
        ),
        client=client,
    )
    from uuid import UUID

    store.search(
        [0.1, 0.2],
        top_k=3,
        min_score=0.4,
        document_ids=[UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")],
    )

    assert client.call[0:2] == (
        "POST",
        "http://qdrant.test/collections/documents/points/search",
    )
    body = client.call[2]["json"]
    assert body["limit"] == 3
    assert body["score_threshold"] == 0.4
    assert body["filter"]["should"][0]["match"]["value"].startswith("aaaaaaaa")
