# Stage124 Pilot15 User-Confirmed Public-Entry Dates

This stage covers only the 15 project-owner-confirmed tickers listed in `listing_pilot15_user_confirmed_stage124.csv`.

The TSETMC oldest `dEven` dates are retained as candidate audit evidence only. They are not canonical public-entry dates and are not used for listing eligibility.

The remaining 115 tickers in `listing_master_partial_verified_stage124.csv` remain `pending` and unchanged from `listing_master_template_stage124.csv`.

Full Stage124 Part 2 has not been run. `listing_master_verified_stage124.csv` must not exist after this pilot.

No Stage122 or Stage123 financial file, target column, financial value, statement scope, or modeling panel is modified by this pilot.

The eligibility output is an impact audit for the 15 pilot tickers only. It is not a canonical modeling panel.

Run:

```bash
python run_stage124_pilot15.py
python -m pytest tests/test_stage124.py tests/test_stage124_feasibility.py tests/test_stage124_pilot15.py -q | tee stage124/stage124_pilot15_unit_test_output.txt
```

QC writes `stage124_pilot15_qc_report.json`. Success metadata is written only when all QC assertions pass.
