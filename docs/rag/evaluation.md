# Module 12 — RAG evaluation

Module 12 evaluates the existing permission-aware retrieval and generation
services read-only. It does not write documents, Storage objects, or Qdrant
points.

## Golden dataset

[`evaluation/golden_dataset.json`](../../evaluation/golden_dataset.json) contains
37 source-scoped cases covering HR, remote work, acceptable use, BYOD, finance,
cross-document comparisons, and unsupported questions. Expected facts preserve
the identity of the five source institutions represented by the six PDFs.

Each case contains a unique ID, category, question, expected answer/key facts,
expected source dataset IDs, department, answerability, and evidence notes
with page references where available.

## Metrics

- Recall@1, Recall@3, and Recall@5 measure whether an expected source appears
  in the ranked prefix.
- MRR rewards an expected source appearing higher in the ranking.
- Precision@5 measures the fraction of the top five results that are expected
  sources.
- Citation presence rate is calculated only for completed, answerable responses
  where the model reported sufficient context. A response without citations is
  a zero, not an excluded case.
- Citation correctness is valid retrieved-context coverage: valid cited chunk
  IDs divided by all returned citations. It measures retrieval/authorization
  validity, not semantic support for the answer.
- Citation completeness is expected source coverage among those same answerable
  responses, after mapping valid chunk IDs to persisted source dataset IDs.
- Abstention correctness compares the model's sufficient-context flag with the
  golden case's explicit answerability and whether expected evidence was
  retrieved. Unanswerable cases and answerable cases with insufficient retrieved
  evidence are expected abstentions.
- Runtime generation validation requires at least one authorized retrieved
  citation whenever a response claims sufficient context. Legitimate
  insufficient-context abstentions may return no citations; invalid or missing
  citations on a sufficient-context answer trigger the existing bounded
  schema-repair retry.
- Failed generations are excluded from completed-answer citation denominators
  and reported separately by safe failure code. Legitimate abstentions are not
  penalized for having no citations. Empty denominators are reported as `null`
  in JSON and `N/A` in Markdown.

Answer correctness and faithfulness require manual rubric review. The
framework does not rely exclusively on an LLM judge. Unanswerable cases are
expected to produce insufficient-context behavior rather than invented policy
answers.

## Running an evaluation

From `backend`:

```powershell
.\.venv\Scripts\python.exe -m scripts.run_module12_evaluation --mode retrieval
.\.venv\Scripts\python.exe -m scripts.run_module12_evaluation --mode full
```

The runner uses the existing `DocumentService`, `RetrievalService`, and
`GenerationService` with the configured evaluation owner. It only lists
authorized active documents and calls retrieval/generation. It never calls
ingestion, upload, update, archive, delete, or Qdrant write methods.

Results are written to `evaluation/results/module12-latest.json` and
`evaluation/results/module12-latest.md`. Reports include dataset version,
model configuration, retrieval rankings, scores, latency, and citations.

## Security evaluation

The existing retrieval and generation authorization boundaries remain the
security controls. Evaluation must cover unauthorized documents, department
restrictions, archived documents, prompt injection in retrieved text,
unsupported questions, and citations outside the authorized context. The
evaluation runner never broadens access to improve metrics.

## Interpretation

Compare results only across runs with the same dataset version, embedding
model, chat model, retrieval parameters, and authorized evaluation identity.
Answer correctness, faithfulness, and latency thresholds should be reviewed
alongside the deterministic retrieval and citation metrics.
