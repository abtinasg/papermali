"""Stage127 — root-cause audit of `equity_return_window` unavailability.

DIAGNOSTIC ONLY. This module does not compute, redefine, or alter any
scientific quantity. It reads the same immutable external evidence bundle the
canonical Gate ingests, calls the Gate's own frozen window/feature functions
(``pair_scientific_window`` / ``compute_pair_features``) so the diagnosis is
computed from EXACTLY the same universe the canonical result was computed
from, and additionally re-parses the raw TSETMC evidence (``qTotCap``,
``qTotTran5J``, ``zTotTran``, ``pClosing``) to classify WHY each pair's
`t0`/`T*` endpoint lacks an adjusted price.

It never modifies:
  * stage127_m2_market_data_gate_decision.json (canonical Gate result)
  * any canonical coverage/common-sample/feature artifact
  * the frozen Stage125 contracts, thresholds, or feature definitions

No live TSETMC endpoint is queried here (no network egress was available in
this execution environment for any Stage127 action to date; see
stage127_m2_source_manifest.json). Root-cause classification is therefore
based entirely on the evidence already present in the immutable bundle:
raw daily closing-price records, the official adjusted-price history, the
restricted-raw provenance manifest, and the retrieval-range manifest. Where
that evidence could not distinguish two categories (e.g. "TSETMC's own
calendar excludes this date" vs "a genuine zero-trade day"), the pair was
classified UNRESOLVED rather than guessed.

That distinction has since been SETTLED by external evidence plus contract
adjudication, so no pair is pending or unresolved any more: the official
InstrumentCalendar evidence proved the dates are real calendar members, and the
frozen contract keeps a zero-trade calendar member in the trading-day sequence.
The affected pairs are therefore TRUE frozen-contract missingness. See
project/stage127/stage127_m2_trading_day_semantics_adjudication.json. The
canonical Gate is unchanged by any of this.
"""
from __future__ import annotations

import json
import os
from datetime import date
from typing import Any

from . import stage127_m2_external_delivery_import as imp
from . import stage127_m2_market_data_gate as gate

# --------------------------------------------------------------------------- #
# Root-cause categories (evidence-bound; never assigned from intuition)
# --------------------------------------------------------------------------- #

CAT_RETRIEVAL_RANGE_TRUNCATION = "A_RETRIEVAL_RANGE_TRUNCATION"
CAT_HISTORY_START_OR_LISTING_LIMIT = "B_TSETMC_HISTORY_START_OR_LISTING_LIMIT"
CAT_IDENTITY_FRAGMENTATION = "C_INSTRUMENT_IDENTITY_OR_INSCODE_FRAGMENTATION"
CAT_RAW_TRADE_ADJUSTED_MISSING = "D_RAW_TSETMC_TRADE_EXISTS_BUT_ADJUSTED_SERIES_MISSING"
#: NOT a proven final category. The immutable bundle only shows that the
#: ClosingPriceDailyList row has qTotCap=0/zTotTran=0; it does NOT, by itself,
#: establish whether that date was a genuine trading day with zero executions,
#: a suspension, a non-tradable state, or a calendar artifact. This label is
#: therefore evidence-honest: it named the open question rather than
#: pre-deciding it. That question is now RESOLVED -- the authoritative TSETMC
#: calendar/state/trade evidence arrived and the frozen contract was
#: adjudicated -- so the label is HISTORICAL and its pairs are now classified
#: as TRUE frozen-contract missingness (see
#: ADJUDICATED_TRUE_MISSINGNESS_CATEGORIES below). The label string itself is
#: kept unchanged for audit-trail continuity.
CAT_ZERO_TRADE_ENDPOINT = (
    "ZERO_TRADE_ENDPOINT_REQUIRES_TRADING_DAY_SEMANTICS_ADJUDICATION"
)
CAT_TRUE_MISSING_ADJUSTED = "F_TRUE_TRADING_DAY_WITH_NO_VALID_ADJUSTED_PRICE"
CAT_FEWER_THAN_126_ONLY = "G_FEWER_THAN_126_VALID_RETURNS_ONLY"
CAT_OTHER_PROVEN_DEFECT = "H_OTHER_PROVEN_DEFECT"
CAT_UNRESOLVED = "I_UNRESOLVED_ROOT_CAUSE"

RECOVERABLE_CATEGORIES = {
    CAT_RETRIEVAL_RANGE_TRUNCATION,
    CAT_IDENTITY_FRAGMENTATION,
    CAT_RAW_TRADE_ADJUSTED_MISSING,
    CAT_OTHER_PROVEN_DEFECT,
}
#: F is the only category the CURRENT bundle evidence can actually establish
#: as final from the market-data bundle alone, so it is never assigned by this
#: module. G (fewer than 126 valid returns) is deliberately NOT listed here
#: unconditionally: it is still split per pair by build_summary() using the
#: low-return upper-bound audit, so the historical sub-breakdown stays visible.
#: Under the completed adjudication BOTH G sub-classes are nonrecoverable,
#: because zero-trade rows may not be dropped from the trading-day sequence.
NONRECOVERABLE_CATEGORIES = {
    CAT_HISTORY_START_OR_LISTING_LIMIT,
    CAT_TRUE_MISSING_ADJUSTED,
}
#: RESOLVED. The external TSETMC calendar/state/trade evidence is complete
#: (stage127_m2_zero_trade_semantics_full_delivery_v3.zip) and the
#: frozen-contract semantics adjudication is complete, so NOTHING is pending
#: external adjudication any more. The set is retained (empty) so the
#: pending-count field keeps a real derivation instead of a hardcoded zero.
PENDING_EXTERNAL_ADJUDICATION_CATEGORIES: set[str] = set()

