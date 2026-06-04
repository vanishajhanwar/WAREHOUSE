"""
app.py — WareHub Analytics Platform v4
Upgraded: SQLite storage, action-first navigation, rent calendar,
          WhatsApp-first collection, tenant risk tool, vacancy tracker,
          P&L export, PDF invoices, mobile-friendly layouts.
Run: streamlit run app.py
"""

import io
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import streamlit as st

from notifications import render_notification_page
from settings import render_settings_page, init_settings
from admin import render_admin_page
from data_manager import get_transaction_df, get_business, get_expiring_leases, get_vacancy_stats
from decisions import render_action_list, render_tenant_risk_tool, render_vacancy_tracker
from rent_calendar import render_rent_calendar
from pl_export import render_pl_export
from utils import (
    load_data, apply_filters, compute_kpis, inr_fmt,
    train_classifier, train_rent_regressor, train_delay_regressor,
    train_clustering, compute_association_rules, score_prospects,
    COLORS, PALETTE, PROSPECT_SCHEMA,
)
from charts import (
    monthly_revenue_trend, owner_revenue_bar, owner_revenue_pie,
    location_bar, payment_status_donut, payment_behaviour_bar,
    quarterly_revenue, wh_type_revenue, automation_summary,
    correlation_heatmap, rent_vs_size, rent_vs_type,
    delay_by_industry, delay_by_tenant_type, risk_score_histogram,
    location_type_heatmap,
    roc_curve_chart, confusion_matrix_chart, feature_importance_chart,
    regression_actual_vs_predicted,
    elbow_chart, cluster_scatter, cluster_profile_radar,
    association_heatmap, association_bubble,
    prospect_gauge, prospect_risk_bar,
)

# ════════════════════════════════════════════════════════════════════════════
# PAGE CONFIG
# ════════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="WareHub Analytics",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&family=DM+Serif+Display&display=swap');
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }

