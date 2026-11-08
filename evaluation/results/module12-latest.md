# Module 12 RAG Evaluation

- Dataset version: `module12-v1`
- Mode: `full`
- Generated: `2026-11-08T20:36:37.285017+00:00`

## Retrieval metrics

| Metric | Value |
|---|---:|
| recall_at_1 | 0.8108 |
| recall_at_3 | 0.8378 |
| recall_at_5 | 0.8378 |
| mrr | 0.8198 |
| precision_at_5 | 0.1838 |

Cases evaluated: **37**

## Generation metrics

| Metric | Value |
|---|---:|
| total | 37 |
| completed | 20 |
| failed | 17 |
| insufficient_context_count | 13 |
| mean_latency_ms | 42240.6000 |
| citation_presence_rate | 1.0000 |
| citation_presence_eligible_cases | 7 |
| citation_presence_cited_cases | 7 |
| citation_correctness | 1.0000 |
| citation_correctness_eligible_cases | 7 |
| citation_correctness_returned_citations | 7 |
| citation_correctness_valid_citations | 7 |
| citation_completeness | 0.6250 |
| citation_completeness_eligible_cases | 7 |
| citation_completeness_expected_sources | 8 |
| citation_completeness_covered_sources | 5 |
| abstention_correctness | 0.5500 |
| abstention_eligible_cases | 20 |
| abstention_correct_cases | 11 |
| abstention_expected_abstentions | 4 |
| abstention_expected_answers | 16 |
| answer_correctness | manual_review_required |
| faithfulness | manual_review_required |

Answer correctness and faithfulness: **manual review required**.
- Failed generations: **17**
- Failure `answer_response_invalid`: **12**
- Failure `chat_provider_unavailable`: **5**

## Limitations

- Answer correctness and faithfulness require manual rubric scoring.
- Results reflect the authorized evaluation user only.
- Citation correctness measures retrieved-context and authorization validity, not semantic support.
- Citation metrics exclude failed generations and legitimate abstentions; denominators are reported explicitly.
