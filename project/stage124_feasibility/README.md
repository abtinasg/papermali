# Stage124 — Listing-source feasibility probe (non-authoritative)

Technical feasibility check **only**: can the *initial* listing info for the Stage124
tickers be pulled automatically from **TSETMC** (instrument + daily trade history) and
**Codal** search? This folder is a probe — it does **not** build a verified file, does
**not** touch eligibility, and does **not** overwrite any frozen Stage123/Stage124 artifact.

## Script
`probe_listing_sources_stage124.py` — runs the 15 pilot tickers.

```bash
# from this folder, on a network whose EXIT IP is in Iran:
python probe_listing_sources_stage124.py --label iran --timeout 20
```

The script self-certifies the exit country (`egress` block + `valid_iran_run` in the
report). TSETMC/Codal geo-block non-Iranian IPs, so a non-Iran egress yields
`network_unreachable` for every ticker — this is expected and honest, not a bug.

## Outputs
- `feasibility_probe_flat_stage124_<label>.csv` — one row per ticker, requested columns.
- `feasibility_probe_report_stage124_<label>.json` — full per-source detail + provenance.
- `raw_responses_manifest_stage124_<label>.csv` — one row per HTTP call
  (endpoint, retrieved_at, http_status, raw_sha256, raw_bytes, saved_raw_path, error).
- `raw_responses_stage124_<label>/{tsetmc,codal}/` — raw response bodies (only written
  when a 200 body is actually returned).

## Rules enforced
1. earliest trade date stored **only** as `candidate_first_trade_date` (`verified=false`).
2. rights (حق‌تقدم), funds (صندوق) and other non-ordinary instruments excluded.
3. multiple insCodes → status `ambiguous_instrument`, **no** automatic pick.
4. original + normalized symbol + aliases all preserved.
5. endpoint / retrieved_at / http_status / error / raw SHA-256 (+ raw body) preserved.
6. `network_unreachable` kept separate from `no_instrument_match`.
7. Codal broad: ≤10 candidate notices for {پذیرش، درج، عرضه اولیه، آغاز معاملات،
   گشایش نماد، امیدنامه، عرضه سهام}.
8. no verified file produced, eligibility never changed.

## extraction_status vocabulary
`candidate_found · network_unreachable · no_instrument_match · ambiguous_instrument ·
empty_trade_history · codal_no_candidate_notice · parse_error`

## Run provenance committed on this branch
The committed `*_iran.*` outputs were produced from a **non-Iran egress
(exit_country=DE)** → all 15 = `network_unreachable` (placeholder, schema-valid).
Re-run from an Iranian network to obtain real data; `valid_iran_run` will flip to `true`.

> Pilot-matching notes: requested `جم‌پیلن` (ZWNJ) is `جم پیلن` (space) in the frozen
> dataset; `اپال` has no `company_name` in the dataset. Both are carried explicitly.
