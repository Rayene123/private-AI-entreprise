from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from time import monotonic
from typing import Any
from uuid import UUID

from app.core.exceptions import AppException
from app.evaluation.dataset import load_evaluation_dataset
from app.evaluation.metrics import (
    calculate_generation_metrics,
    calculate_retrieval_metrics,
    citation_score,
)
from app.services.generation_service import GenerationService
from app.services.retrieval_service import RetrievalService


def evaluate(
    dataset: dict[str, Any],
    *,
    user_id: UUID,
    retrieval_service: RetrievalService,
    generation_service: GenerationService | None = None,
    dataset_id_by_document_id: dict[str, str],
    mode: str,
    model_metadata: dict[str, Any],
) -> dict[str, Any]:
    retrieval_rows: list[dict[str, Any]] = []
    generation_rows: list[dict[str, Any]] = []
    for case in dataset["cases"]:
        started = monotonic()
        retrieval = retrieval_service.retrieve(user_id, case["question"], top_k=5)
        retrieval_latency_ms = round((monotonic() - started) * 1000, 2)
        retrieved_sources = [
            dataset_id_by_document_id.get(str(chunk.document_id), "unknown")
            for chunk in retrieval.results
        ]
        retrieval_rows.append(
            {
                "case_id": case["id"],
                "expected_sources": set(case["expected_source_ids"]),
                "retrieved_sources": retrieved_sources,
                "retrieved_chunks": [
                    {
                        "chunk_id": chunk.chunk_id,
                        "document_id": str(chunk.document_id),
                        "dataset_id": dataset_id_by_document_id.get(
                            str(chunk.document_id)
                        ),
                        "score": chunk.score,
                    }
                    for chunk in retrieval.results
                ],
                "latency_ms": retrieval_latency_ms,
            }
        )
        if mode == "full" and generation_service is not None:
            started = monotonic()
            try:
                answer = generation_service.ask_with_retrieval(
                    user_id,
                    case["question"],
                    retrieval,
                )
            except AppException as exc:
                generation_rows.append(
                    {
                        "case_id": case["id"],
                        "status": "failed",
                        "answerable": case["answerable"],
                        "error_code": exc.code,
                        "latency_ms": round((monotonic() - started) * 1000, 2),
                    }
                )
            else:
                retrieved_ids = {chunk.chunk_id for chunk in retrieval.results}
                chunk_sources = {
                    chunk.chunk_id: dataset_id_by_document_id.get(
                        str(chunk.document_id), "unknown"
                    )
                    for chunk in retrieval.results
                }
                scores = citation_score(
                    [citation.chunk_id for citation in answer.citations],
                    retrieved_ids,
                    set(case["expected_source_ids"]),
                    chunk_sources,
                )
                generation_rows.append(
                    {
                        "case_id": case["id"],
                        "status": "completed",
                        "answerable": case["answerable"],
                        "expected_source_ids": case["expected_source_ids"],
                        "retrieved_sources": retrieved_sources,
                        "retrieved_chunk_ids": sorted(retrieved_ids),
                        "chunk_to_source": chunk_sources,
                        "answer": answer.answer,
                        "has_sufficient_context": answer.has_sufficient_context,
                        "citations": [
                            {
                                "chunk_id": citation.chunk_id,
                                "document_id": str(citation.document_id),
                            }
                            for citation in answer.citations
                        ],
                        "latency_ms": round((monotonic() - started) * 1000, 2),
                        **scores,
                    }
                )
    metrics = calculate_retrieval_metrics(retrieval_rows)
    completed_generation = [
        row for row in generation_rows if row["status"] == "completed"
    ]
    generation_metrics = calculate_generation_metrics(completed_generation)
    failure_categories: dict[str, int] = {}
    for row in generation_rows:
        if row["status"] == "failed":
            code = row["error_code"]
            failure_categories[code] = failure_categories.get(code, 0) + 1
    result = {
        "dataset_version": dataset["version"],
        "mode": mode,
        "generated_at": datetime.now(UTC).isoformat(),
        "model_metadata": model_metadata,
        "retrieval_metrics": {
            "total": metrics.total,
            "recall_at_1": metrics.recall_at_1,
            "recall_at_3": metrics.recall_at_3,
            "recall_at_5": metrics.recall_at_5,
            "mrr": metrics.mrr,
            "precision_at_5": metrics.precision_at_5,
        },
        "retrieval_cases": _json_safe(retrieval_rows),
        "generation_cases": generation_rows,
        "generation_metrics": {
            "total": len(generation_rows),
            "completed": len(completed_generation),
            "failed": len(generation_rows) - len(completed_generation),
            "failure_categories": failure_categories,
            "insufficient_context_count": sum(
                not row["has_sufficient_context"] for row in completed_generation
            ),
            "mean_latency_ms": _mean(
                row["latency_ms"] for row in completed_generation
            ),
            **generation_metrics.__dict__,
            "answer_correctness": "manual_review_required",
            "faithfulness": "manual_review_required",
        },
        "limitations": [
            "Answer correctness and faithfulness require manual rubric scoring.",
            "Results reflect the authorized evaluation user only.",
            "Citation correctness measures retrieved-context and authorization validity, not semantic support.",
            "Citation metrics exclude failed generations and legitimate abstentions; denominators are reported explicitly.",
        ],
    }
    return result


def write_report(result: dict[str, Any], json_path: Path, markdown_path: Path) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(
        json.dumps(result, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    metrics = result["retrieval_metrics"]
    lines = [
        "# Module 12 RAG Evaluation",
        "",
        f"- Dataset version: `{result['dataset_version']}`",
        f"- Mode: `{result['mode']}`",
        f"- Generated: `{result['generated_at']}`",
        "",
        "## Retrieval metrics",
        "",
        "| Metric | Value |",
        "|---|---:|",
    ]
    lines.extend(
        f"| {name} | {value:.4f} |"
        for name, value in metrics.items()
        if name != "total"
    )
    lines.extend(
        [
            "",
            f"Cases evaluated: **{metrics['total']}**",
            "",
            "## Generation metrics",
            "",
            "| Metric | Value |",
            "|---|---:|",
        ]
    )
    generation_metrics = result.get("generation_metrics")
    if generation_metrics:
        lines.extend(
            f"| {name} | {_format_metric(value)} |"
            for name, value in generation_metrics.items()
            if name != "failure_categories"
        )
        lines.extend(
            [
                "",
                "Answer correctness and faithfulness: **manual review required**.",
            ]
        )
        failure_categories = generation_metrics.get("failure_categories", {})
        lines.append(
            f"- Failed generations: **{generation_metrics.get('failed', 0)}**"
        )
        lines.extend(
            f"- Failure `{code}`: **{count}**"
            for code, count in sorted(failure_categories.items())
        )
    lines.extend(
        [
            "",
            "## Limitations",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in result["limitations"])
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def load_dataset(path: Path) -> dict[str, Any]:
    return load_evaluation_dataset(path)


def _json_safe(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            **row,
            "expected_sources": sorted(row["expected_sources"]),
        }
        for row in rows
    ]


def _mean(values: Any) -> float:
    values = list(values)
    return sum(values) / len(values) if values else 0.0


def _format_metric(value: Any) -> str:
    if value is None:
        return "N/A"
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)
