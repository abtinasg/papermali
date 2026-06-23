# Stage124 Pilot15 Change Log

## 2026-06-23

- Added immutable user-confirmed public-entry date input for 15 tickers.
- Added independent Stage124 Pilot15 runner and implementation.
- Added partial listing master generation that verifies only the 15 pilot tickers.
- Added TSETMC conflict audit retaining candidate dates outside canonical eligibility use.
- Added eligibility impact audit and ticker-level summary for the pilot rows only.
- Added QC report and success metadata generation gated on full QC pass.
- Added tests for input integrity, partial master invariants, TSETMC conflict handling, eligibility impact, file immutability, and provenance hashes.
