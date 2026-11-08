# Corporate Dataset Inspection Report

## Executive summary

Six local public PDF documents were inspected from
`datasets/corporate/raw/`. All six files were readable and yielded coherent
text with the repository's existing `pypdf` parser and `pdfplumber` table
inspection. The files are public external reference materials from five
different institutions; they are not policies of one company and must remain
separate by source organization.

The collection is suitable for controlled ingestion after provenance review.
No PDF was modified, uploaded, embedded, chunked, or sent to Supabase/Qdrant.

## Files inspected

| ID | Actual file | Organization | Pages | Size | Words | Tables detected | Quality | RAG suitability | Recommendation |
|---|---|---|---:|---:|---:|---:|---|---|---|
| CORP-HR-001 | `employee_handbook_5_2026.pdf` | University of Southern Mississippi | 93 | 1,209,492 | ~36,487 | 1 | Good | High | Keep |
| CORP-HR-002 | `Remoteworkpolicy.pdf` | Yeshiva University | 9 | 220,080 | ~2,646 | 1 | Good | High | Keep |
| CORP-IT-001 | `it-acceptable-use-policy.pdf` | King's College London | 9 | 288,194 | ~2,630 | 7 | Good | High | Keep |
| CORP-IT-002 | `it-aup-byod-procedure.pdf` | King's College London | 6 | 176,792 | ~1,704 | 4 | Good | High | Keep |
| CORP-FIN-001 | `Employee Travel and Expense Policy.pdf` | Suffolk University | 10 | 452,621 | ~4,655 | 8 | Good | High | Keep |
| CORP-FIN-002 | `Travel & Expense Reimbursement Procedures (July 1, 2022) (1).pdf` | Temple University | 17 | 366,336 | ~5,838 | 10 | Good | High | Keep |

Word counts are approximate counts of extracted text tokens. Table counts are
the number of tables detected by `pdfplumber`; they are not a claim that every
table will be perfectly represented by downstream Markdown conversion.

## Per-document inspection

### CORP-HR-001 — University of Southern Mississippi employee handbook

- Actual file: `hr/employee_handbook_5_2026.pdf`
- PDF metadata identifies Microsoft Word for Microsoft 365 and edition text
  states May 2026.
- The opening text identifies University Human Resources and the University
  of Southern Mississippi.
- Structure includes definitions, employment conditions, performance,
  termination, benefits, records, and other staff policies.
- Extraction is text-based and coherent across 93 pages. One table was
  detected.
- Quality: **Good**. RAG suitability: **High**. Recommendation: **Keep**.
  It is long but rich in actionable HR rules; preserve its institution and
  edition metadata to avoid treating it as a generic handbook.

### CORP-HR-002 — Yeshiva University remote work policy

- Actual file: `hr/Remoteworkpolicy.pdf`
- PDF title is `remote work policy 8.12 (00058208).DOCX`; author metadata is
  Julie Auster and creation metadata is August 13, 2021.
- The first page contains `REMOTE WORK POLICY` and the document includes
  `REMOTE WORK ELEMENTS`.
- Extraction is coherent across 9 text-based pages. One table was detected.
- Canonical source URL recorded in the inventory:
  https://www.yu.edu/sites/default/files/inline-files/Remoteworkpolicy.pdf
- Quality: **Good**. RAG suitability: **High**. Recommendation: **Keep**.
  it directly covers remote-work responsibilities and procedures.

### CORP-IT-001 — King's College London acceptable-use policy

- Actual file: `it/it-acceptable-use-policy.pdf`
- The document identifies King's College London, version V10.8, effective
  June 4, 2026, last reviewed May 19, 2026, with next review May 19, 2027.
- Structure includes purpose and scope, definitions, credentials, access,
  remote work, security, equipment, personal use, email, monitoring, and
  reporting.
- Official source URL:
  https://www.kcl.ac.uk/assets/policyzone/informationpolicies/it-acceptable-use-policy.pdf
- Extraction is coherent across 9 text-based pages. Seven tables were
  detected.
- Quality: **Good**. RAG suitability: **High**. Recommendation: **Keep**.
  It has clear user obligations, prohibited actions, security requirements,
  and review metadata.

### CORP-IT-002 — King's College London BYOD procedure

