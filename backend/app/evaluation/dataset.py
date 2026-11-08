from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REQUIRED_FIELDS = {
    "id",
    "category",
    "question",
    "expected_answer",
    "expected_source_ids",
    "expected_department",
    "answerable",
    "evidence",
}
ALLOWED_CATEGORIES = {
    "hr_policies",
    "remote_work",
    "it_acceptable_use",
    "byod_procedures",
    "finance_travel_expenses",
    "cross_document",
    "unanswerable",
}


def load_evaluation_dataset(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    cases = payload.get("cases")
    if not isinstance(cases, list) or len(cases) < 30:
        raise ValueError("evaluation dataset must contain at least 30 cases")
    ids: set[str] = set()
    for case in cases:
        if not isinstance(case, dict) or not REQUIRED_FIELDS.issubset(case):
            raise ValueError("evaluation case is missing required fields")
        if case["id"] in ids:
            raise ValueError(f"duplicate evaluation case ID: {case['id']}")
        ids.add(case["id"])
        if case["category"] not in ALLOWED_CATEGORIES:
            raise ValueError(f"invalid evaluation category: {case['category']}")
        if not isinstance(case["expected_source_ids"], list):
            raise ValueError(f"expected sources must be a list: {case['id']}")
        if not isinstance(case["answerable"], bool):
            raise ValueError(f"answerable must be boolean: {case['id']}")
        if not case["answerable"] and case["category"] != "unanswerable":
            raise ValueError(f"unanswerable case has wrong category: {case['id']}")
    return payload
