from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class RetrievalMetrics:
    total: int
    recall_at_1: float
    recall_at_3: float
    recall_at_5: float
    mrr: float
    precision_at_5: float


@dataclass(frozen=True)
class GenerationMetrics:
    citation_presence_rate: float | None
    citation_presence_eligible_cases: int
    citation_presence_cited_cases: int
    citation_correctness: float | None
    citation_correctness_eligible_cases: int
    citation_correctness_returned_citations: int
    citation_correctness_valid_citations: int
    citation_completeness: float | None
    citation_completeness_eligible_cases: int
    citation_completeness_expected_sources: int
    citation_completeness_covered_sources: int
    abstention_correctness: float | None
    abstention_eligible_cases: int
    abstention_correct_cases: int
    abstention_expected_abstentions: int
    abstention_expected_answers: int


def recall_at_k(
    expected_sources: set[str],
    retrieved_sources: Sequence[str],
    k: int,
) -> float:
    if not expected_sources:
        return 1.0 if not set(retrieved_sources[:k]) else 0.0
    return float(bool(expected_sources.intersection(retrieved_sources[:k])))


def reciprocal_rank(
    expected_sources: set[str],
    retrieved_sources: Sequence[str],
) -> float:
    for rank, source in enumerate(retrieved_sources, start=1):
        if source in expected_sources:
            return 1.0 / rank
    return 0.0


def precision_at_k(
    expected_sources: set[str],
    retrieved_sources: Sequence[str],
    k: int,
) -> float:
    ranked = list(retrieved_sources[:k])
    if not ranked:
        return 1.0 if not expected_sources else 0.0
    return len(expected_sources.intersection(ranked)) / len(ranked)


def calculate_retrieval_metrics(rows: Iterable[dict[str, Any]]) -> RetrievalMetrics:
    materialized = list(rows)
    if not materialized:
        return RetrievalMetrics(0, 0.0, 0.0, 0.0, 0.0, 0.0)
    return RetrievalMetrics(
        total=len(materialized),
        recall_at_1=_mean(
            recall_at_k(row["expected_sources"], row["retrieved_sources"], 1)
            for row in materialized
        ),
        recall_at_3=_mean(
            recall_at_k(row["expected_sources"], row["retrieved_sources"], 3)
            for row in materialized
        ),
        recall_at_5=_mean(
            recall_at_k(row["expected_sources"], row["retrieved_sources"], 5)
            for row in materialized
        ),
        mrr=_mean(
            reciprocal_rank(row["expected_sources"], row["retrieved_sources"])
            for row in materialized
        ),
        precision_at_5=_mean(
            precision_at_k(row["expected_sources"], row["retrieved_sources"], 5)
            for row in materialized
        ),
    )


def citation_score(
    cited_chunk_ids: Sequence[str],
    retrieved_chunk_ids: set[str],
    expected_source_ids: set[str],
    chunk_to_source: dict[str, str],
) -> dict[str, float]:
    valid = [chunk_id for chunk_id in cited_chunk_ids if chunk_id in retrieved_chunk_ids]
    source_valid = [
        chunk_to_source[chunk_id]
        for chunk_id in valid
        if chunk_id in chunk_to_source
    ]
    expected_count = max(len(expected_source_ids), 1)
    return {
        "citation_correctness": len(valid) / max(len(cited_chunk_ids), 1),
        "citation_completeness": len(
            expected_source_ids.intersection(source_valid)
        ) / expected_count,
    }


def calculate_generation_metrics(
    completed_rows: Iterable[dict[str, Any]],
) -> GenerationMetrics:
    rows = [
        row
        for row in completed_rows
        if row.get("status", "completed") == "completed"
    ]
    citation_rows = [
        row
        for row in rows
        if row["answerable"] and row["has_sufficient_context"]
    ]
    valid_citation_count = 0
    returned_citation_count = 0
    cited_case_count = 0
    expected_source_count = 0
    covered_source_count = 0
    for row in citation_rows:
        cited_ids = [citation["chunk_id"] for citation in row["citations"]]
        retrieved_ids = set(row["retrieved_chunk_ids"])
        valid_ids = [chunk_id for chunk_id in cited_ids if chunk_id in retrieved_ids]
        valid_citation_count += len(valid_ids)
        returned_citation_count += len(cited_ids)
        if valid_ids:
            cited_case_count += 1
        source_ids = {
            row["chunk_to_source"][chunk_id]
            for chunk_id in valid_ids
            if chunk_id in row["chunk_to_source"]
        }
        expected_sources = set(row["expected_source_ids"])
        expected_source_count += len(expected_sources)
        covered_source_count += len(expected_sources.intersection(source_ids))

    abstention_rows = []
    for row in rows:
        expected_sources = set(row["expected_source_ids"])
        retrieved_sources = set(row["retrieved_sources"])
        evidence_sufficient = bool(expected_sources.intersection(retrieved_sources))
        expected_abstention = not row["answerable"] or not evidence_sufficient
        actual_abstention = not row["has_sufficient_context"]
        abstention_rows.append(expected_abstention == actual_abstention)

    return GenerationMetrics(
        citation_presence_rate=_ratio(cited_case_count, len(citation_rows)),
        citation_presence_eligible_cases=len(citation_rows),
        citation_presence_cited_cases=cited_case_count,
        citation_correctness=_ratio(valid_citation_count, returned_citation_count),
        citation_correctness_eligible_cases=len(citation_rows),
        citation_correctness_returned_citations=returned_citation_count,
        citation_correctness_valid_citations=valid_citation_count,
        citation_completeness=_ratio(
            covered_source_count,
            expected_source_count,
        ),
        citation_completeness_eligible_cases=len(citation_rows),
        citation_completeness_expected_sources=expected_source_count,
        citation_completeness_covered_sources=covered_source_count,
        abstention_correctness=_ratio(
            sum(abstention_rows),
            len(abstention_rows),
        ),
        abstention_eligible_cases=len(abstention_rows),
        abstention_correct_cases=sum(abstention_rows),
        abstention_expected_abstentions=sum(
            not row["answerable"]
            or not set(row["expected_source_ids"]).intersection(
                row["retrieved_sources"]
            )
            for row in rows
        ),
        abstention_expected_answers=sum(
            row["answerable"]
            and bool(
                set(row["expected_source_ids"]).intersection(
                    row["retrieved_sources"]
                )
            )
            for row in rows
        ),
    )


def _ratio(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def _mean(values: Iterable[float]) -> float:
    values = list(values)
    return sum(values) / len(values) if values else 0.0