[data-testid="stSidebar"] { background: #0F1923; border-right: 1px solid #1E2D3D; }
[data-testid="stSidebar"] * { color: #C8D8E8 !important; }
[data-testid="stSidebar"] h1, h2, h3 { color: #FFFFFF !important; }
[data-testid="stSidebar"] .stMarkdown p { color: #90A4AE !important; font-size: 12px; }

.sidebar-section-label {
    font-size: 9px; font-weight: 600; color: #546E7A !important;
    text-transform: uppercase; letter-spacing: .1em;
    padding: 10px 4px 3px; margin: 0;
}

.kpi-card {
    background: #FFFFFF; border: 1px solid #E5E0D8;
    border-radius: 14px; padding: 14px 16px;
    box-shadow: 0 1px 4px rgba(15,25,35,.07);
}
.kpi-label { font-size: 10px; font-weight: 600; color: #64748B;
             text-transform: uppercase; letter-spacing: .07em; margin-bottom: 4px; }
.kpi-value { font-size: 22px; font-weight: 700; color: #0F1923;
             letter-spacing: -.03em; line-height: 1.1; }
.kpi-footer { font-size: 10px; color: #94A3B8; margin-top: 4px; }
.kpi-tag { display: inline-block; font-size: 9px; font-weight: 600;
           padding: 2px 8px; border-radius: 10px; margin-top: 6px;
           text-transform: uppercase; letter-spacing: .04em; }
.tag-green  { background: #E8F6F0; color: #1D8A5F; }
.tag-red    { background: #FCEAEA; color: #C0392B; }
.tag-amber  { background: #FDF6E3; color: #D97706; }
.tag-blue   { background: #EBF2FA; color: #1A3C5E; }

.alert-danger  { background:#FCEAEA;border:1px solid #F5C4C4;border-radius:10px;padding:10px 14px;margin-bottom:14px;font-size:13px;color:#C0392B; }
.alert-info    { background:#EBF2FA;border:1px solid #BDD5EE;border-radius:10px;padding:10px 14px;margin-bottom:14px;font-size:13px;color:#1A3C5E; }
.alert-success { background:#E8F6F0;border:1px solid #A8DDD8;border-radius:10px;padding:10px 14px;margin-bottom:14px;font-size:13px;color:#1D8A5F; }
.alert-warning { background:#FDF6E3;border:1px solid #F0DFA0;border-radius:10px;padding:10px 14px;margin-bottom:14px;font-size:13px;color:#D97706; }

.section-header { font-family:'DM Serif Display',serif;font-size:22px;color:#0F1923;letter-spacing:-.02em;margin-bottom:4px; }
.section-sub { font-size:13px;color:#64748B;margin-bottom:18px; }
.divider { border:none;border-top:1px solid #E5E0D8;margin:20px 0; }
</style>
""", unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════
# DATA LOADING
# ════════════════════════════════════════════════════════════════════════════
df_main = get_transaction_df()
init_settings()

biz = get_business()
if biz.get("phone") and not st.session_state.get("sender_phone_set"):
    import re as _re
    ph = _re.sub(r"\D","", biz["phone"])
    if not ph.startswith("91"): ph = "91" + ph
    st.session_state["sender_phone"] = ph
    st.session_state["sender_phone_set"] = True
if biz.get("email") and not st.session_state.get("gmail_user"):
    st.session_state["gmail_user_prefill"] = biz["email"]


# ════════════════════════════════════════════════════════════════════════════
# SIDEBAR — grouped navigation (Upgrade #1)
# ════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("## 🏭 WareHub")
    st.markdown(f"<span style='font-size:11px;color:#90A4AE'>Data as of Dec 2024</span>", unsafe_allow_html=True)
    st.markdown("---")

    # Urgency badge for action list
    expiring_count = len(get_expiring_leases(days_ahead=30))
    vacant_count   = sum(1 for v in get_vacancy_stats() if v["is_vacant"])
    overdue_count  = int((df_main["Payment_Status"] == "Not Paid").sum()) if not df_main.empty else 0
    urgent_total   = overdue_count + expiring_count

    st.markdown('<p class="sidebar-section-label">Day-to-day</p>', unsafe_allow_html=True)
    page = st.radio(
        "nav",
        options=[
            f"📋 Action list {'🔴' if urgent_total > 0 else ''}",
            "📅 Rent calendar",
            "📨 Invoice & reminders",
        ],
        label_visibility="collapsed",
        key="nav_ops",
    )

    st.markdown('<p class="sidebar-section-label">Analytics</p>', unsafe_allow_html=True)
    page2 = st.radio(
        "nav2",
        options=[
            "📊 Overview",
            "💰 Revenue analysis",
            "🔍 Why did it happen?",
        ],
        label_visibility="collapsed",
        key="nav_analytics",
    )

    st.markdown('<p class="sidebar-section-label">AI tools</p>', unsafe_allow_html=True)
    page3 = st.radio(
        "nav3",
        options=[
            "🔮 Should I sign this tenant?",
            "🏭 Vacancy & renewals",
            "🎯 Tenant segments",
            "🔗 Patterns & rules",
            "🚀 Score a prospect",
            "📈 Rent & delay forecasts",
        ],
        label_visibility="collapsed",
        key="nav_ai",
    )

    st.markdown('<p class="sidebar-section-label">Management</p>', unsafe_allow_html=True)
    page4 = st.radio(
        "nav4",
        options=[
            "📊 Annual P&L report",
            "⚙️ Settings",
            "🗂️ Admin — manage data",
        ],
        label_visibility="collapsed",
        key="nav_mgmt",
    )

    # Active page detection: whichever radio was most recently changed
    # We track via session state which group was touched last
    _all_pages = {
        f"📋 Action list {'🔴' if urgent_total > 0 else ''}": "action_list",
        "📅 Rent calendar": "rent_calendar",
        "📨 Invoice & reminders": "invoice",
        "📊 Overview": "overview",
        "💰 Revenue analysis": "revenue",
        "🔍 Why did it happen?": "diagnostic",
        "🔮 Should I sign this tenant?": "tenant_risk",
        "🏭 Vacancy & renewals": "vacancy",
        "🎯 Tenant segments": "clustering",
        "🔗 Patterns & rules": "association",
        "🚀 Score a prospect": "prospect",
        "📈 Rent & delay forecasts": "regression",
        "📊 Annual P&L report": "pl_export",
        "⚙️ Settings": "settings",
        "🗂️ Admin — manage data": "admin",
    }

    # Detect which group changed
    if "active_page" not in st.session_state:
        st.session_state["active_page"] = "action_list"
        st.session_state["_prev_ops"]     = page
        st.session_state["_prev_analytics"] = page2
        st.session_state["_prev_ai"]      = page3
        st.session_state["_prev_mgmt"]    = page4

    if page != st.session_state.get("_prev_ops"):
        st.session_state["active_page"] = _all_pages.get(page, "action_list")
        st.session_state["_prev_ops"] = page
    elif page2 != st.session_state.get("_prev_analytics"):
        st.session_state["active_page"] = _all_pages.get(page2, "overview")
        st.session_state["_prev_analytics"] = page2
    elif page3 != st.session_state.get("_prev_ai"):
        st.session_state["active_page"] = _all_pages.get(page3, "tenant_risk")
        st.session_state["_prev_ai"] = page3
    elif page4 != st.session_state.get("_prev_mgmt"):
        st.session_state["active_page"] = _all_pages.get(page4, "pl_export")
        st.session_state["_prev_mgmt"] = page4

    active = st.session_state["active_page"]

    st.markdown("---")

    # Filters (shown only for analytics pages)
    if active in {"overview", "revenue", "diagnostic"}:
        st.markdown("**Filters**")
        if not df_main.empty:
            owners    = ["All"] + sorted(df_main["Owner_Name"].dropna().unique().tolist())
            locations = ["All"] + sorted(df_main["Warehouse_Location"].dropna().unique().tolist())
            wh_types  = ["All"] + sorted(df_main["Warehouse_Type"].dropna().unique().tolist())
            years     = ["All"] + sorted(df_main["Month"].dt.year.dropna().unique().astype(str).tolist())
            sel_owner    = st.selectbox("Owner",    owners)
            sel_location = st.selectbox("Location", locations)
            sel_type     = st.selectbox("WH Type",  wh_types)
            sel_year     = st.selectbox("Year",     years)
            sel_pay      = st.selectbox("Payment",  ["All", "Paid", "Not Paid"])
            df = apply_filters(df_main, owner=sel_owner, location=sel_location,
                               wh_type=sel_type, pay_status=sel_pay, year=sel_year)
            n_filtered = len(df)
            n_total    = len(df_main)
            if n_filtered < n_total:
                st.caption(f"🔍 {n_filtered}/{n_total} records")
                if st.button("Reset filters", key="reset_filters"):
                    st.rerun()
        else:
            df = df_main
    else:
        df = df_main

    st.markdown("---")
    from data_manager import get_tenants as _get_tnt, get_warehouses as _get_wh
    st.caption(f"🏭 {len(_get_wh())} warehouses · {len(_get_tnt())} tenants")


# ── KPI helpers ───────────────────────────────────────────────────────────────
def kpi_card(label, value, footer="", tag="", tag_class="tag-blue"):
    return f"""
    <div class="kpi-card">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{value}</div>
        <div class="kpi-footer">{footer}</div>
        {'<span class="kpi-tag '+tag_class+'">'+tag+'</span>' if tag else ''}
    </div>"""


def render_kpis(df_kpi):
    kpis = compute_kpis(df_kpi)
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1:
        st.markdown(kpi_card("Total Invoiced", inr_fmt(kpis["total_inv"]), "incl. 18% GST", "Info", "tag-blue"), unsafe_allow_html=True)
    with c2:
        tc = "tag-green" if kpis["col_rate"] >= 85 else "tag-amber"
        st.markdown(kpi_card("Revenue Collected", inr_fmt(kpis["total_col"]), f"{kpis['col_rate']}% collection rate", "On track" if kpis["col_rate"] >= 85 else "Watch", tc), unsafe_allow_html=True)
    with c3:
        oc = "tag-red" if kpis["total_out"] > 100000 else "tag-amber"
        st.markdown(kpi_card("Outstanding", inr_fmt(kpis["total_out"]), f"{kpis['high_risk']} high-risk records", "Collect now" if kpis["total_out"] > 100000 else "Low", oc), unsafe_allow_html=True)
    with c4:
        pc = "tag-green" if kpis["paid_rate"] >= 85 else "tag-amber"
        st.markdown(kpi_card("Payment Rate", f"{kpis['paid_rate']}%", "of all transactions", "On track" if kpis["paid_rate"] >= 85 else "Review", pc), unsafe_allow_html=True)
    with c5:
        st.markdown(kpi_card("Avg Monthly Rent", inr_fmt(kpis["avg_rent"]), "active contracts", "Info", "tag-blue"), unsafe_allow_html=True)
    with c6:
        dc = "tag-red" if kpis["avg_delay"] > 20 else "tag-amber"
        st.markdown(kpi_card("Avg Delay (late only)", f"{kpis['avg_delay']}d", "delayed records only", "High" if kpis["avg_delay"] > 20 else "Moderate", dc), unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════
# PAGES
# ════════════════════════════════════════════════════════════════════════════

# ── ACTION LIST (Upgrade #1) ─────────────────────────────────────────────────
if active == "action_list":
    render_action_list()

# ── RENT CALENDAR (Upgrade #3) ───────────────────────────────────────────────
elif active == "rent_calendar":
    render_rent_calendar()

# ── INVOICE & REMINDERS (Upgrade #2) ────────────────────────────────────────
elif active == "invoice":
    render_notification_page(df)

# ── OVERVIEW ─────────────────────────────────────────────────────────────────
elif active == "overview":
    st.markdown('<div class="section-header">📊 Portfolio Overview</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">Family warehouse rental business — descriptive summary of all operations</div>', unsafe_allow_html=True)

    kpis = compute_kpis(df)
    if kpis["total_out"] > 0:
        overdue_tenants = df[df["Balance_Due_INR"] > 0]["Tenant_Name"].unique()
        st.markdown(
            f'<div class="alert-danger">⚠️ <strong>Collect now:</strong> '
            f'{inr_fmt(kpis["total_out"])} outstanding across {len(overdue_tenants)} tenant(s): '
            f'{", ".join(overdue_tenants[:3])}{"..." if len(overdue_tenants) > 3 else ""}. '
            f'Go to Invoice & Reminders to send one-tap WhatsApp reminders.</div>',
            unsafe_allow_html=True,
        )

    render_kpis(df)
    st.markdown("<hr class='divider'>", unsafe_allow_html=True)

    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        st.plotly_chart(monthly_revenue_trend(df), use_container_width=True)
    with c2:
        st.plotly_chart(payment_status_donut(df), use_container_width=True)
    with c3:
        st.plotly_chart(wh_type_revenue(df), use_container_width=True)

    c1, c2 = st.columns([3, 2])
    with c1:
        st.plotly_chart(location_bar(df), use_container_width=True)
    with c2:
        st.plotly_chart(payment_behaviour_bar(df), use_container_width=True)

    # Segment summary — now with action labels
    st.markdown("#### Tenant segments")
    seg_counts = df["Tenant_Segment"].value_counts()
    total_seg  = len(df)
    seg_config = {
        "High-Value Regular": ("#EBF2FA", "#1A3C5E", "⭐", "Offer 3-yr lock-in"),
        "Regular Payer":      ("#E8F6F0", "#1D8A5F", "✅", "Revise rent at CPI+2%"),
        "Late Payer":         ("#FDF6E3", "#D97706", "⏰", "Early payment discount"),
        "Defaulter":          ("#FCEAEA", "#C0392B", "⚠️", "Require 3-month advance"),
    }
    cols = st.columns(4)
    for i, (seg, cnt) in enumerate(seg_counts.items()):
        bg, fg, icon, action = seg_config.get(seg, ("#F7F4EF", "#0F1923", "•", ""))
        pct = round(cnt / total_seg * 100, 1)
        with cols[i % 4]:
            st.markdown(
                f'<div style="background:{bg};border-radius:12px;padding:14px;text-align:center;">'
                f'<div style="font-size:20px">{icon}</div>'
                f'<div style="font-size:11px;font-weight:600;color:{fg};text-transform:uppercase;'
                f'letter-spacing:.06em;margin:4px 0">{seg}</div>'
                f'<div style="font-size:28px;font-weight:700;color:{fg}">{cnt}</div>'
                f'<div style="font-size:10px;color:{fg};opacity:.7">{pct}% of records</div>'
                f'<div style="font-size:10px;font-weight:600;color:{fg};margin-top:6px;'
                f'opacity:.9">{action} →</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    st.markdown("<hr class='divider'>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(quarterly_revenue(df), use_container_width=True)
    with c2:
        st.plotly_chart(automation_summary(df), use_container_width=True)

# ── REVENUE ANALYSIS ─────────────────────────────────────────────────────────
elif active == "revenue":
    st.markdown('<div class="section-header">💰 Revenue Analysis</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">Owner-wise, location-wise and quarterly revenue breakdown</div>', unsafe_allow_html=True)
    render_kpis(df)
    st.markdown("<hr class='divider'>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(owner_revenue_bar(df), use_container_width=True)
    with c2:
        st.plotly_chart(owner_revenue_pie(df), use_container_width=True)
    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(quarterly_revenue(df), use_container_width=True)
    with c2:
        st.plotly_chart(location_type_heatmap(df), use_container_width=True)

    st.markdown("#### Location performance")
    loc_tbl = (df.groupby("Warehouse_Location").agg(
        Revenue=("Revenue_Collected_INR","sum"), Invoiced=("Total_Invoice_INR","sum"),
        Outstanding=("Balance_Due_INR","sum"), Avg_Rent=("Monthly_Rent_INR","mean"),
        Transactions=("Row_ID","count"), Paid_Rate=("Is_Paid_Binary","mean"),
    ).reset_index())
    loc_tbl["Collection_Rate"] = (loc_tbl["Revenue"]/loc_tbl["Invoiced"]*100).round(1)
    loc_tbl["Paid_Rate"]       = (loc_tbl["Paid_Rate"]*100).round(1)
    loc_tbl["Revenue"]         = loc_tbl["Revenue"].apply(inr_fmt)
    loc_tbl["Invoiced"]        = loc_tbl["Invoiced"].apply(inr_fmt)
    loc_tbl["Outstanding"]     = loc_tbl["Outstanding"].apply(inr_fmt)
    loc_tbl["Avg_Rent"]        = loc_tbl["Avg_Rent"].apply(lambda v: inr_fmt(round(v)))
    loc_tbl.columns = ["Location","Revenue","Invoiced","Outstanding","Avg Rent","Txns","Paid%","Collection%"]
    st.dataframe(loc_tbl, use_container_width=True, hide_index=True)

# ── DIAGNOSTIC ───────────────────────────────────────────────────────────────
elif active == "diagnostic":
    st.markdown('<div class="section-header">🔍 Why did it happen?</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">Correlation analysis, delay drivers, and risk patterns</div>', unsafe_allow_html=True)
    st.plotly_chart(correlation_heatmap(df), use_container_width=True)
    st.markdown('<div class="alert-info">📌 <strong>Key findings:</strong> WH Type vs Rent (strong positive), Risk Score vs Delay Days (strong positive), Tenure vs Delay (negative — longer tenants pay faster).</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1: st.plotly_chart(rent_vs_size(df), use_container_width=True)
    with c2: st.plotly_chart(rent_vs_type(df), use_container_width=True)
    c1, c2 = st.columns(2)
    with c1: st.plotly_chart(delay_by_industry(df), use_container_width=True)
    with c2: st.plotly_chart(delay_by_tenant_type(df), use_container_width=True)
    c1, c2 = st.columns(2)
    with c1: st.plotly_chart(risk_score_histogram(df), use_container_width=True)
    with c2: st.plotly_chart(location_type_heatmap(df), use_container_width=True)
    st.markdown("#### Pearson correlations")
    from scipy.stats import pearsonr
    pairs = [
        ("Monthly_Rent_INR","Size_Encoded","Rent vs WH Size"),
        ("Monthly_Rent_INR","Type_Encoded","Rent vs WH Type"),
        ("Delay_Days","TenantType_Encoded","Delay vs Tenant Type"),
        ("Delay_Days","Customer_Tenure_Months","Delay vs Tenure"),
        ("Risk_Score","Delay_Days","Risk Score vs Delay"),
        ("Is_Paid_Binary","Customer_Tenure_Months","Paid vs Tenure"),
        ("Monthly_Rent_INR","Lease_Duration_Months","Rent vs Lease Duration"),
    ]
    corr_rows = []
    for c1n, c2n, label in pairs:
        if c1n in df.columns and c2n in df.columns:
            sub = df[[c1n,c2n]].dropna()
            if len(sub) > 5:
                r, p = pearsonr(sub[c1n], sub[c2n])
                corr_rows.append({"Variables":label,"Pearson r":round(r,3),"p-value":round(p,4),"Strength":"Strong" if abs(r)>0.7 else ("Moderate" if abs(r)>0.4 else "Weak"),"Direction":"Positive ↑" if r>0 else "Negative ↓","Significant":"Yes ✓" if p<0.05 else "No"})
    st.dataframe(pd.DataFrame(corr_rows), use_container_width=True, hide_index=True)

# ── TENANT RISK TOOL (Upgrade #1) ────────────────────────────────────────────
elif active == "tenant_risk":
    render_tenant_risk_tool()

# ── VACANCY & RENEWALS (Upgrade #4) ──────────────────────────────────────────
elif active == "vacancy":
    render_vacancy_tracker()

# ── CLUSTERING — now called "Tenant segments" ────────────────────────────────
elif active == "clustering":
    st.markdown('<div class="section-header">🎯 Tenant Segments</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">K-Means clusters — who are your tenants and what should you do with each group?</div>', unsafe_allow_html=True)

    k_val = st.slider("Number of segments", 2, 8, 4)
    with st.spinner("Segmenting tenants..."):
        km_model, km_scaler, df_clustered, profile, inertias, feat_cluster = train_clustering(df_main, k=k_val)

    # Persona cards instead of raw table
    st.markdown("#### Segment personas")
    persona_config = {
        "High-Value Regular": ("⭐", "#EBF2FA", "#1A3C5E", "Offer 3-year lock-in with minor rent relief."),
        "Regular Payer":      ("✅", "#E8F6F0", "#1D8A5F", "Annual revision at CPI+2%. Stable income."),
        "Late Payer":         ("⏰", "#FDF6E3", "#D97706", "1% discount if paid by 5th. 2% penalty after 10th."),
        "At-Risk":            ("⚠️", "#FCEAEA", "#C0392B", "Legal notice. Require 3-month advance. Non-renewal."),
    }
    cols = st.columns(min(k_val, 4))
    for i, (cluster_id, row) in enumerate(profile.iterrows()):
        label = row.get("Label", f"Cluster {cluster_id}")
        icon, bg, fg, action = persona_config.get(label, ("•", "#F7F4EF", "#444", ""))
        with cols[i % min(k_val, 4)]:
            st.markdown(
                f'<div style="background:{bg};border-radius:14px;padding:16px;margin-bottom:10px;">'
                f'<div style="font-size:24px">{icon}</div>'
                f'<div style="font-size:13px;font-weight:600;color:{fg};margin:6px 0">{label}</div>'
                f'<div style="font-size:11px;color:{fg};opacity:.8">Count: {int(row.get("Count",0))}</div>'
                f'<div style="font-size:11px;color:{fg};opacity:.8">Avg rent: {inr_fmt(row.get("Avg_Rent",0))}</div>'
                f'<div style="font-size:11px;color:{fg};opacity:.8">Paid rate: {row.get("Paid_Rate",0)*100:.0f}%</div>'
                f'<div style="font-size:11px;color:{fg};margin-top:8px;font-weight:500">{action}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    c1, c2 = st.columns(2)
    with c1: st.plotly_chart(elbow_chart(inertias), use_container_width=True)
    with c2: st.plotly_chart(cluster_profile_radar(profile), use_container_width=True)
    st.plotly_chart(cluster_scatter(df_clustered), use_container_width=True)

    with st.expander("View all transactions by segment"):
        cluster_col = "Cluster_Label" if "Cluster_Label" in df_clustered.columns else "KMeans_Cluster"
        selected_cluster = st.selectbox("Filter by segment", ["All"] + sorted(df_clustered[cluster_col].unique().tolist()))
        view_df = df_clustered if selected_cluster == "All" else df_clustered[df_clustered[cluster_col] == selected_cluster]
        show_cols = [c for c in ["Tenant_Name","Warehouse_Location","Warehouse_Type","Monthly_Rent_INR","Delay_Days","Payment_Behavior","Risk_Score",cluster_col] if c in df_clustered.columns]
        st.dataframe(view_df[show_cols].head(50), use_container_width=True, hide_index=True)

# ── ASSOCIATION RULES — human-readable ───────────────────────────────────────
elif active == "association":
    st.markdown('<div class="section-header">🔗 Patterns & Rules</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">Which tenant types + warehouse types lead to late payment? Plain-English findings.</div>', unsafe_allow_html=True)
    min_sup = st.slider("Sensitivity (minimum support)", 0.01, 0.20, 0.05, 0.01)
    rules   = compute_association_rules(df_main, min_support=min_sup)
    if rules.empty:
        st.warning("No patterns found at this sensitivity. Try lowering the slider.")
    else:
        st.markdown("#### What the data says")
        for i, (_, rule) in enumerate(rules.head(6).iterrows()):
            lift    = rule["Lift"]
            conf    = rule["Confidence"]
            sup     = rule["Support"]
            outcome = rule["Consequent"]
            antec   = rule["Antecedent"]
            bg      = "#E8F6F0" if outcome == "Paid" else "#FCEAEA"
            fg      = "#1D8A5F" if outcome == "Paid" else "#A32D2D"
            icon    = "✅" if outcome == "Paid" else "⚠️"
            st.markdown(
                f'<div style="background:{bg};border-radius:12px;padding:14px 18px;margin-bottom:8px;">'
                f'<div style="font-size:13px;font-weight:500;color:{fg}">'
                f'{icon} When tenant is <strong>{antec}</strong> → <strong>{conf*100:.0f}%</strong> chance of <strong>{outcome}</strong></div>'
                f'<div style="font-size:11px;color:{fg};opacity:.8;margin-top:4px">'
                f'{lift:.1f}× more likely than average &nbsp;·&nbsp; Seen in {sup*100:.1f}% of all records ({int(rule["Count"])} transactions)</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
        with st.expander("View all rules (technical)"):
            display = rules.copy()
            display["Support"]    = (display["Support"]*100).round(2).astype(str) + "%"
            display["Confidence"] = (display["Confidence"]*100).round(1).astype(str) + "%"
            display["Lift"]       = display["Lift"].round(3)
            st.dataframe(display[["Antecedent","Consequent","Support","Confidence","Lift","Count"]], use_container_width=True, hide_index=True)

# ── PROSPECT SCORING ─────────────────────────────────────────────────────────
elif active == "prospect":
    st.markdown('<div class="section-header">🚀 Score a Prospect</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">Upload a list of prospects and get them ranked by payment reliability</div>', unsafe_allow_html=True)
    with st.spinner("Loading model..."):
        model_clf, scaler_clf, metrics_clf, feat_clf = train_classifier(df_main)
    st.markdown('<div class="alert-info">💡 Upload a CSV of prospects. The model scores each one and recommends whether to proceed.</div>', unsafe_allow_html=True)
    template_df = pd.DataFrame([
        {"Tenant_Name":"ABC Logistics","Tenant_Type":"Business","Industry_Type":"Logistics","Warehouse_Type":"Distribution Hub","Warehouse_Size":"Large","Monthly_Rent_INR":90000,"Customer_Tenure_Months":0,"Lease_Duration_Months":24},
        {"Tenant_Name":"Priya Textiles","Tenant_Type":"Business","Industry_Type":"Textile","Warehouse_Type":"Dry Warehouse","Warehouse_Size":"Medium","Monthly_Rent_INR":35000,"Customer_Tenure_Months":0,"Lease_Duration_Months":12},
    ])
    buf = io.BytesIO()
    template_df.to_csv(buf, index=False); buf.seek(0)
    st.download_button("⬇️ Download template CSV", data=buf, file_name="prospect_template.csv", mime="text/csv")
    uploaded = st.file_uploader("Upload prospect CSV", type=["csv"])
    use_manual = st.checkbox("Enter one prospect manually")
    prospects_df = None
    if uploaded:
        try:
            prospects_df = pd.read_csv(uploaded)
            st.success(f"✅ Loaded {len(prospects_df)} prospects.")
        except Exception as e:
            st.error(f"Error: {e}")
    elif use_manual:
        with st.form("manual_prospect"):
            mc1, mc2, mc3 = st.columns(3)
            with mc1:
                m_name=st.text_input("Name","New Prospect Ltd"); m_ttype=st.selectbox("Type",["Business","Individual"]); m_ind=st.text_input("Industry","Logistics")
            with mc2:
                m_wtype=st.selectbox("WH Type",["Distribution Hub","Cold Storage","Dry Warehouse","General"]); m_wsize=st.selectbox("WH Size",["Large","Medium","Small"]); m_rent=st.number_input("Monthly Rent (₹)",5000,300000,50000,step=1000)
            with mc3:
                m_tenure=st.slider("Est. tenure (months)",0,60,0); m_lease=st.slider("Lease duration (months)",6,36,12)
            if st.form_submit_button("Score this prospect", type="primary"):
                prospects_df = pd.DataFrame([{"Tenant_Name":m_name,"Tenant_Type":m_ttype,"Industry_Type":m_ind,"Warehouse_Type":m_wtype,"Warehouse_Size":m_wsize,"Monthly_Rent_INR":m_rent,"Customer_Tenure_Months":m_tenure,"Lease_Duration_Months":m_lease}])
    if prospects_df is not None and not prospects_df.empty:
        try:
            scored = score_prospects(prospects_df, model_clf, scaler_clf, feat_clf)
            st.markdown("### Results")
            if len(scored) <= 3:
                gcols = st.columns(len(scored))
                for i, (_, row) in enumerate(scored.iterrows()):
                    with gcols[i]:
                        st.plotly_chart(prospect_gauge(float(row["Pay_Probability"]), row.get("Tenant_Name",f"Prospect {i+1}")), use_container_width=True)
            else:
                st.plotly_chart(prospect_risk_bar(scored), use_container_width=True)
            out_df = scored[["Tenant_Name","Tenant_Type","Warehouse_Type","Warehouse_Size","Monthly_Rent_INR","Pay_Probability","Risk_Tier","Recommended_Action"]].copy()
            out_df["Pay_Probability"] = (out_df["Pay_Probability"]*100).round(1).astype(str)+"%"
            st.dataframe(out_df, use_container_width=True, hide_index=True)
        except Exception as e:
            st.error(f"Scoring error: {e}")

# ── REGRESSION ───────────────────────────────────────────────────────────────
elif active == "regression":
    st.markdown('<div class="section-header">📈 Rent & Delay Forecasts</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">What should I charge? How long will a late payer take to pay?</div>', unsafe_allow_html=True)
    with st.spinner("Training models..."):
        model_rent, metrics_rent, feat_rent   = train_rent_regressor(df_main)
        model_delay, metrics_delay, feat_delay = train_delay_regressor(df_main)
    st.markdown("#### Rent estimator — what should I charge?")
    with st.form("rent_form"):
        rc1,rc2,rc3 = st.columns(3)
        with rc1: r_size=st.selectbox("WH Size",["Small","Medium","Large"])
        with rc2: r_type=st.selectbox("WH Type",["General","Dry Warehouse","Cold Storage","Distribution Hub"])
        with rc3: r_lease=st.slider("Lease duration (months)",6,36,12)
        r_tenure=st.slider("Tenant tenure (months)",1,60,12)
        if st.form_submit_button("Estimate fair rent",type="primary"):
            from utils import SIZE_MAP, TYPE_MAP
            X_new = pd.DataFrame([{"Size_Encoded":SIZE_MAP.get(r_size,2),"Type_Encoded":TYPE_MAP.get(r_type,2),"Month_Num":25,"Customer_Tenure_Months":r_tenure,"Lease_Duration_Months":r_lease}])[feat_rent]
            pred_rent = model_rent.predict(X_new)[0]
            st.success(f"💰 Estimated fair rent: **{inr_fmt(max(5000,pred_rent))}** / month")
    with st.expander("Technical model details"):
        r1,r2,r3 = st.columns(3)
        with r1: st.metric("R² Score",f"{metrics_rent['r2']:.3f}")
        with r2: st.metric("MAE",inr_fmt(metrics_rent['mae']))
        with r3: st.metric("RMSE",inr_fmt(metrics_rent['rmse']))
        st.plotly_chart(regression_actual_vs_predicted(metrics_rent["y_test"],metrics_rent["y_pred"],"Rent — Actual vs Predicted"), use_container_width=True)

# ── P&L EXPORT (Upgrade #8) ──────────────────────────────────────────────────
elif active == "pl_export":
    render_pl_export()

# ── SETTINGS ─────────────────────────────────────────────────────────────────
elif active == "settings":
    render_settings_page()

# ── ADMIN ────────────────────────────────────────────────────────────────────
elif active == "admin":
    render_admin_page()