- Actual file: `it/it-aup-byod-procedure.pdf`
- The document identifies King's IT, version 3.0, effective November 1, 2021,
  last reviewed August 28, 2025, and next review August 28, 2026.
- Structure includes purpose and scope, definitions, responsibilities,
  personal-device security, maintenance, data governance, loss/unauthorized
  access, and annual review.
- Official source URL:
  https://www.kcl.ac.uk/assets/policyzone/informationpolicies/it-aup-byod-procedure.pdf
- Extraction is coherent across 6 text-based pages. Four tables were detected.
- Quality: **Good**. RAG suitability: **High**. Recommendation: **Keep**.
  It is concise and actionable; the review date should be refreshed because
  the stated next review is now due or past.

### CORP-FIN-001 — Suffolk University travel and expense policy

- Actual file: `finance/Employee Travel and Expense Policy.pdf`
- PDF metadata names Suffolk University and the first page states latest
  revision date December 1, 2021.
- Canonical source URL is recorded in the inventory, including the source
  query parameters.
- Structure includes purchases, approvers, exceptions, air/car travel,
  lodging, meals, alcohol, business expenses, and reimbursement.
- Extraction is coherent across 10 text-based pages. Eight tables were
  detected.
- Quality: **Good**. RAG suitability: **High**. Recommendation: **Keep**.
  It contains practical approval and reimbursement rules, but it is older
  than the Temple document and must remain source-scoped.

### CORP-FIN-002 — Temple University travel and expense procedures

- Actual file: `finance/Travel & Expense Reimbursement Procedures (July 1, 2022) (1).pdf`
- The first page identifies Temple University, the Office of the President,
  responsible finance officers, and an effective date of July 1, 2022.
- Structure includes booking, airline travel, lodging, meals, receipts,
  personal travel combinations, and approval/reimbursement procedures.
- Extraction is coherent across 17 text-based pages. Ten tables were detected.
  A few pages are short, but no page was empty or unreadable.
- Quality: **Good**. RAG suitability: **High**. Recommendation: **Keep**.
  It is detailed and actionable; retain the July 2022 effective date and
  Temple provenance.

## Quality and extraction assessment

All six files are text-based rather than scan-only PDFs. No document failed
text extraction, showed an obviously duplicated page sequence, or appeared
too short to contain useful policy information. The 93-page handbook is the
largest and may need careful chunk-size and metadata review during ingestion.
Detected tables should be validated after canonical Markdown conversion.

## Overlap and conflicts

- **Temple vs Suffolk:** Both cover travel and expense reimbursement, but their
  approval chains, rates, exceptions, lodging/meal rules, and effective dates
  belong to different universities. They must never be merged or presented as
  one corporate travel policy.
- **Handbook vs remote work:** The USM handbook is broad HR guidance, while
  the Yeshiva document is a focused remote-work policy. Similar employment or
  work-location concepts do not establish a shared rule.
- **Acceptable use vs BYOD:** Both King's College London documents address
  devices, access, security, and remote use. The acceptable-use policy is the
  broader governing policy; the BYOD procedure specializes in unmanaged
  personal devices. Preserve both document types and their version dates.
- **Institutional conflicts:** Different institutions may impose different
  approval limits, device requirements, review cycles, and responsibilities.
  Retrieval and generation must cite the source organization and should
  identify ambiguity rather than combine requirements.

## Language distribution

All six documents are English-language documents based on extracted text and
institutional terminology.

## Recommendations

1. Keep all six as public external reference documents with organization-level
   access in this initial inventory.
2. Preserve all six verified official source URLs when publishing the
   provenance catalog.
3. Refresh or replace the King's BYOD procedure if a newer revision exists.
4. Consider adding a `source_organization` citation prefix to future display
   metadata to prevent cross-institution policy conflation.
5. Validate PDF table Markdown after test ingestion; table detection here is
   an inspection signal, not an ingestion result.
6. Add synthetic internal-company policies separately if the evaluation needs
   one coherent simulated enterprise policy set.

## Final decision

**Ready for controlled ingestion as a public external reference collection,
with provenance review recommended first.** It is not ready to be represented
as a single company's internal policy corpus. No ingestion was performed in
this task.
