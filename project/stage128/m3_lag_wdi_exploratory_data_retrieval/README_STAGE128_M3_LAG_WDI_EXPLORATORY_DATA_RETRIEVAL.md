# Stage128 — Track B: M3-LAG-WDI exploratory DATA RETRIEVAL

**Action:** `stage128-m3-lag-wdi-exploratory-data-retrieval`
**Authorized scope:** `retrieval_only`
**Baseline:** `main` @ `175e7949e009eeecdd66aedab31ec4b48e9d3c7d` (the merge commit of
PR #78, the contract lock)

## What this action is

Acquisition of the raw official World Bank WDI source payloads for the **two
indicators frozen by the merged contract**, for **IRN**, and nothing else.

**Acquiring bytes is not admitting data.** This action answers no question
about coverage, about the Data Gate, about admission or about modeling.

| Indicator | Country | Result | HTTP | Bytes | SHA-256 |
| --- | --- | --- | --- | --- | --- |
| `FP.CPI.TOTL.ZG` | IRN | SUCCESS | 200 | 15805 | `f62292c52088df71…` |
| `PA.NUS.FCRF` | IRN | SUCCESS | 200 | 16482 | `74b585734cc48dd2…` |

Raw payloads are retained **outside the repository**; only their byte counts
and SHA-256 digests are committed
(`raw_payloads_committed_to_git: 0`).

## Where this action stopped

The payload was **never decoded or parsed**
(`payload_json_decoded: False`,
`wdi_observations_read: 0`). Reading what is
*inside* the retained bytes is the separately authorized post-retrieval audit.

All zero: value inspections, coverage calculations, candidate/block coverage
evaluations, Data Gate executions, admission decisions, company-row joins,
feature materializations, FX transformation calculations, common-sample
constructions, model fits, predictions, predictive metrics, bootstrap
executions, Holm calculations, SHAP executions, tuning runs, **Final Test rows
read**.

## The authorization boundary

The retrieval authorization (125 UTF-8 bytes, SHA-256
`b409e0a53d255955…`) is
**single-use and is now consumed**. It does not reach:

| Step | Action | Authorized |
| --- | --- | --- |
| C | `stage128-m3-lag-wdi-exploratory-post-retrieval-audit` | **false** |
| D | `stage128-m3-lag-wdi-exploratory-data-gate` | **false** — needs a NEW explicit human authorization |
| E | `stage128-m3-lag-wdi-exploratory-incremental-evaluation` | **false** — only after a Gate PASS, and needs ANOTHER authorization |

A retrieval authorization does **not** authorize the Data Gate. A Data Gate
PASS would be **data admission only** and would **not** authorize modeling. A
pointer is never an authorization.

## Track A is untouched

The World Bank official inquiry remains a parallel ACTIVE track: still
`SUBMITTED_ACKNOWLEDGED_WAITING_FOR_SUBSTANTIVE_RESPONSE`, follow-up and
response adjudication both unauthorized. Retrieving Track B data does not
resolve, close or abandon Track A.

## Reproducing

```
python3 project/run_stage128_m3_lag_wdi_exploratory_data_retrieval.py --check
```

`--check` is offline and read-only. `--build-from-bundle DIR` rebuilds every
artifact here from the retained raw bytes. `--retrieve` is the one authorized
network path and is already spent.
