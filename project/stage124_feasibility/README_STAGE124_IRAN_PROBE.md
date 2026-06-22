# Stage124 Iran listing-source probe

This folder is only for the Stage124 feasibility probe. Outputs are candidate data, not verified listing dates.

## Virtual environment

From repository root:

```bash
python3 -m venv .venv-stage124-iran
source .venv-stage124-iran/bin/activate
python -m pip install --upgrade pip
python -m pip install -r project/stage124_feasibility/requirements_stage124_iran_probe.txt
```

Python 3.11 to 3.13 is preferred.

## Optional proxy

Do not write proxy credentials to Git. If needed, set environment variables only:

```bash
export HTTP_PROXY="http://user:pass@host:port"
export HTTPS_PROXY="http://user:pass@host:port"
```

`.env` is gitignored.

## Run probe

Run only from a network with Iranian egress IP and foreign VPN disabled:

```bash
python project/stage124_feasibility/probe_listing_sources_stage124_v2.py
```

Or from inside `project`:

```bash
python stage124_feasibility/probe_listing_sources_stage124_v2.py
```

The script stops at the 15 pilot tickers and does not run the full 130 tickers.

## Outputs

- `project/stage124_feasibility/feasibility_probe_flat_stage124_iran.csv`
- `project/stage124_feasibility/feasibility_probe_report_stage124_iran.json`
- `project/stage124_feasibility/raw_responses_manifest_stage124_iran.csv`
- `project/stage124_feasibility/raw/tsetmc/`
- `project/stage124_feasibility/raw/codal/`

## `valid_iran_run`

`valid_iran_run=true` only when:

- `egress_country_code = IR`
- at least one of TSETMC or Codal is network-accessible

The full IP is not stored. The report stores masked IP and SHA-256 hash only.

## Scientific restrictions

- Outputs are not verified.
- `verified` is always false.
- Stage124 Part 2 is not executed.
- `listing_master_verified_stage124.csv` is not created.
- Stage123 and frozen Stage124 files must not be modified.
- Eligibility columns are not created or changed.

## Tests

```bash
pytest -q project/tests/test_stage124_feasibility.py
```

## ZIP deliverable

From repository root:

```bash
zip -r stage124_iran_probe_batch01.zip \
  project/stage124_feasibility/probe_listing_sources_stage124_v2.py \
  project/stage124_feasibility/README_STAGE124_IRAN_PROBE.md \
  project/stage124_feasibility/requirements_stage124_iran_probe.txt \
  project/stage124_feasibility/feasibility_probe_flat_stage124_iran.csv \
  project/stage124_feasibility/feasibility_probe_report_stage124_iran.json \
  project/stage124_feasibility/raw_responses_manifest_stage124_iran.csv \
  project/stage124_feasibility/raw \
  project/tests/test_stage124_feasibility.py
```
