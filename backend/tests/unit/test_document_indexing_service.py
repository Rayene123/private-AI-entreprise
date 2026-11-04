from uuid import UUID, uuid4

from app.schemas.document import DocumentResponse
from app.schemas.ingestion import IngestionChunk, IngestionResponse
from app.services.document_indexing_service import DocumentIndexingService


DOCUMENT_ID = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
OWNER_ID = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")


def document() -> DocumentResponse:
    return DocumentResponse(
        id=DOCUMENT_ID,
        owner_id=OWNER_ID,
        title="Policy",
        status="active",
        access_level="private",
        created_at="2026-11-04T00:00:00Z",
        updated_at="2026-11-04T00:00:00Z",
    )


def ingestion() -> IngestionResponse:
    return IngestionResponse(
        document_id=DOCUMENT_ID,
        source_hash="a" * 64,
        file_type="text/plain",
        markdown_length=5,
        chunk_count=1,
        markdown="hello",
        chunks=[
            IngestionChunk(
                document_id=DOCUMENT_ID,
                chunk_index=0,
                text="hello",
                source_hash="a" * 64,
                chunk_id="b" * 64,
            )
        ],
    )


class Documents:
    def get_document(self, user_id, document_id):
        return document()


class Ingestion:
    def ingest(self, user_id, document_id):
        return ingestion()


class Embeddings:
    model = "test-embed"
    dimension = 3

    def embed(self, texts):
        return [[0.1, 0.2, 0.3] for _ in texts]


class Vectors:
    def __init__(self):
        self.points = None
        self.deleted = None
        self.collection_checked = False

    def ensure_collection(self):
        self.collection_checked = True

    def upsert(self, points):
        self.points = list(points)

    def delete_obsolete(self, document_id, source_hash):
        self.deleted = (document_id, source_hash)


def test_indexing_preserves_authorization_metadata_and_is_idempotent() -> None:
    vectors = Vectors()
    service = DocumentIndexingService(
        Documents(),
        Ingestion(),
        Embeddings(),
        vectors,
    )

    first = service.index(uuid4(), DOCUMENT_ID)
    second = service.index(uuid4(), DOCUMENT_ID)

    assert first.indexed_count == second.indexed_count == 1
    assert first.embedding_model == "test-embed"
    assert vectors.collection_checked is True
    assert vectors.points[0]["payload"]["owner_id"] == str(OWNER_ID)
    assert vectors.points[0]["payload"]["document_status"] == "active"
    assert vectors.points[0]["payload"]["source_hash"] == "a" * 64
    assert vectors.points[0]["id"] == vectors.points[0]["id"]
    assert vectors.deleted == (DOCUMENT_ID, "a" * 64)
