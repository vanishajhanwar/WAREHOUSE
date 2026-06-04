"""
decisions.py — Business Decision Engine (Upgrade #1 + #4)

Replaces raw ML pages with actionable business tools:
  1. "Who needs attention today" — daily prioritised action list
  2. "Should I sign this tenant?" — single verdict from the ML model
  3. Vacancy tracker with revenue loss counter
  4. Lease renewal alerts
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from utils import train_classifier, inr_fmt, encode_prospect
from data_manager import (
    get_rentals, get_tenants, get_warehouses, get_transaction_df,
    get_vacancy_stats, get_expiring_leases, get_business
)


# ════════════════════════════════════════════════════════════════════════════
# PAGE: WHO NEEDS ATTENTION TODAY
# ════════════════════════════════════════════════════════════════════════════

def render_action_list():
    st.markdown('<div class="section-header">📋 What needs your attention today?</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">Everything that needs action, in one place — sorted by urgency</div>', unsafe_allow_html=True)

    df     = get_transaction_df()
    today  = datetime.today()
    actions = []

    # ── 1. Overdue payments ──────────────────────────────────────────────────
    if not df.empty:
        overdue = df[(df["Payment_Status"] == "Not Paid") & (df["Delay_Days"] > 0)].copy()
        overdue = overdue.sort_values("Delay_Days", ascending=False)
        for _, row in overdue.iterrows():
            actions.append({
                "priority": "🔴 Urgent",
                "priority_order": 1,
                "action": f"Collect payment from **{row['Tenant_Name']}**",
                "detail": f"{inr_fmt(row['Balance_Due_INR'])} overdue — {int(row['Delay_Days'])} days late",
                "phone":  row.get("Tenant_Phone", ""),
                "wh":     row.get("Warehouse_Location", ""),
                "type":   "collect",
                "month":  str(row.get("Month_Name", "")),
            })

    # ── 2. Expiring leases ───────────────────────────────────────────────────
    expiring = get_expiring_leases(days_ahead=60)
    for lease in expiring:
        urgency = "🔴 Urgent" if lease["days_left"] <= 14 else ("🟡 Soon" if lease["days_left"] <= 30 else "🟢 Plan ahead")
        order   = 1 if lease["days_left"] <= 14 else (2 if lease["days_left"] <= 30 else 3)
        actions.append({
            "priority":       urgency,
            "priority_order": order,
            "action":         f"Renew lease for **{lease['tenant_name']}**",
            "detail":         f"{lease['wh_name']} — expires in {lease['days_left']} days ({lease['end_date']})",
            "phone":          lease.get("tenant_phone", ""),
            "wh":             lease.get("wh_location", ""),
            "type":           "renewal",
            "month":          "",
        })

    # ── 3. Vacant warehouses ─────────────────────────────────────────────────
    vacancies = [v for v in get_vacancy_stats() if v["is_vacant"]]
    for v in vacancies:
        days = v.get("days_vacant", 0)
        loss = v.get("revenue_lost", 0)
        actions.append({
            "priority":       "🟡 Soon",
            "priority_order": 2,
            "action":         f"Find tenant for **{v['name']}**",
            "detail":         f"{v['location']} — vacant {days} days, ₹{int(loss):,} revenue lost",
            "phone":          "",
            "wh":             v.get("location", ""),
            "type":           "vacancy",
            "month":          "",
        })

    if not actions:
        st.markdown(
            '<div class="alert-success">✅ <strong>All clear!</strong> No urgent actions needed today. Your portfolio is healthy.</div>',
            unsafe_allow_html=True,
        )
        return

    # Sort by priority
    actions.sort(key=lambda x: x["priority_order"])

    # Summary strip
    urgent_count = sum(1 for a in actions if a["priority_order"] == 1)
    soon_count   = sum(1 for a in actions if a["priority_order"] == 2)
    plan_count   = sum(1 for a in actions if a["priority_order"] == 3)

    c1, c2, c3 = st.columns(3)
    for col, count, label, bg, fg in [
        (c1, urgent_count, "Urgent — act today", "#FCEAEA", "#A32D2D"),
        (c2, soon_count,   "Due this week",       "#FDF6E3", "#854F0B"),
        (c3, plan_count,   "Plan ahead",          "#E8F6F0", "#1D8A5F"),
    ]:
        with col:
            st.markdown(
                f'<div style="background:{bg};border-radius:12px;padding:14px 18px;text-align:center;">'
                f'<div style="font-size:28px;font-weight:600;color:{fg}">{count}</div>'
                f'<div style="font-size:11px;color:{fg};text-transform:uppercase;letter-spacing:.06em">{label}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    st.markdown("<br>", unsafe_allow_html=True)

    # Action cards
    color_map = {
        "collect":  ("#FCEAEA", "#A32D2D", "💰"),
        "renewal":  ("#FDF6E3", "#854F0B", "📄"),
        "vacancy":  ("#EBF2FA", "#185FA5", "🏭"),
    }

    for i, act in enumerate(actions):
        bg, fg, icon = color_map.get(act["type"], ("#F7F4EF", "#444", "•"))
        phone = act["phone"]
        wa_url = f"https://wa.me/91{phone}?text=Hello%2C%20this%20is%20a%20reminder%20regarding%20your%20WareHub%20account." if phone else ""

        st.markdown(
            f'<div style="background:{bg};border-radius:12px;padding:14px 18px;'
            f'margin-bottom:10px;display:flex;align-items:flex-start;gap:12px;">'
            f'<div style="font-size:22px;line-height:1">{icon}</div>'
            f'<div style="flex:1;">'
            f'<div style="font-size:13px;color:{fg};font-weight:500">{act["priority"]} &nbsp;·&nbsp; {act["action"]}</div>'
            f'<div style="font-size:12px;color:{fg};opacity:.8;margin-top:3px">{act["detail"]}</div>'
            f'</div>'
            + (f'<a href="{wa_url}" target="_blank" style="background:#25D366;color:white;'
               f'font-size:11px;font-weight:600;padding:6px 12px;border-radius:20px;'
               f'text-decoration:none;white-space:nowrap;align-self:center">📱 WhatsApp</a>'
               if wa_url else "")
            + '</div>',
            unsafe_allow_html=True,
        )


# ════════════════════════════════════════════════════════════════════════════
# PAGE: SHOULD I SIGN THIS TENANT?
# ════════════════════════════════════════════════════════════════════════════

def render_tenant_risk_tool():
    st.markdown('<div class="section-header">🔮 Should I sign this tenant?</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">Enter the prospect\'s details — get a plain-English verdict in seconds</div>', unsafe_allow_html=True)

    df_main = get_transaction_df()

    with st.spinner("Loading risk model..."):
        model_clf, scaler_clf, metrics_clf, feat_clf = train_classifier(df_main)

    # Accuracy callout
    acc = round(metrics_clf["accuracy"] * 100, 1)
    st.markdown(
        f'<div class="alert-info">🤖 This model is trained on your actual rental history. '
        f'It correctly identifies <strong>{acc}%</strong> of payment outcomes.</div>',
        unsafe_allow_html=True,
    )

    with st.form("tenant_risk_form"):
        st.markdown("#### Enter prospect details")
        c1, c2, c3 = st.columns(3)
        with c1:
            p_name   = st.text_input("Prospect name", "New Prospect Ltd")
            p_ttype  = st.selectbox("Tenant type", ["Business", "Individual"])
            p_rent   = st.number_input("Monthly rent (₹)", 5000, 500000, 45000, step=1000)
        with c2:
            p_size   = st.selectbox("Warehouse size", ["Small", "Medium", "Large"])
            p_type   = st.selectbox("Warehouse type", ["General", "Dry Warehouse", "Cold Storage", "Distribution Hub"])
            p_lease  = st.slider("Lease duration (months)", 6, 36, 12)
        with c3:
            p_tenure = st.slider("Estimated prior tenancy (months)", 0, 60, 0)
            p_risk   = st.slider("Estimated risk score (0=low, 100=high)", 0, 100, 30)
        submitted = st.form_submit_button("Get Verdict", type="primary", use_container_width=True)

    if submitted:
        from utils import SIZE_MAP, TYPE_MAP, TTYPE_MAP
        enc = encode_prospect({
            "Monthly_Rent_INR": p_rent, "Warehouse_Size": p_size,
            "Warehouse_Type": p_type, "Tenant_Type": p_ttype,
            "Customer_Tenure_Months": p_tenure, "Lease_Duration_Months": p_lease,
            "Risk_Score": p_risk,
        }, month_num=25)
        row   = pd.DataFrame([enc])[feat_clf]
        row_s = scaler_clf.transform(row)
        prob  = model_clf.predict_proba(row_s)[0][1]

        st.markdown("---")
        if prob >= 0.75:
            verdict_bg, verdict_fg = "#E8F6F0", "#1D8A5F"
            verdict_icon = "✅"
            verdict_text = "Low risk — proceed with standard contract"
            action_text  = "Standard 1-month security deposit. Standard rental agreement."
        elif prob >= 0.5:
            verdict_bg, verdict_fg = "#FDF6E3", "#854F0B"
            verdict_icon = "⚠️"
            verdict_text = "Medium risk — proceed with caution"
            action_text  = "Increase security deposit to 2 months. Add penalty clause for late payment."
        else:
            verdict_bg, verdict_fg = "#FCEAEA", "#A32D2D"
            verdict_icon = "🚫"
            verdict_text = "High risk — do not proceed without protection"
            action_text  = "Require 3-month advance OR decline tenancy. If proceeding, add monthly auto-debit clause."

        st.markdown(
            f'<div style="background:{verdict_bg};border-radius:16px;padding:24px 28px;text-align:center;">'
            f'<div style="font-size:48px">{verdict_icon}</div>'
            f'<div style="font-size:20px;font-weight:600;color:{verdict_fg};margin:8px 0">{p_name}</div>'
            f'<div style="font-size:15px;color:{verdict_fg};margin-bottom:8px">{verdict_text}</div>'
            f'<div style="font-size:24px;font-weight:700;color:{verdict_fg}">{prob*100:.0f}% chance of paying on time</div>'
            f'<div style="font-size:12px;color:{verdict_fg};opacity:.7;margin-top:6px">Based on warehouse type, rent level, and lease duration</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div style="background:#F7F4EF;border-radius:10px;padding:14px 18px;margin-top:12px;font-size:13px;color:#444">'
            f'<strong>Recommended action:</strong> {action_text}</div>',
            unsafe_allow_html=True,
        )

        # Technical expander
        with st.expander("View technical details (for academic review)"):
            from charts import roc_curve_chart, confusion_matrix_chart, feature_importance_chart
            c1, c2 = st.columns(2)
            with c1:
                st.plotly_chart(roc_curve_chart(metrics_clf["fpr"], metrics_clf["tpr"], metrics_clf["roc_auc"]), use_container_width=True)
            with c2:
                st.plotly_chart(confusion_matrix_chart(metrics_clf["cm"]), use_container_width=True)
            st.plotly_chart(feature_importance_chart(metrics_clf["feature_names"], metrics_clf["feature_importance"]), use_container_width=True)
            m1,m2,m3,m4,m5 = st.columns(5)
            for col, lbl, val in [(m1,"Accuracy",f"{metrics_clf['accuracy']*100:.1f}%"),(m2,"Precision",f"{metrics_clf['precision']*100:.1f}%"),(m3,"Recall",f"{metrics_clf['recall']*100:.1f}%"),(m4,"F1",f"{metrics_clf['f1']*100:.1f}%"),(m5,"ROC-AUC",f"{metrics_clf['roc_auc']:.3f}")]:
                with col:
                    st.metric(lbl, val)


# ════════════════════════════════════════════════════════════════════════════
# PAGE: VACANCY & RENEWAL TRACKER
# ════════════════════════════════════════════════════════════════════════════

def render_vacancy_tracker():
    st.markdown('<div class="section-header">🏭 Vacancy & Renewal Tracker</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">Empty warehouses and expiring leases — your two biggest revenue risks</div>', unsafe_allow_html=True)

    # ── Vacancies ────────────────────────────────────────────────────────────
    st.markdown("#### Warehouse occupancy")
    vacancies = get_vacancy_stats()
    total_wh  = len(vacancies)
    vacant    = [v for v in vacancies if v["is_vacant"]]
    occupied  = [v for v in vacancies if not v["is_vacant"]]

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(
            f'<div style="background:#E8F6F0;border-radius:12px;padding:14px 18px;text-align:center;">'
            f'<div style="font-size:28px;font-weight:600;color:#1D8A5F">{len(occupied)}</div>'
            f'<div style="font-size:11px;color:#1D8A5F;text-transform:uppercase;letter-spacing:.06em">Occupied</div>'
            f'</div>', unsafe_allow_html=True,
        )
    with c2:
        lost = sum(v["revenue_lost"] for v in vacant)
        st.markdown(
            f'<div style="background:#FCEAEA;border-radius:12px;padding:14px 18px;text-align:center;">'
            f'<div style="font-size:28px;font-weight:600;color:#A32D2D">{len(vacant)}</div>'
            f'<div style="font-size:11px;color:#A32D2D;text-transform:uppercase;letter-spacing:.06em">Vacant</div>'
            f'</div>', unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            f'<div style="background:#FDF6E3;border-radius:12px;padding:14px 18px;text-align:center;">'
            f'<div style="font-size:22px;font-weight:600;color:#854F0B">{inr_fmt(lost)}</div>'
            f'<div style="font-size:11px;color:#854F0B;text-transform:uppercase;letter-spacing:.06em">Revenue lost to vacancy</div>'
            f'</div>', unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # Occupancy grid
    cols = st.columns(min(total_wh, 3))
    for i, v in enumerate(vacancies):
        with cols[i % min(total_wh, 3)]:
            bg  = "#FCEAEA" if v["is_vacant"] else "#E8F6F0"
            fg  = "#A32D2D" if v["is_vacant"] else "#1D8A5F"
            status = f"🔴 Vacant — {v['days_vacant']} days" if v["is_vacant"] else "🟢 Occupied"
            st.markdown(
                f'<div style="background:{bg};border-radius:12px;padding:14px;margin-bottom:10px">'
                f'<div style="font-size:13px;font-weight:500;color:{fg}">{v["name"]}</div>'
                f'<div style="font-size:11px;color:{fg};opacity:.8">{v["location"]} · {v["type"]}</div>'
                f'<div style="font-size:11px;color:{fg};margin-top:6px">{status}</div>'
                + (f'<div style="font-size:11px;color:{fg};margin-top:3px">Revenue lost: {inr_fmt(v["revenue_lost"])}</div>' if v["is_vacant"] and v["revenue_lost"] > 0 else "")
                + f'</div>', unsafe_allow_html=True,
            )

    # ── Expiring leases ──────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("#### Leases expiring in the next 60 days")
    expiring = get_expiring_leases(days_ahead=60)

    if not expiring:
        st.markdown('<div class="alert-success">✅ No leases expiring in the next 60 days.</div>', unsafe_allow_html=True)
    else:
        for lease in expiring:
            urgency_bg = "#FCEAEA" if lease["days_left"] <= 14 else ("#FDF6E3" if lease["days_left"] <= 30 else "#E8F6F0")
            urgency_fg = "#A32D2D" if lease["days_left"] <= 14 else ("#854F0B" if lease["days_left"] <= 30 else "#1D8A5F")
            urgency_label = "Act now" if lease["days_left"] <= 14 else ("Soon" if lease["days_left"] <= 30 else "Plan ahead")

            phone  = lease.get("tenant_phone","")
            wa_url = f"https://wa.me/91{phone}?text=Hello%20{lease['tenant_name'].replace(' ','%20')}%2C%20we%20would%20like%20to%20discuss%20renewing%20your%20lease%20at%20{lease['wh_name'].replace(' ','%20')}." if phone else ""

            st.markdown(
                f'<div style="background:{urgency_bg};border-radius:12px;padding:14px 18px;margin-bottom:8px;display:flex;align-items:center;gap:12px;">'
                f'<div style="flex:1">'
                f'<div style="font-size:13px;font-weight:500;color:{urgency_fg}">{lease["tenant_name"]} — {lease["wh_name"]}</div>'
                f'<div style="font-size:11px;color:{urgency_fg};opacity:.8">Expires {lease["end_date"]} · {lease["days_left"]} days left · ₹{int(lease["monthly_rent"]):,}/month</div>'
                f'</div>'
                f'<div style="font-size:10px;font-weight:600;padding:3px 10px;border-radius:10px;background:{urgency_fg};color:white">{urgency_label}</div>'
                + (f'<a href="{wa_url}" target="_blank" style="background:#25D366;color:white;font-size:11px;font-weight:600;padding:6px 12px;border-radius:20px;text-decoration:none;white-space:nowrap">📱 WhatsApp</a>' if wa_url else "")
                + '</div>',
                unsafe_allow_html=True,
            )
