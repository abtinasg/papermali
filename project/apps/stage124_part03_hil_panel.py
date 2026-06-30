"""Stage124 Batch02 Part 3.1B.1B — Human-in-the-Loop Streamlit panel.

This file contains only UI code. All operations are delegated to
``src.stage124_part03_hil_panel``.
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

_PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_DIR))

from src.stage124_part03_hil_panel import (  # noqa: E402
    ALLOWED_EVENT_CANDIDATES,
    ALLOWED_SOURCE_TYPES,
    ALLOWED_UPLOAD_EXTENSIONS,
    MAX_UPLOAD_BYTES,
    PART03_TICKERS,
    apply_submission,
    build_intake_row,
    load_dashboard_data,
    read_audit_events,
    sanitize_filename,
    store_snapshot,
)

_REVIEW_MODES = {
    "کشف منبع": "discovery",
    "نیازمند بررسی": "pending_manual_review",
    "بررسی‌شده": "reviewed",
    "ردشده": "rejected",
}

_DASHBOARD_COLUMNS = [
    "ticker",
    "company_name",
    "research_status",
    "evidence_status",
    "attempted_source_count",
    "fetched_source_count",
    "reviewed_source_count",
    "evidence_source_count",
    "ready_for_user_review",
    "proposed_canonical_public_entry_date_jalali",
    "conflict_flag",
    "recommended_next_step",
]

_DATE_PRECISIONS = ["unknown", "exact_day", "month_only", "year_only"]

st.set_page_config(
    page_title="Stage124 Part03 HIL",
    page_icon="🔎",
    layout="wide",
)

st.title("Stage124 Part03 — Human-in-the-Loop Panel")


_SNAPSHOT_STATE_KEYS = (
    "snapshot_path",
    "content_sha256",
    "snapshot_size",
    "snapshot_stored",
    "_last_upload_key",
)


def _clear_snapshot_state() -> None:
    """Remove all snapshot-related keys from session state."""
    for key in _SNAPSHOT_STATE_KEYS:
        st.session_state.pop(key, None)


def _snapshot_upload_key(selected_ticker: str, uploaded) -> tuple:
    """Return a stable key for the uploaded file including the ticker."""
    return (selected_ticker, uploaded.name, hashlib.sha256(uploaded.getvalue()).hexdigest())


def _render_preview(snapshot_path: str) -> None:
    """Render a safe, non-executable preview of the stored snapshot."""
    if not snapshot_path:
        return
    abs_path = _PROJECT_DIR / snapshot_path
    if not abs_path.exists():
        return
    ext = abs_path.suffix.lower()
    content = abs_path.read_bytes()
    if ext in {".png", ".jpg", ".jpeg", ".webp"}:
        st.image(str(abs_path))
    elif ext in {".html", ".htm"}:
        text = content.decode("utf-8", errors="replace")
        st.code(text[:20000], language="html")
        st.download_button(
            "دانلود HTML",
            data=content,
            file_name=abs_path.name,
            mime="text/html",
            key="download_html_preview",
        )
    elif ext in {".txt", ".json", ".csv"}:
        text = content.decode("utf-8", errors="replace")
        lang = {"json": "json", "csv": "csv"}.get(ext.lstrip("."), "text")
        st.code(text[:20000], language=lang)
    elif ext == ".pdf":
        st.info("PDF فقط از طریق دانلود قابل مشاهده است.")
        st.download_button(
            "دانلود PDF",
            data=content,
            file_name=abs_path.name,
            mime="application/pdf",
            key="download_pdf_preview",
        )
    else:
        st.info("پیش‌نمایش این نوع فایل پشتیبانی نمی‌شود.")


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("تنظیمات پنل")
    actor = st.text_input(
        "نام پژوهشگر / بازبین",
        key="actor",
        placeholder="مثلاً ali.researcher",
    )
    apply_mode = st.toggle(
        "حالت اعمال نهایی (Apply)",
        key="apply_mode",
        help="در حالت خاموش فقط اعتبارسنجی بدون تغییر فایل‌ها انجام می‌شود.",
    )
    st.text_input("مسیر پروژه", value=str(_PROJECT_DIR), disabled=True, key="project_path")
    if st.button("Refresh", key="refresh", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

apply_enabled = bool(actor.strip()) and apply_mode

# ---------------------------------------------------------------------------
# Dashboard data
# ---------------------------------------------------------------------------
data = load_dashboard_data(_PROJECT_DIR)
metrics = data.get("metrics", {})

# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------
tab_dashboard, tab_register, tab_review, tab_history = st.tabs(
    ["داشبورد", "ثبت منبع", "بررسی منبع", "سوابق"]
)

# ---------------------------------------------------------------------------
# Tab 1 — Dashboard
# ---------------------------------------------------------------------------
with tab_dashboard:
    st.subheader("داشبورد ۱۰ نماد Part03")
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("تعداد نمادها", metrics.get("ticker_count", len(PART03_TICKERS)))
    c2.metric("آماده برای بازبینی", metrics.get("ready_count", 0))
    c3.metric("نیازمند بررسی", metrics.get("requires_review_count", 0))
    c4.metric("دارای conflict", metrics.get("conflict_count", 0))
    c5.metric("Network blocked", metrics.get("network_blocked_count", 0))
    st.divider()

    screening = data.get("screening")
    if screening is not None and not screening.empty:
        display = screening[[c for c in _DASHBOARD_COLUMNS if c in screening.columns]]
        st.dataframe(display, hide_index=True, use_container_width=True)
    else:
        empty_df = pd.DataFrame(columns=_DASHBOARD_COLUMNS)
        st.info("هنوز خروجی research screening موجود نیست.")
        st.dataframe(empty_df, hide_index=True, use_container_width=True)

# ---------------------------------------------------------------------------
# Tab 2 — Source registration
# ---------------------------------------------------------------------------
with tab_register:
    st.subheader("ثبت منبع جدید")
    st.selectbox("نماد", PART03_TICKERS, key="ticker")
    st.selectbox(
        "نوع منبع",
        sorted(ALLOWED_SOURCE_TYPES),
        key="source_type",
    )
    st.text_input("URL", key="source_url", placeholder="https://www.codal.ir/...")
    st.text_input("عنوان منبع", key="source_title")
    st.text_area("یادداشت کشف", key="discovery_notes", height=100)
    st.radio(
        "حالت بررسی",
        list(_REVIEW_MODES.keys()),
        key="review_mode_fa",
        index=0,
    )

    review_mode = _REVIEW_MODES.get(st.session_state.get("review_mode_fa", "کشف منبع"), "discovery")

    st.divider()
    st.markdown("**Snapshot upload** (اختیاری برای کشف، اجباری برای بررسی‌شده)")
    uploaded = st.file_uploader(
        "فایل snapshot",
        type=[ext.lstrip(".") for ext in ALLOWED_UPLOAD_EXTENSIONS],
        key="snapshot_upload",
        help=f"حداکثر حجم: {MAX_UPLOAD_BYTES // 1024 // 1024} MB",
    )

    if uploaded is None:
        # Clear stale snapshot metadata when the user removes the upload.
        _clear_snapshot_state()
    else:
        selected_ticker = st.session_state.get("ticker", PART03_TICKERS[0])
        upload_key = _snapshot_upload_key(selected_ticker, uploaded)
        # Streamlit reruns the script whenever state changes; only store the
        # snapshot once per distinct (ticker, upload) to avoid duplicate files
        # on disk and to keep it attached to the correct ticker.
        if st.session_state.get("_last_upload_key") == upload_key:
            st.info("snapshot قبلاً ذخیره شده است.")
        else:
            try:
                snap = store_snapshot(
                    root=_PROJECT_DIR,
                    ticker=selected_ticker,
                    filename=uploaded.name,
                    content=uploaded.getvalue(),
                )
                st.session_state["snapshot_path"] = snap["snapshot_path"]
                st.session_state["content_sha256"] = snap["content_sha256"]
                st.session_state["snapshot_size"] = snap["size_bytes"]
                st.session_state["snapshot_stored"] = snap["stored_filename"]
                st.session_state["_last_upload_key"] = upload_key
                st.success("snapshot با موفقیت ذخیره شد.")
            except Exception as exc:
                st.error(f"خطا در ذخیره snapshot: {exc}")
                _clear_snapshot_state()

    if st.session_state.get("snapshot_path"):
        st.markdown("**پیش‌نمایش Snapshot**")
        st.json(
            {
                "نام فایل": st.session_state.get("snapshot_stored"),
                "حجم (بایت)": st.session_state.get("snapshot_size"),
                "SHA-256": st.session_state.get("content_sha256"),
                "نوع فایل": Path(st.session_state.get("snapshot_stored", "")).suffix,
            }
        )
        _render_preview(st.session_state.get("snapshot_path"))


def _handle_submission(action: str, actor: str) -> None:
    """Collect form state, build an intake row, and delegate to the core."""
    state = st.session_state
    review_mode = _REVIEW_MODES.get(state.get("review_mode_fa", "کشف منبع"), "discovery")
    try:
        row = build_intake_row(
            ticker=state.get("ticker", ""),
            source_type=state.get("source_type", ""),
            source_url=state.get("source_url", ""),
            source_title=state.get("source_title", ""),
            review_mode=review_mode,
            event_type=state.get("event_type", "") if review_mode == "reviewed" else "",
            candidate_date_jalali=state.get("candidate_date_jalali", "") if review_mode == "reviewed" else "",
            date_precision=state.get("date_precision", "unknown") if review_mode == "reviewed" else "unknown",
            ordinary_share_explicit=state.get("ordinary_share_explicit", "unknown") if review_mode == "reviewed" else "unknown",
            snapshot_path=state.get("snapshot_path", ""),
            content_sha256=state.get("content_sha256", ""),
            publication_date_jalali=state.get("publication_date_jalali", "") if review_mode == "reviewed" else "",
            actor=actor.strip(),
            discovery_notes=state.get("discovery_notes", ""),
            reviewer_notes=state.get("reviewer_notes", "") if review_mode in ("reviewed", "rejected") else "",
        )
    except Exception as exc:
        st.error(f"خطا در ساخت ردیف: {exc}")
        return

    if action == "validate":
        result = apply_submission(row=row, root=_PROJECT_DIR, actor=actor.strip(), action="validate")
        st.json(result)
    elif action == "apply":
        result = apply_submission(row=row, root=_PROJECT_DIR, actor=actor.strip(), action="apply")
        if result.get("applied"):
            st.success("Apply با موفقیت انجام شد.")
            _clear_snapshot_state()
        elif result.get("bridge_status") == "duplicate_blocked":
            st.error(result["errors"][0])
        else:
            st.error(f"Apply ناموفق: {result['errors']}")
        st.json(result)
    else:  # reject
        result = apply_submission(row=row, root=_PROJECT_DIR, actor=actor.strip(), action="reject")
        if result.get("rejected"):
            st.success("منبع ردشده با موفقیت ثبت شد.")
        else:
            st.error(f"ثبت رد منبع ناموفق بود: {result.get('errors', [])}")
        st.json(result)


# ---------------------------------------------------------------------------
# Tab 3 — Source review
# ---------------------------------------------------------------------------
with tab_review:
    st.subheader("بررسی و ثبت نهایی منبع")
    review_mode = _REVIEW_MODES.get(st.session_state.get("review_mode_fa", "کشف منبع"), "discovery")

    if review_mode == "reviewed":
        st.selectbox(
            "event type",
            sorted([e for e in ALLOWED_EVENT_CANDIDATES if e]),
            key="event_type",
        )
        st.text_input("candidate Jalali date", key="candidate_date_jalali", placeholder="YYYY-MM-DD")
        st.selectbox("date precision", _DATE_PRECISIONS, key="date_precision", index=0)
        st.radio(
            "ordinary share explicit",
            ["true", "false", "unknown"],
            key="ordinary_share_explicit",
            index=2,
        )
        st.text_input("publication date", key="publication_date_jalali", placeholder="YYYY-MM-DD")
        st.text_area("reviewer notes", key="reviewer_notes", height=120)
    elif review_mode == "rejected":
        st.text_area("دلیل رد", key="reviewer_notes", height=120)
    elif review_mode == "pending_manual_review":
        st.info("در حالت نیازمند بررسی، فیلدهای finding غیرفعال هستند.")
    else:
        st.info("در حالت کشف منبع، فقط منبع ثبت می‌شود و finding ایجاد نمی‌شود.")

    st.divider()
    col_validate, col_apply, col_reject = st.columns(3)

    with col_validate:
        validate_clicked = st.button(
            "اعتبارسنجی بدون اعمال",
            key="btn_validate",
            use_container_width=True,
        )

    with col_apply:
        confirm = st.checkbox(
            "تأیید می‌کنم منبع و Snapshot را شخصاً بررسی کرده‌ام و اطلاعات ثبت‌شده حدسی نیست.",
            key="confirm_apply",
            disabled=not apply_enabled,
        )
        apply_clicked = st.button(
            "اعمال نهایی در Provenance",
            key="btn_apply",
            use_container_width=True,
            disabled=not (apply_enabled and confirm),
        )

    with col_reject:
        reject_clicked = st.button(
            "ثبت منبع ردشده",
            key="btn_reject",
            use_container_width=True,
            disabled=not bool(actor.strip()),
        )

    if validate_clicked or apply_clicked or reject_clicked:
        action = "validate"
        if apply_clicked:
            action = "apply"
        elif reject_clicked:
            action = "reject"
        _handle_submission(action, actor)


# ---------------------------------------------------------------------------
# Tab 4 — History
# ---------------------------------------------------------------------------
with tab_history:
    st.subheader("سوابق عملیات پنل")
    events = read_audit_events(_PROJECT_DIR, limit=100)
    if not events:
        st.info("هنوز هیچ رویداد audit ثبت نشده است.")
    else:
        df = pd.DataFrame(events)
        display_cols = ["created_at_utc", "actor", "action", "ticker", "source_url", "review_mode", "bridge_status", "error"]
        available = [c for c in display_cols if c in df.columns]
        st.dataframe(df[available], hide_index=True, use_container_width=True)
        for ev in events[:5]:
            with st.expander(f"رویداد {ev.get('event_id', '')[:8]} — {ev.get('action', '')}"):
                st.json(ev)