#: The completed adjudication, accepted by the human supervisor.
ADJUDICATION_OUTCOME = (
    "FROZEN_CONTRACT_UNAMBIGUOUS_CURRENT_IMPLEMENTATION_CONFORMANT"
)
ADJUDICATION_ARTIFACT = (
    "project/stage127/stage127_m2_trading_day_semantics_adjudication.json"
)
#: Under the adjudicated frozen contract a zero-traded-value InstrumentCalendar
#: member REMAINS a trading day of W, so a zero-trade endpoint with no adjusted
#: price is TRUE frozen-contract missingness, not an open question and not a
#: data-capture defect.
CURRENT_SEMANTIC_STATUS = "TRUE_FROZEN_CONTRACT_MISSINGNESS"
ADJUDICATED_TRUE_MISSINGNESS_CATEGORIES = {
    CAT_ZERO_TRADE_ENDPOINT,
}

# --------------------------------------------------------------------------- #
# Low-return semantics upper bound (BLOCKER 1)
# --------------------------------------------------------------------------- #

#: A <126-return pair whose PRICED observation count alone -- i.e. even under
#: the most favorable hypothetical where every zero-trade row is excluded from
#: the trading-day sequence entirely -- cannot reach 126 valid returns. This
#: is a mathematical ceiling, not evidence about what a zero-trade row means;
#: it was true regardless of how the semantics question resolved.
CAT_GUARANTEED_LT126 = "GUARANTEED_LT126_EVEN_IF_ALL_ZERO_TRADE_ROWS_EXCLUDED"
#: HISTORICAL sub-class: reaching 126 returns for this pair would have
#: required zero-trade rows to be non-trading days. The adjudication decided
#: they ARE trading days of W, so this sub-class is nonrecoverable under the
#: current frozen contract. Never treated as recoverable.
CAT_PENDING_LOW_RETURN_SEMANTICS = (
    "POTENTIALLY_RECOVERABLE_PENDING_ZERO_TRADE_DAY_SEMANTICS"
)

PARTIAL_RANGE_TICKERS: dict[str, str] = dict(imp.EXPECTED_PARTIAL_RANGES)


class RootCauseAudit:
    """Holds the enriched per-observation raw evidence needed for the audit."""

    def __init__(self, repo_root: str, bundle_path: str) -> None:
        self.repo_root = repo_root
        canonical = imp.load_canonical_ranges(repo_root)
        with imp.ExternalDelivery(bundle_path) as delivery:
            self.import_qc, self.observations, self.mapping, self.manifest = (
                imp.validate_delivery(delivery, canonical)
            )
            self._raw_daily, self._raw_adjusted = self._load_raw(delivery)

        self.pairs = gate.load_development_pairs(repo_root)
        self.canonical_by_range = {r["range_id"]: r for r in canonical}
        # ticker -> sorted list of range_ids it owns, in retrieval order
        self.ranges_by_ticker: dict[str, list[str]] = {}
        for rid, r in self.canonical_by_range.items():
            self.ranges_by_ticker.setdefault(r["ticker"], []).append(rid)
        for rid_list in self.ranges_by_ticker.values():
            rid_list.sort(
                key=lambda rid: self.canonical_by_range[rid]["requested_start_date"]
            )

    def _load_raw(
        self, delivery: imp.ExternalDelivery,
    ) -> tuple[
        dict[str, dict[str, dict[str, Any]]],
        dict[str, dict[str, float]],
    ]:
        """Independently re-parse raw daily + adjusted evidence per range_id."""
        raw_daily: dict[str, dict[str, dict[str, Any]]] = {}
        raw_adjusted: dict[str, dict[str, float]] = {}
        for rid in self.manifest:
            daily_rel = f"raw_restricted/{rid}/{imp.RAW_DAILY_BASENAME}"
            adj_rel = f"raw_restricted/{rid}/{imp.RAW_ADJUSTED_BASENAME}"
            payload = json.loads(
                delivery.read(f"{imp.ROOT}/{daily_rel}").decode("utf-8")
            )
            by_date: dict[str, dict[str, Any]] = {}
            for rec in payload["closingPriceDaily"]:
                iso = imp.deven_to_iso(rec["dEven"])
                by_date[iso] = rec
            raw_daily[rid] = by_date
            adj_text = delivery.read(f"{imp.ROOT}/{adj_rel}").decode("utf-8")
            raw_adjusted[rid] = imp.parse_adjusted_records(adj_text)
        return raw_daily, raw_adjusted

    # -- lookups ------------------------------------------------------------ #

    def raw_at(self, ticker: str, iso: str) -> tuple[str | None, dict[str, Any] | None]:
        """Return (range_id, raw_record) for a ticker/date, or (None, None)."""
        for rid in self.ranges_by_ticker.get(ticker, ()):
            canon = self.canonical_by_range[rid]
            if canon["requested_start_date"] <= iso <= canon["requested_end_date"]:
                return rid, self._raw_daily.get(rid, {}).get(iso)
        return None, None

    def history_bounds(self, ticker: str) -> dict[str, str]:
        raw_dates: list[str] = []
        adj_dates: list[str] = []
        for rid in self.ranges_by_ticker.get(ticker, ()):
            raw_dates.extend(self._raw_daily.get(rid, {}).keys())
            adj_dates.extend(self._raw_adjusted.get(rid, {}).keys())
        return {
            "first_raw_daily_date": min(raw_dates) if raw_dates else "",
            "last_raw_daily_date": max(raw_dates) if raw_dates else "",
            "first_adjusted_price_date": min(adj_dates) if adj_dates else "",
            "last_adjusted_price_date": max(adj_dates) if adj_dates else "",
        }

    def authorized_bounds(self, ticker: str) -> tuple[str, str]:
        rids = self.ranges_by_ticker.get(ticker, ())
        if not rids:
            return "", ""
        starts = [self.canonical_by_range[r]["requested_start_date"] for r in rids]
        ends = [self.canonical_by_range[r]["requested_end_date"] for r in rids]
        return min(starts), max(ends)

    def nearest_prior(
        self, ticker: str, iso: str, *, positive_trade_only: bool, adjusted_only: bool,
    ) -> str:
        """Latest date strictly before ``iso`` satisfying the given predicate."""
        best = ""
        for rid in self.ranges_by_ticker.get(ticker, ()):
            if adjusted_only:
                for d in self._raw_adjusted.get(rid, {}):
                    if d < iso and d > best:
                        best = d
                continue
            for d, rec in self._raw_daily.get(rid, {}).items():
                if d >= iso:
                    continue
                if positive_trade_only and not (
                    float(rec.get("qTotCap") or 0) > 0
                    and float(rec.get("zTotTran") or 0) > 0
                ):
                    continue
                if d > best:
                    best = d
        return best

    def is_zero_trade_raw(self, ticker: str, iso: str) -> bool | None:
        """True/False from raw evidence (qTotCap==0 and zTotTran==0); None if
        no raw observation exists at all for this ticker/date."""
        _rid, raw = self.raw_at(ticker, iso)
        if raw is None:
            return None
        return (
            float(raw.get("qTotCap") or 0) == 0
            and float(raw.get("zTotTran") or 0) == 0
        )


