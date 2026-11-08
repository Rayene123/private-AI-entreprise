"""Run read-only retrieval or full-RAG evaluation against existing services."""

from __future__ import annotations

import argparse
from pathlib import Path
from uuid import UUID

from app.core.config import get_settings
from app.evaluation.runner import evaluate, load_dataset, write_report
from app.integrations.supabase.client import get_service_supabase_client
from app.services.document_service import DocumentService
from app.services.generation_service import GenerationService
from app.services.permission_service import AuthorizationService
from app.services.retrieval_service import RetrievalService

ROOT = Path(__file__).resolve().parents[2]
DATASET_PATH = ROOT / "evaluation" / "golden_dataset.json"
RESULTS_DIR = ROOT / "evaluation" / "results"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mode",
        choices=("retrieval", "full"),
        default="retrieval",
        help="Evaluate retrieval only or retrieval plus POST /chat/ask services.",
    )
    parser.add_argument("--dataset", type=Path, default=DATASET_PATH)
    parser.add_argument("--json", type=Path, default=RESULTS_DIR / "module12-latest.json")
    parser.add_argument(
        "--markdown",
        type=Path,
        default=RESULTS_DIR / "module12-latest.md",
    )
    args = parser.parse_args()

    settings = get_settings()
    if not settings.dataset_ingestion_owner_id:
        raise RuntimeError("DATASET_INGESTION_OWNER_ID is required for evaluation")
    user_id = UUID(settings.dataset_ingestion_owner_id)
    dataset = load_dataset(args.dataset)
    client = get_service_supabase_client(settings)
    authorization = AuthorizationService(supabase_client=client)
    documents = DocumentService(authorization, supabase_client=client)
    retrieval = RetrievalService(documents, authorization, settings=settings)
    generation = (
        GenerationService(retrieval, settings=settings) if args.mode == "full" else None
    )
    visible_documents = documents.list_documents(user_id)
    dataset_id_by_document_id = {
        str(document.id): str(document.source_metadata["dataset_id"])
        for document in visible_documents
        if document.source_metadata
        and document.source_metadata.get("dataset_id")
    }
    result = evaluate(
        dataset,
        user_id=user_id,
        retrieval_service=retrieval,
        generation_service=generation,
        dataset_id_by_document_id=dataset_id_by_document_id,
        mode=args.mode,
        model_metadata={
            "embedding_model": settings.embedding_model,
            "embedding_dimension": settings.embedding_dimension,
            "chat_model": settings.ollama_chat_model,
            "retrieval_top_k": settings.retrieval_top_k,
            "retrieval_min_score": settings.retrieval_min_score,
            "qdrant_collection": settings.qdrant_collection_name,
        },
    )
    write_report(result, args.json, args.markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
