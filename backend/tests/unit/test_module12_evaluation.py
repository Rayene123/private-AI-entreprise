from pathlib import Path
from uuid import UUID

import pytest

from app.evaluation.dataset import load_evaluation_dataset
from app.evaluation.metrics import (
    calculate_generation_metrics,
    calculate_retrieval_metrics,
    citation_score,
    precision_at_k,
    recall_at_k,
    reciprocal_rank,
)
from app.evaluation.runner import write_report
from app.schemas.generation import AnswerCitation, AnswerResponse
from app.schemas.retrieval import (
    RetrievedChunk,
    RetrievedChunkMetadata,
    RetrievalResponse,
)
from app.evaluation.runner import evaluate


ROOT = Path(__file__).resolve().parents[3]
GOLDEN_DATASET = ROOT / "evaluation" / "golden_dataset.json"


def test_golden_dataset_has_required_shape_and_categories() -> None:
    dataset = load_evaluation_dataset(GOLDEN_DATASET)

    assert len(dataset["cases"]) >= 30
    assert {
        "hr_policies",
        "remote_work",
        "it_acceptable_use",
        "byod_procedures",
        "finance_travel_expenses",
        "cross_document",
        "unanswerable",
    } == {case["category"] for case in dataset["cases"]}


def test_golden_dataset_rejects_duplicate_ids(tmp_path) -> None:
    dataset = load_evaluation_dataset(GOLDEN_DATASET)
    dataset["cases"][1]["id"] = dataset["cases"][0]["id"]
    path = tmp_path / "dataset.json"
    import json

    path.write_text(json.dumps(dataset), encoding="utf-8")

    with pytest.raises(ValueError, match="duplicate"):
        load_evaluation_dataset(path)


def test_retrieval_metrics() -> None:
    assert recall_at_k({"a"}, ["b", "a"], 3) == 1.0
    assert recall_at_k({"a"}, ["b"], 1) == 0.0
    assert reciprocal_rank({"a"}, ["b", "a"]) == 0.5
    assert precision_at_k({"a"}, ["a", "b"], 5) == 0.5

    metrics = calculate_retrieval_metrics(
        [
            {"expected_sources": {"a"}, "retrieved_sources": ["a", "b"]},
            {"expected_sources": {"z"}, "retrieved_sources": ["b"]},
        ]
    )
    assert metrics.total == 2
    assert metrics.recall_at_1 == 0.5
    assert metrics.mrr == 0.5


def test_unanswerable_metric_requires_no_retrieved_sources() -> None:
    assert recall_at_k(set(), [], 5) == 1.0
    assert recall_at_k(set(), ["unrelated"], 5) == 0.0


def test_citation_scoring_rejects_citations_outside_context() -> None:
    scores = citation_score(
        ["allowed", "invented"],
        {"allowed"},
        {"CORP-IT-001"},
        {"allowed": "CORP-IT-001"},
    )

    assert scores == {
        "citation_correctness": 0.5,
        "citation_completeness": 1.0,
    }


def test_generation_metrics_distinguish_citations_and_abstentions() -> None:
    metrics = calculate_generation_metrics(
        [
            {
                "answerable": True,
                "has_sufficient_context": True,
                "citations": [{"chunk_id": "allowed"}],
                "retrieved_chunk_ids": ["allowed"],
                "chunk_to_source": {"allowed": "CORP-HR-001"},
                "expected_source_ids": ["CORP-HR-001"],
                "retrieved_sources": ["CORP-HR-001"],
            },
            {
                "answerable": True,
                "has_sufficient_context": True,
                "citations": [],
                "retrieved_chunk_ids": ["allowed"],
                "chunk_to_source": {"allowed": "CORP-HR-001"},
                "expected_source_ids": ["CORP-HR-001"],
                "retrieved_sources": ["CORP-HR-001"],
            },
            {
                "answerable": False,
                "has_sufficient_context": False,
                "citations": [],
                "retrieved_chunk_ids": [],
                "chunk_to_source": {},
                "expected_source_ids": [],
                "retrieved_sources": [],
            },
            {
                "answerable": True,
                "has_sufficient_context": True,
                "citations": [
                    {"chunk_id": "unexpected"},
                    {"chunk_id": "not-retrieved"},
                ],
                "retrieved_chunk_ids": ["unexpected"],
                "chunk_to_source": {"unexpected": "CORP-IT-001"},
                "expected_source_ids": ["CORP-HR-001", "CORP-HR-002"],
                "retrieved_sources": ["CORP-HR-001", "CORP-HR-002"],
            },
            {
                "answerable": True,
                "has_sufficient_context": False,
                "citations": [],
                "retrieved_chunk_ids": ["allowed"],
                "chunk_to_source": {"allowed": "CORP-HR-001"},
                "expected_source_ids": ["CORP-HR-001"],
                "retrieved_sources": [],
            },
        ]
    )

    assert metrics.citation_presence_rate == 2 / 3
    assert metrics.citation_presence_eligible_cases == 3
    assert metrics.citation_presence_cited_cases == 2
    assert metrics.citation_correctness == 2 / 3
    assert metrics.citation_correctness_returned_citations == 3
    assert metrics.citation_correctness_valid_citations == 2
    assert metrics.citation_completeness == 1 / 4
    assert metrics.citation_completeness_expected_sources == 4
    assert metrics.citation_completeness_covered_sources == 1
    assert metrics.abstention_correctness == 1.0
    assert metrics.abstention_expected_abstentions == 2
    assert metrics.abstention_expected_answers == 3