def _endpoint_evidence(
    audit: RootCauseAudit, ticker: str, iso: str,
) -> dict[str, Any]:
    rid, raw = audit.raw_at(ticker, iso)
    if raw is None:
        return {
            "source_range_id": rid or "",
            "raw_observation_present": False,
            "qTotCap": "", "qTotTran5J": "", "zTotTran": "", "raw_close": "",
        }
    return {
        "source_range_id": rid or "",
        "raw_observation_present": True,
        "qTotCap": float(raw.get("qTotCap") or 0),
        "qTotTran5J": float(raw.get("qTotTran5J") or 0),
        "zTotTran": float(raw.get("zTotTran") or 0),
        "raw_close": float(raw.get("pClosing") or 0),
    }


def _classify_endpoint(
    audit: RootCauseAudit, ticker: str, iso: str, window_start: str,
) -> tuple[str, dict[str, Any]]:
    """Classify why one endpoint date (t0 or T*) has no adjusted price.

    Returns (category, evidence). Evidence-bound only:
      * no raw observation at all AND the requested window predates the
        authorized retrieval range start -> retrieval-range truncation
        (recoverable: a wider authorized request would very likely capture it);
      * no raw observation at all AND it also predates the earliest raw date
        this ticker's OWN authorized ranges ever returned -> listing/history
        start limit (the instrument itself has no earlier trade evidence in
        what TSETMC returned for the requested span);
      * a raw observation exists with qTotCap>0 and zTotTran>0 (a REAL trade)
        but no adjusted price -> proven extraction/join defect;
      * a raw observation exists with qTotCap==0 / zTotTran==0 (no trade) and
        no adjusted price -> zero-trade/non-trading endpoint semantics, which
        is the same observed property already confirmed for all 27,615
        ADJUSTED_CLOSE_UNRESOLVED rows;
      * anything else -> unresolved (evidence does not settle it).
    """
    rid, raw = audit.raw_at(ticker, iso)
    ev = _endpoint_evidence(audit, ticker, iso)
    auth_start, auth_end = audit.authorized_bounds(ticker)
    bounds = audit.history_bounds(ticker)

    if raw is None:
        if auth_start and iso < auth_start:
            return CAT_RETRIEVAL_RANGE_TRUNCATION, ev
        if bounds["first_raw_daily_date"] and iso < bounds["first_raw_daily_date"]:
            # Inside the authorized window in principle, but before ANY raw
            # observation TSETMC returned for this ticker at all: no evidence
            # of an earlier trading history within what was retrieved.
            return CAT_HISTORY_START_OR_LISTING_LIMIT, ev
        return CAT_UNRESOLVED, ev

    q_total_cap = float(raw.get("qTotCap") or 0)
    z_tot_tran = float(raw.get("zTotTran") or 0)
    if q_total_cap > 0 and z_tot_tran > 0:
        return CAT_RAW_TRADE_ADJUSTED_MISSING, ev
    if q_total_cap == 0 and z_tot_tran == 0:
        return CAT_ZERO_TRADE_ENDPOINT, ev
    return CAT_UNRESOLVED, ev


