# Stage125 Part 1 — Data Dictionary & Provenance Contract

This directory contains the Stage125 **Part 1** deliverables. Part 1 is a
documentation / contract / read-only-audit step. It performs **no** modeling,
**no** data extraction, **no** network access, and does **not** change the
frozen target, sample, eligibility, cutoff, or any Stage122–Stage124 asset.

## Deliverables

- `data_dictionary_stage125.csv` — data dictionary for blocks M1–M4.
- `identifier_time_contract_stage125.json` — identifier and observation/publication/availability/retrieval time contract.
- `source_registry_stage125.csv` — source registry (M1–M4 only; no M5).
- `provenance_manifest_schema_stage125.json` — provenance manifest record schema.
- `data_admission_gate_template_stage125.csv` — data admission gate template.
- `m1_provenance_gap_audit_stage125.csv` — per-row M1 provenance flags (identifiers + flags only).
- `m1_provenance_gap_summary_stage125.json` — M1 provenance gap summary.
- `stage125_part1_data_contract_qc_report.json` — QC report.
- `metadata_and_hashes_stage125_part1.json` — hashes/metadata manifest.

## M1 provenance gap counts (read-only)

- rows: 1331 (unique row_key: 1331)
- source_file present/missing: 1303/28
- source_url present/missing: 15/1316
- fiscal_year_end present/missing: 1327/4
- company_name present/missing: 1324/7
- industry present/missing: 1302/29
- audit_status_unknown: 316

Input: `modeling_all_rows_stage123.csv` (source: canonical_input_csv)

Input SHA-256: `28b9f9d4185617182c0fe06299deeb0e9a092558b8849f1dfdef7072261bc390`

## Guardrails

- Empty `source_url` (1316 rows) is a provenance gap only; it never changes
  eligibility or drops a row in Part 1.
- `row_key` stays immutable and unique across 1331 rows.
- `predictor_row_key_t` and `target_row_key_t_plus_1` are not redefined.
- M5 (Persian text modeling) is not part of the registry or dictionary.
- Modeling remains prohibited; `modeling_started=false`.
- Part 2 has not started.