def test_generation_metrics_use_null_for_empty_denominators() -> None:
    metrics = calculate_generation_metrics([])

    assert metrics.citation_presence_rate is None
    assert metrics.citation_correctness is None
    assert metrics.citation_completeness is None
    assert metrics.abstention_correctness is None


def test_generation_metrics_exclude_failed_rows_and_score_incorrect_abstention() -> None:
    metrics = calculate_generation_metrics(
        [
            {
                "status": "failed",
                "answerable": True,
                "has_sufficient_context": True,
                "citations": [],
                "retrieved_chunk_ids": [],
                "chunk_to_source": {},
                "expected_source_ids": ["CORP-HR-001"],
                "retrieved_sources": [],
            },
            {
                "status": "completed",
                "answerable": True,
                "has_sufficient_context": False,
                "citations": [],
                "retrieved_chunk_ids": ["allowed"],
                "chunk_to_source": {"allowed": "CORP-HR-001"},
                "expected_source_ids": ["CORP-HR-001"],
                "retrieved_sources": ["CORP-HR-001"],
            },
        ]
    )

    assert metrics.citation_presence_eligible_cases == 0
    assert metrics.abstention_eligible_cases == 1
    assert metrics.abstention_correctness == 0.0


def test_report_generation_is_machine_and_human_readable(tmp_path) -> None:
    result = {
        "dataset_version": "test",
        "mode": "retrieval",
        "generated_at": "2026-01-01T00:00:00+00:00",
        "model_metadata": {"embedding_model": "test"},
        "retrieval_metrics": {
            "total": 1,
            "recall_at_1": 1.0,
            "recall_at_3": 1.0,
            "recall_at_5": 1.0,
            "mrr": 1.0,
            "precision_at_5": 1.0,
        },
        "retrieval_cases": [],
        "generation_cases": [],
        "generation_metrics": {
            "total": 1,
            "completed": 1,
            "failed": 0,
            "mean_latency_ms": 10.0,
            "mean_citation_correctness": 1.0,
            "mean_citation_completeness": 1.0,
            "answer_correctness": "manual_review_required",
            "faithfulness": "manual_review_required",
        },
        "limitations": ["manual scoring required"],
    }
    json_path = tmp_path / "result.json"
    markdown_path = tmp_path / "result.md"

    write_report(result, json_path, markdown_path)

    assert json_path.exists()
    assert "recall_at_1" in markdown_path.read_text(encoding="utf-8")
    assert "Generation metrics" in markdown_path.read_text(encoding="utf-8")


def test_evaluation_uses_only_chunks_returned_by_authorized_retrieval() -> None:
    retrieval_calls = 0

    class Retrieval:
        def retrieve(self, user_id, query, top_k):
            nonlocal retrieval_calls
            retrieval_calls += 1
            return RetrievalResponse(
                query=query,
                retrieved_count=1,
                results=[
                    RetrievedChunk(
                        document_id=UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
                        chunk_id="authorized-chunk",
                        content="authorized",
                        score=0.9,
                        metadata=RetrievedChunkMetadata(source_filename="policy.pdf"),
                    )
                ],
            )

    class Generation:
        def ask_with_retrieval(self, user_id, query, retrieval):
            return AnswerResponse(
                answer="authorized",
                citations=[
                    AnswerCitation(
                        document_id=retrieval.results[0].document_id,
                        chunk_id=retrieval.results[0].chunk_id,
                        filename=retrieval.results[0].metadata.source_filename,
                    )
                ],
                has_sufficient_context=True,
            )

    dataset = {
        "version": "test",
        "cases": [
            {
                "id": "SEC-001",
                "category": "hr_policies",
                "question": "What is allowed?",
                "expected_answer": "authorized",
                "expected_source_ids": ["CORP-HR-001"],
                "expected_department": "hr",
                "answerable": True,
                "evidence": [],
            }
        ],
    }

    result = evaluate(
        dataset,
        user_id=UUID("11111111-1111-1111-1111-111111111111"),
        retrieval_service=Retrieval(),
        generation_service=Generation(),
        dataset_id_by_document_id={
            "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa": "CORP-HR-001"
        },
        mode="full",
        model_metadata={},
    )

    assert result["retrieval_cases"][0]["retrieved_chunks"][0]["chunk_id"] == (
        "authorized-chunk"
    )
    assert retrieval_calls == 1
    assert result["generation_cases"][0]["citation_correctness"] == 1.0
    assert result["generation_cases"][0]["citation_completeness"] == 1.0
    assert "unauthorized" not in str(result)