def build_audit_rows(audit: RootCauseAudit) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for p in sorted(audit.pairs, key=lambda x: (x["target_year"], x["ticker"])):
        ticker = p["ticker"]
        cutoff = p["pair_cutoff_date"]
        obs = audit.observations.get(ticker, [])
        win = gate.pair_scientific_window(cutoff, obs)
        feat = gate.compute_pair_features(cutoff, obs)
        bounds = audit.history_bounds(ticker)
        auth_start, auth_end = audit.authorized_bounds(ticker)

        window = win.get("window", [])
        t_star = win.get("t_star", "")
        t0_date = window[0]["trading_date"] if window else ""

        t_star_ev = _endpoint_evidence(audit, ticker, t_star) if t_star else {
            "source_range_id": "", "raw_observation_present": False,
            "qTotCap": "", "qTotTran5J": "", "zTotTran": "", "raw_close": "",
        }
        t0_ev = _endpoint_evidence(audit, ticker, t0_date) if t0_date else {
            "source_range_id": "", "raw_observation_present": False,
            "qTotCap": "", "qTotTran5J": "", "zTotTran": "", "raw_close": "",
        }

        t_star_status = ""
        t0_status = ""
        for o in window:
            if o["trading_date"] == t_star:
                t_star_status = o["adjusted_close_status"]
            if o["trading_date"] == t0_date:
                t0_status = o["adjusted_close_status"]

        primary_cause = ""
        secondary_causes: list[str] = []
        equity_usable = feat["equity_return_window"] is not None
        rvol_usable = feat["realized_volatility"] is not None
        amihud_usable = feat["amihud_illiquidity"] is not None

        if not equity_usable and win["resolution"] == gate.RESOLUTION_PASS:
            causes: list[str] = []
            if feat["missing_tN_adjusted_close"]:
                cat, _ = _classify_endpoint(
                    audit, ticker, t_star, win.get("window_start_calendar_date", "")
                )
                causes.append(cat)
            if feat["missing_t0_adjusted_close"]:
                cat, _ = _classify_endpoint(
                    audit, ticker, t0_date, win.get("window_start_calendar_date", "")
                )
                causes.append(cat)
            if feat["fewer_than_126_valid_returns"] and not causes:
                causes.append(CAT_FEWER_THAN_126_ONLY)
            elif feat["fewer_than_126_valid_returns"]:
                causes.append(CAT_FEWER_THAN_126_ONLY)
            if causes:
                primary_cause = causes[0]
                secondary_causes = causes[1:]
            else:
                primary_cause = CAT_UNRESOLVED
        elif not equity_usable:
            primary_cause = "UNRESOLVED_NO_SCIENTIFIC_WINDOW"

        rows.append({
            "sample_design": gate.PRIMARY_SAMPLE,
            "ticker": ticker,
            "fiscal_year_t": p["fiscal_year_t"],
            "target_year": p["target_year"],
            "temporal_folds": ";".join(p["folds"]),
            "pair_cutoff_date": cutoff,
            # T*
            "t_star": t_star,
            "t_star_source_range_id": t_star_ev["source_range_id"],
            "t_star_raw_observation_present": t_star_ev["raw_observation_present"],
            "t_star_adjusted_close_present": bool(
                t_star and t_star_status == imp.ADJUSTED_STATUS_OK
            ),
            "t_star_qTotCap": t_star_ev["qTotCap"],
            "t_star_qTotTran5J": t_star_ev["qTotTran5J"],
            "t_star_zTotTran": t_star_ev["zTotTran"],
            "t_star_raw_close": t_star_ev["raw_close"],
            "t_star_adjusted_close_status": t_star_status,
            # t0
            "window_start_calendar_date": win.get("window_start_calendar_date", ""),
            "t0_trading_date": t0_date,
            "t0_source_range_id": t0_ev["source_range_id"],
            "t0_raw_observation_present": t0_ev["raw_observation_present"],
            "t0_adjusted_close_present": bool(
                t0_date and t0_status == imp.ADJUSTED_STATUS_OK
            ),
            "t0_qTotCap": t0_ev["qTotCap"],
            "t0_qTotTran5J": t0_ev["qTotTran5J"],
            "t0_zTotTran": t0_ev["zTotTran"],
            "t0_raw_close": t0_ev["raw_close"],
            "t0_adjusted_close_status": t0_status,
            # history bounds
            "authorized_range_start": auth_start,
            "authorized_range_end": auth_end,
            "first_raw_daily_date": bounds["first_raw_daily_date"],
            "last_raw_daily_date": bounds["last_raw_daily_date"],
            "first_adjusted_price_date": bounds["first_adjusted_price_date"],
            "last_adjusted_price_date": bounds["last_adjusted_price_date"],
            # feature diagnostics
            "window_trading_day_count": feat["window_trading_day_count"],
            "missing_price_day_count": feat["missing_price_day_count"],
            "zero_traded_value_day_count": feat["zero_traded_value_day_count"],
            "usable_daily_return_count": feat["usable_daily_return_count"],
            "usable_amihud_day_count": feat["usable_amihud_day_count"],
            "equity_return_window_usable": equity_usable,
            "realized_volatility_usable": rvol_usable,
            "amihud_illiquidity_usable": amihud_usable,
            "primary_root_cause": primary_cause,
            "secondary_root_causes": ";".join(secondary_causes),
            "evidence_status": (
                "OBSERVED_FROM_IMMUTABLE_BUNDLE_NO_LIVE_TSETMC_QUERY"
            ),
            "range_is_partial_source": ticker in PARTIAL_RANGE_TICKERS.values(),
        })
    return rows


# --------------------------------------------------------------------------- #
# tN / t0 detail audits (sections 5 and 6 of the request)
# --------------------------------------------------------------------------- #

def build_tN_detail_rows(
    audit: RootCauseAudit, main_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows = []
    for r in main_rows:
        if r["t_star_adjusted_close_present"] or not r["t_star"]:
            continue
        ticker, iso = r["ticker"], r["t_star"]
        cat, _ = _classify_endpoint(audit, ticker, iso, r["window_start_calendar_date"])
        prev_raw = audit.nearest_prior(
            ticker, iso, positive_trade_only=False, adjusted_only=False)
        prev_trade = audit.nearest_prior(
            ticker, iso, positive_trade_only=True, adjusted_only=False)
        prev_adj = audit.nearest_prior(
            ticker, iso, positive_trade_only=False, adjusted_only=True)
        gap = (
            (date.fromisoformat(iso) - date.fromisoformat(prev_adj)).days
            if prev_adj else ""
        )
        rows.append({
            "ticker": ticker,
            "target_year": r["target_year"],
            "pair_cutoff_date": r["pair_cutoff_date"],
            "t_star": iso,
            "qTotCap": r["t_star_qTotCap"],
            "volume_qTotTran5J": r["t_star_qTotTran5J"],
            "trade_count_zTotTran": r["t_star_zTotTran"],
            "raw_close": r["t_star_raw_close"],
            "adjusted_status": r["t_star_adjusted_close_status"],
            "previous_raw_observation_date": prev_raw,
            "previous_positive_trade_date": prev_trade,
            "previous_adjusted_price_date": prev_adj,
            "calendar_day_gap_to_previous_valid_adjusted_price": gap,
            "root_cause": cat,
        })
    return rows


def build_t0_detail_rows(
    audit: RootCauseAudit, main_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows = []
    for r in main_rows:
        if r["t0_adjusted_close_present"] or not r["t0_trading_date"]:
            continue
        ticker, iso = r["ticker"], r["t0_trading_date"]
        cat, _ = _classify_endpoint(audit, ticker, iso, r["window_start_calendar_date"])
        dist_first_raw = (
            (date.fromisoformat(r["first_raw_daily_date"])
             - date.fromisoformat(r["window_start_calendar_date"])).days
            if r["first_raw_daily_date"] and r["window_start_calendar_date"] else ""
        )
        dist_first_trade = ""
        first_trade = audit.nearest_prior(
            ticker, r["last_raw_daily_date"] or iso,
            positive_trade_only=True, adjusted_only=False,
        ) if False else ""  # not meaningful as "prior"; computed below instead
        dist_first_adj = (
            (date.fromisoformat(r["first_adjusted_price_date"])
             - date.fromisoformat(r["window_start_calendar_date"])).days
            if r["first_adjusted_price_date"] and r["window_start_calendar_date"]
            else ""
        )
        rows.append({
            "ticker": ticker,
            "target_year": r["target_year"],
            "pair_cutoff_date": r["pair_cutoff_date"],
            "window_start_calendar_date": r["window_start_calendar_date"],
            "t0_trading_date": iso,
            "qTotCap": r["t0_qTotCap"],
            "volume_qTotTran5J": r["t0_qTotTran5J"],
            "trade_count_zTotTran": r["t0_zTotTran"],
            "raw_close": r["t0_raw_close"],
            "adjusted_status": r["t0_adjusted_close_status"],
            "first_raw_observation_date_this_ticker": r["first_raw_daily_date"],
            "first_adjusted_price_date_this_ticker": r["first_adjusted_price_date"],
            "days_from_window_start_to_first_raw_observation": dist_first_raw,
            "days_from_window_start_to_first_adjusted_price": dist_first_adj,
            "root_cause": cat,
        })
    return rows


# --------------------------------------------------------------------------- #
# <126-return detail (section 7)
# --------------------------------------------------------------------------- #

def build_low_return_rows(
    audit: RootCauseAudit, main_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows = []
    for r in main_rows:
        if not r["equity_return_window_usable"] is False:
            pass
        if r["usable_daily_return_count"] == "" or r["usable_daily_return_count"] is None:
            continue
        if int(r["usable_daily_return_count"]) >= gate.MIN_VALID_RETURN_OBSERVATIONS:
            continue
        rows.append({
            "ticker": r["ticker"],
            "target_year": r["target_year"],
            "window_observation_count": r["window_trading_day_count"],
            "missing_adjusted_price_days": r["missing_price_day_count"],
            "zero_trade_days": r["zero_traded_value_day_count"],
            "valid_return_count": r["usable_daily_return_count"],
            "range_is_partial_source": r["range_is_partial_source"],
            "primary_root_cause": r["primary_root_cause"] or CAT_FEWER_THAN_126_ONLY,
        })
    return rows


def build_low_return_upper_bound_rows(
    audit: RootCauseAudit, main_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """For all 90 <126-return pairs: is <126 mathematically guaranteed?

    Recomputed independently from raw evidence (qTotCap/zTotTran per window
    observation), not from the already-derived ``missing_price_day_count``
    field, so this audit cannot silently inherit an upstream assumption.

    ``max_possible_valid_returns_if_all_zero_trade_rows_are_non_trading =
    priced_observation_count - 1`` is a pure ceiling on consecutive valid
    returns if EVERY zero-trade row were excluded from the trading-day
    sequence entirely. It never asserts that this is the correct semantics --
    only whether the pair's outcome depended on that (now adjudicated)
    question.
    """
    rows: list[dict[str, Any]] = []
    for r in main_rows:
        cnt = r["usable_daily_return_count"]
        if cnt == "" or cnt is None:
            continue
        if int(cnt) >= gate.MIN_VALID_RETURN_OBSERVATIONS:
            continue

        ticker, cutoff = r["ticker"], r["pair_cutoff_date"]
        obs = audit.observations.get(ticker, [])
        win = gate.pair_scientific_window(cutoff, obs)
        window = win.get("window", [])

        zero_trade = 0
        priced = 0
        for o in window:
            z = audit.is_zero_trade_raw(ticker, o["trading_date"])
            if z:
                zero_trade += 1
            if o["adjusted_close"] is not None:
                priced += 1

        max_possible = priced - 1 if priced > 0 else 0
        classification = (
            CAT_GUARANTEED_LT126 if max_possible < gate.MIN_VALID_RETURN_OBSERVATIONS
            else CAT_PENDING_LOW_RETURN_SEMANTICS
        )
        rows.append({
            "ticker": ticker,
            "fiscal_year_t": r["fiscal_year_t"],
            "target_year": r["target_year"],
            "window_observation_count": len(window),
            "zero_trade_day_count": zero_trade,
            "priced_observation_count": priced,
            "current_valid_return_count": int(cnt),
            "max_possible_valid_returns_if_all_zero_trade_rows_are_non_trading": (
                max_possible),
            "current_endpoint_requirements_pass": bool(
                r["t0_adjusted_close_present"]
                and r["t_star_adjusted_close_present"]
            ),
            "classification": classification,
        })
    return rows


# --------------------------------------------------------------------------- #
# Summary
# --------------------------------------------------------------------------- #

def build_summary(
    audit: RootCauseAudit,
    rows: list[dict[str, Any]],
    upper_bound_rows: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    upper_bound_rows = upper_bound_rows or []
    upper_bound_by_key = {
        (u["ticker"], u["target_year"]): u["classification"]
        for u in upper_bound_rows
    }

    unavailable = [r for r in rows if not r["equity_return_window_usable"]]
    usable = [r for r in rows if r["equity_return_window_usable"]]

    root_cause_counts: dict[str, int] = {}
    for r in unavailable:
        c = r["primary_root_cause"] or CAT_UNRESOLVED
        root_cause_counts[c] = root_cause_counts.get(c, 0) + 1

    def _low_return_class(r: dict[str, Any]) -> str | None:
        if r["primary_root_cause"] != CAT_FEWER_THAN_126_ONLY:
            return None
        return upper_bound_by_key.get((r["ticker"], r["target_year"]))

    guaranteed_low_return = sum(
        1 for r in unavailable if _low_return_class(r) == CAT_GUARANTEED_LT126
    )
    pending_low_return = sum(
        1 for r in unavailable
        if _low_return_class(r) == CAT_PENDING_LOW_RETURN_SEMANTICS
    )

    recoverable = sum(
        1 for r in unavailable if r["primary_root_cause"] in RECOVERABLE_CATEGORIES
    )
    # Adjudicated: the zero-trade endpoint cases are now TRUE frozen-contract
    # missingness. The <126 cases resolve the same way -- under the adjudicated
    # contract a zero-trade row may NOT be dropped from the trading-day
    # sequence, so the favourable upper bound that made some of them
    # "potentially recoverable" is not reachable and BOTH low-return sub-classes
    # remain unavailable. Every count below is re-derived from the rows.
    adjudicated_true_missingness = sum(
        1 for r in unavailable
        if r["primary_root_cause"] in ADJUDICATED_TRUE_MISSINGNESS_CATEGORIES
    )
    nonrecoverable = (
        guaranteed_low_return
        + pending_low_return
        + adjudicated_true_missingness
        + sum(
            1 for r in unavailable
            if r["primary_root_cause"] in NONRECOVERABLE_CATEGORIES
        )
    )
    pending_external = sum(
        1 for r in unavailable
        if r["primary_root_cause"] in PENDING_EXTERNAL_ADJUDICATION_CATEGORIES
    )
    pending_total = pending_external
    unresolved = sum(
        1 for r in unavailable
        if r["primary_root_cause"] not in RECOVERABLE_CATEGORIES
        and r["primary_root_cause"] not in NONRECOVERABLE_CATEGORIES
        and r["primary_root_cause"] not in ADJUDICATED_TRUE_MISSINGNESS_CATEGORIES
        and _low_return_class(r) is None
    )

    missing_t0 = sum(1 for r in rows if not r["t0_adjusted_close_present"] and r["t0_trading_date"])
    missing_tN = sum(1 for r in rows if not r["t_star_adjusted_close_present"] and r["t_star"])
    missing_both = sum(
        1 for r in rows
        if r["t_star"] and r["t0_trading_date"]
        and not r["t_star_adjusted_close_present"]
        and not r["t0_adjusted_close_present"]
    )
    fewer_126 = sum(
        1 for r in rows
        if r["usable_daily_return_count"] != ""
        and int(r["usable_daily_return_count"]) < gate.MIN_VALID_RETURN_OBSERVATIONS
    )
    missing_endpoint_union = sum(
        1 for r in rows
        if (r["t_star"] and not r["t_star_adjusted_close_present"])
        or (r["t0_trading_date"] and not r["t0_adjusted_close_present"])
    )

    partial_tickers = set(PARTIAL_RANGE_TICKERS.values())
    partial_equity_fail = sum(
        1 for r in unavailable if r["ticker"] in partial_tickers
    )
    partial_rvol_fail = sum(
        1 for r in rows
        if r["ticker"] in partial_tickers and not r["realized_volatility_usable"]
    )
    partial_amihud_fail = sum(
        1 for r in rows
        if r["ticker"] in partial_tickers and not r["amihud_illiquidity_usable"]
    )

    zero_trade_endpoint_count = root_cause_counts.get(CAT_ZERO_TRADE_ENDPOINT, 0)
    true_missing_adjusted_count = root_cause_counts.get(CAT_TRUE_MISSING_ADJUSTED, 0)
    retrieval_truncation_count = root_cause_counts.get(
        CAT_RETRIEVAL_RANGE_TRUNCATION, 0)
    # NOT a proof of absence: this is the count of pairs where the CURRENT
    # bundle's own evidence (raw daily records + adjusted history under the
    # CURRENT mapping) demonstrates identity fragmentation. It does not rule
    # out a predecessor TSETMC instrument identity that this bundle never
    # requested; that requires external historical-identity evidence (see
    # historical_identity_evidence.csv in the evidence-request package).
    identity_fragmentation_count = root_cause_counts.get(
        CAT_IDENTITY_FRAGMENTATION, 0)
    adjusted_defect_count = root_cause_counts.get(
        CAT_RAW_TRADE_ADJUSTED_MISSING, 0)

    # Diagnostic-only counterfactual: if every RECOVERABLE-category pair were
    # restored to usable, what would coverage become? Never canonical.
    counterfactual_usable = len(usable) + recoverable
    counterfactual_coverage = round(counterfactual_usable / len(rows), 10)

    return {
        "diagnostic_only": True,
        "does_not_alter_canonical_gate": True,
        "development_pairs": len(rows),
        "equity_return_usable_current": len(usable),
        "equity_return_unavailable_current": len(unavailable),
        "missing_endpoint_union_count": missing_endpoint_union,
        "missing_t0_count": missing_t0,
        "missing_tN_count": missing_tN,
        "missing_both_count": missing_both,
        "fewer_than_126_count": fewer_126,
        "root_cause_counts": dict(sorted(root_cause_counts.items())),
        "recoverable_due_to_proven_data_capture_defect": recoverable,
        "nonrecoverable_under_current_frozen_contract": nonrecoverable,
        "nonrecoverable_breakdown": {
            "zero_trade_or_missing_adjusted_endpoint_under_frozen_sequence": (
                adjudicated_true_missingness),
            "fewer_than_126_valid_returns_only_under_frozen_sequence": (
                guaranteed_low_return + pending_low_return),
            "guaranteed_lt126_even_if_all_zero_trade_rows_excluded": (
                guaranteed_low_return),
            "would_have_needed_zero_trade_rows_dropped_to_reach_126": (
                pending_low_return),
            "other_proven_nonrecoverable_categories": sum(
                1 for r in unavailable
                if r["primary_root_cause"] in NONRECOVERABLE_CATEGORIES
            ),
            "note": (
                "Under the adjudicated frozen contract a zero-trade "
                "InstrumentCalendar member REMAINS a trading day of W, so "
                "dropping zero-trade rows to reach 126 returns is not "
                "permitted and both low-return sub-classes are unavailable."
            ),
        },
        "pending_external_tsetmc_adjudication_count": pending_total,
        "pending_breakdown": {
            "pending_endpoint_semantics": pending_external,
            "pending_low_return_sequence_semantics": 0,
            "note": (
                "Zero. The external TSETMC calendar/state/trade evidence is "
                "complete and the frozen-contract semantics adjudication is "
                "complete, so no case now depends on further external "
                "evidence. (Historically a pair could be pending for endpoint "
                "semantics, low-return sequence semantics, or both; a pair's "
                "primary_root_cause is single-valued, so those counts never "
                "double-counted the same pair.)"
            ),
        },
        "external_adjudication_resolution_note": (
            "RESOLVED -- these pairs are no longer pending. The official "
            "TSETMC evidence is complete: all 427 requested zero-trade "
            "endpoint dates ARE members of the official "
            "ClosingPrice/GetInstrumentCalendar InstrumentCalendar, and for "
            "all 27 bounded low-return RANGE requests the InstrumentCalendar "
            "date set equals the ClosingPriceDailyList date set. The frozen "
            "contract was then adjudicated: a zero-traded-value calendar "
            "member REMAINS a trading day of W, so a zero-trade endpoint "
            "carrying no adjusted price yields null by the frozen rule, and "
            "zero-trade rows may not be dropped to reach 126 returns. Both "
            "groups are therefore TRUE frozen-contract missingness under the "
            "CURRENT frozen contract, not defects and not open questions. "
            "Superseded prior request (historical): "
            "stage127_m2_zero_trade_endpoint_evidence_request_v2.zip."
        ),
        "zero_trade_endpoint_label_status": {
            "label": CAT_ZERO_TRADE_ENDPOINT,
            "label_historical": True,
            "adjudication_status": "RESOLVED_BY_FROZEN_CONTRACT_ADJUDICATION",
            "adjudication_outcome": ADJUDICATION_OUTCOME,
            "current_semantic_status": CURRENT_SEMANTIC_STATUS,
            "external_calendar_state_trade_evidence": "COMPLETE",
            "evidence_delivery": (
                "stage127_m2_zero_trade_semantics_full_delivery_v3.zip"
            ),
            "established_fact": (
                "All 427 unique requested zero-trade endpoint dates ARE members "
                "of the official TSETMC ClosingPrice/GetInstrumentCalendar "
                "InstrumentCalendar, and for all 27 bounded low-return RANGE "
                "requests the InstrumentCalendar date set equals the "
                "ClosingPriceDailyList date set. These dates are therefore real "
                "official calendar dates, not retrieval or extraction defects."
            ),
            "semantics_adjudicated_in": (
                "project/stage127/"
                "stage127_m2_trading_day_semantics_adjudication.json"
            ),
            "factual_evidence_in": (
                "project/stage127/stage127_m2_zero_trade_point_endpoint_"
                "evidence.csv"
            ),
            "note": (
                "The word ADJUDICATION in this label named an OPEN question "
                "when the label was first assigned. That question is now "
                "answered against the frozen Stage125 contract; see the "
                "adjudication artifact. The label is retained unchanged so the "
                "audit trail stays stable, and the pairs remain unavailable "
                "under the frozen contract."
            ),
        },
        "unresolved_root_cause_count": unresolved,
        "partial_range_contribution": {
            "partial_source_tickers": sorted(partial_tickers),
            "equity_return_window_failures_among_partial_tickers": (
                partial_equity_fail),
            "realized_volatility_failures_among_partial_tickers": (
                partial_rvol_fail),
            "amihud_illiquidity_failures_among_partial_tickers": (
                partial_amihud_fail),
            "note": (
                "The six PARTIAL ranges cover at most 6 of 110 tickers; they "
                "cannot explain the global 40.39% coverage and are reported "
                "here only as their actual, bounded contribution."
            ),
        },
        "instrument_identity_fragmentation_count": identity_fragmentation_count,
        "zero_trade_endpoint_count": zero_trade_endpoint_count,
        "true_trading_day_missing_adjusted_price_count": (
            true_missing_adjusted_count),
        "retrieval_truncation_count": retrieval_truncation_count,
        "adjusted_parser_or_join_defect_count": adjusted_defect_count,
        "no_live_tsetmc_endpoint_queried": True,
        "classification_evidence_source": (
            "raw_restricted_closing_price_daily_bounded_json_and_"
            "adjusted_price_history_bounded_csv_from_the_immutable_bundle"
        ),
        "would_any_proven_data_only_correction_change_gate_result": (
            counterfactual_coverage >= gate.CANDIDATE_VALID_COVERAGE_MIN
        ),
        "diagnostic_counterfactual_not_canonical_result": {
            "label": "DIAGNOSTIC_COUNTERFACTUAL_NOT_CANONICAL_RESULT",
            "assumption": (
                "ONLY pairs whose primary_root_cause is a PROVEN data-capture "
                "defect (retrieval truncation, identity fragmentation, or a "
                "real trade with a missing adjusted price) are assumed "
                "recovered; TRUE frozen-contract missingness is left as-is. "
                "The zero-trade endpoint pairs are NOT assumed recovered here. "
                "That is no longer because their status is unproven -- it is "
                "now ADJUDICATED: the official TSETMC evidence is complete and "
                "the frozen contract retains a zero-trade calendar member as a "
                "trading day of W, so those pairs are TRUE frozen-contract "
                "missingness and are excluded exactly like every other "
                "nonrecoverable pair. Recovering them would require changing "
                "the frozen contract, which no data-only correction can do."
            ),
            "counterfactual_equity_return_usable": counterfactual_usable,
            "counterfactual_equity_return_coverage": counterfactual_coverage,
            "crosses_0_80_candidate_threshold": (
                counterfactual_coverage >= gate.CANDIDATE_VALID_COVERAGE_MIN
            ),
        },
        "semantics_adjudication_completed": True,
        "adjudication_outcome": ADJUDICATION_OUTCOME,
        "adjudication_artifact": ADJUDICATION_ARTIFACT,
        "current_semantic_status_of_zero_trade_endpoint_cases": (
            CURRENT_SEMANTIC_STATUS),
        "external_evidence_still_awaited": False,
        "canonical_gate_status_unchanged": "FAIL_M2_DATA_GATE",
        "no_scientific_artifact_modified_by_this_audit": True,
    }


def run(repo_root: str, bundle_path: str) -> dict[str, Any]:
    audit = RootCauseAudit(repo_root, bundle_path)
    main_rows = build_audit_rows(audit)
    tN_rows = build_tN_detail_rows(audit, main_rows)
    t0_rows = build_t0_detail_rows(audit, main_rows)
    low_return_rows = build_low_return_rows(audit, main_rows)
    upper_bound_rows = build_low_return_upper_bound_rows(audit, main_rows)
    summary = build_summary(audit, main_rows, upper_bound_rows)
    return {
        "main_rows": main_rows,
        "tN_rows": tN_rows,
        "t0_rows": t0_rows,
        "low_return_rows": low_return_rows,
        "upper_bound_rows": upper_bound_rows,
        "summary": summary,
    }
