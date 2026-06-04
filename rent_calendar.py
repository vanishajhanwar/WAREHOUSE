"""
rent_calendar.py — Rent Calendar View (Upgrade #3)

Replaces the 48-column data table with a visual monthly grid:
  - Each warehouse = a column
  - Each row = one month
  - Cells: green (paid), red (overdue), grey (no tenancy), amber (pending)
  - Tap any cell to see invoice detail and take action
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from data_manager import (
    get_rentals, get_tenants, get_warehouses, get_transaction_df,
    get_payments_for_month, ensure_payments_for_month,
    mark_payment_paid, mark_reminder_sent
)
from utils import inr_fmt
from settings import send_whatsapp_ultramsg, is_whatsapp_configured


def render_rent_calendar():
    st.markdown('<div class="section-header">📅 Rent Calendar</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">Every warehouse, every month — see who\'s paid and who hasn\'t</div>', unsafe_allow_html=True)

    df      = get_transaction_df()
    whs     = get_warehouses()
    tenants = {t["id"]: t for t in get_tenants()}
    rentals = get_rentals()

    if df.empty:
        st.info("No transaction data available. Add rentals in the Admin panel.")
        return

    # Month selector
    available_months = sorted(df["Month"].dt.to_period("M").unique(), reverse=True)
    month_labels     = [str(m) for m in available_months]

    col_sel, col_view = st.columns([2, 3])
    with col_sel:
        selected_label = st.selectbox("Select month", month_labels, index=0)
    with col_view:
        view_mode = st.radio("View", ["Calendar grid", "Detailed list"], horizontal=True)

    sel_period = pd.Period(selected_label, "M")
    sel_year   = sel_period.year
    sel_month  = sel_period.month

    # Filter df to selected month
    month_df = df[df["Month"].dt.to_period("M") == sel_period].copy()

    # Summary strip
    paid_rows   = month_df[month_df["Payment_Status"] == "Paid"]
    unpaid_rows = month_df[month_df["Payment_Status"] == "Not Paid"]
    total_due   = month_df["Total_Invoice_INR"].sum()
    total_paid  = paid_rows["Revenue_Collected_INR"].sum()
    total_out   = unpaid_rows["Balance_Due_INR"].sum()

    c1, c2, c3, c4 = st.columns(4)
    for col, val, label, bg, fg in [
        (c1, f"{len(month_df)}", "Invoices",    "#EBF2FA", "#185FA5"),
        (c2, inr_fmt(total_paid), "Collected",  "#E8F6F0", "#1D8A5F"),
        (c3, inr_fmt(total_out),  "Outstanding","#FCEAEA", "#A32D2D"),
        (c4, f"{len(paid_rows)}/{len(month_df)}", "Paid",  "#FDF6E3", "#854F0B"),
    ]:
        with col:
            st.markdown(
                f'<div style="background:{bg};border-radius:10px;padding:12px 14px;text-align:center;">'
                f'<div style="font-size:20px;font-weight:600;color:{fg}">{val}</div>'
                f'<div style="font-size:10px;color:{fg};text-transform:uppercase;letter-spacing:.06em">{label}</div>'
                f'</div>', unsafe_allow_html=True,
            )

    st.markdown("<br>", unsafe_allow_html=True)

    if view_mode == "Calendar grid":
        _render_grid(month_df, whs, sel_year, sel_month)
    else:
        _render_detail_list(month_df, sel_year, sel_month)


def _render_grid(month_df, whs, year, month):
    """Visual grid — warehouses as columns, status as colour-coded cells."""
    if month_df.empty:
        st.info("No transactions found for this month.")
        return

    # Build lookup: wh_id → row data
    wh_data = {}
    for _, row in month_df.iterrows():
        wh_data[row["WH_ID"]] = row

    # Render grid
    n_cols = min(len(whs), 3)
    cols   = st.columns(n_cols)

    for i, wh in enumerate(whs):
        with cols[i % n_cols]:
            row = wh_data.get(wh["id"])
            if row is None:
                # No tenancy this month
                st.markdown(
                    f'<div style="background:#F7F4EF;border-radius:12px;padding:16px;margin-bottom:12px;'
                    f'border:1px dashed #D3D1C7;text-align:center;">'
                    f'<div style="font-size:12px;font-weight:500;color:#888780">{wh["name"]}</div>'
                    f'<div style="font-size:10px;color:#B4B2A9;margin-top:4px">{wh["location"]}</div>'
                    f'<div style="font-size:10px;color:#B4B2A9;margin-top:8px">No tenancy</div>'
                    f'</div>', unsafe_allow_html=True,
                )
                continue

            paid   = row["Payment_Status"] == "Paid"
            delay  = int(row["Delay_Days"])
            bal    = row["Balance_Due_INR"]

            if paid:
                bg, fg   = "#E8F6F0", "#1D8A5F"
                status   = f"✅ Paid" + (f" ({delay}d late)" if delay > 0 else "")
            elif delay > 0:
                bg, fg   = "#FCEAEA", "#A32D2D"
                status   = f"🔴 {delay} days overdue"
            else:
                bg, fg   = "#FDF6E3", "#854F0B"
                status   = "🟡 Pending"

            phone  = str(row.get("Tenant_Phone", ""))
            wa_url = f"https://wa.me/91{phone}?text=Dear%20{str(row.get('Tenant_Name','')).replace(' ','%20')}%2C%20your%20rent%20of%20{inr_fmt(bal)}%20for%20{str(row.get('Month_Name',''))}%20is%20pending.%20Please%20pay%20at%20the%20earliest." if phone and not paid else ""

            st.markdown(
                f'<div style="background:{bg};border-radius:12px;padding:16px;margin-bottom:12px;">'
                f'<div style="font-size:13px;font-weight:500;color:{fg}">{wh["name"]}</div>'
                f'<div style="font-size:11px;color:{fg};opacity:.8">{row.get("Tenant_Name","—")}</div>'
                f'<div style="font-size:18px;font-weight:600;color:{fg};margin:8px 0">{inr_fmt(row["Total_Invoice_INR"])}</div>'
                f'<div style="font-size:11px;color:{fg}">{status}</div>'
                + (f'<a href="{wa_url}" target="_blank" style="display:inline-block;margin-top:8px;background:#25D366;color:white;font-size:10px;font-weight:600;padding:4px 10px;border-radius:20px;text-decoration:none">📱 Send reminder</a>' if wa_url else "")
                + f'</div>', unsafe_allow_html=True,
            )


def _render_detail_list(month_df, year, month):
    """Detailed list with mark-paid buttons."""
    if month_df.empty:
        st.info("No transactions found for this month.")
        return

    # Ensure payment records exist in DB for this month
    payments = ensure_payments_for_month(year, month)
    pay_map  = {p["tenant_id"]: p for p in payments}

    for _, row in month_df.sort_values("Balance_Due_INR", ascending=False).iterrows():
        paid   = row["Payment_Status"] == "Paid"
        bal    = row["Balance_Due_INR"]
        total  = row["Total_Invoice_INR"]
        delay  = int(row["Delay_Days"])
        tnt_id = row["Tenant_ID"]

        bg = "#E8F6F0" if paid else ("#FCEAEA" if delay > 0 else "#FFFDF7")
        fg = "#1D8A5F" if paid else ("#A32D2D" if delay > 0 else "#854F0B")

        payment_record = pay_map.get(tnt_id, {})
        pay_id = payment_record.get("id", "")

        with st.expander(f"{'✅' if paid else '🔴' if delay > 0 else '🟡'} {row['Tenant_Name']} — {row['Warehouse_Location']} — {inr_fmt(total)}"):
            cols = st.columns([2, 1])
            with cols[0]:
                st.markdown(f"**Warehouse:** {row.get('WH_ID','')} · {row.get('Warehouse_Location','')}")
                st.markdown(f"**Invoice:** {inr_fmt(row.get('Monthly_Rent_INR',0))} rent + {inr_fmt(row.get('GST_18pct_INR',0))} GST = **{inr_fmt(total)}**")
                st.markdown(f"**Status:** {row['Payment_Status']} · {f'{delay} days delay' if delay > 0 else 'On time'}")
                st.markdown(f"**Contact:** {row.get('Contact_Person','')} · {row.get('Tenant_Phone','')}")
            with cols[1]:
                if not paid and pay_id:
                    if st.button(f"✅ Mark paid", key=f"paid_{pay_id}"):
                        mark_payment_paid(pay_id, total)
                        st.success("Marked as paid!")
                        st.rerun()

                phone  = str(row.get("Tenant_Phone",""))
                if phone and not paid:
                    wa_msg = f"Dear {row.get('Tenant_Name','')}, your rent of {inr_fmt(bal)} for {row.get('Month_Name','')} is pending. Please arrange payment."
                    wa_url = f"https://wa.me/91{phone}?text={wa_msg.replace(' ','%20').replace(',','%2C')}"
                    st.markdown(f'<a href="{wa_url}" target="_blank" style="display:block;text-align:center;background:#25D366;color:white;font-size:12px;font-weight:600;padding:8px;border-radius:8px;text-decoration:none;margin-top:6px">📱 Send WhatsApp reminder</a>', unsafe_allow_html=True)

                    email = str(row.get("Tenant_Email",""))
                    if email:
                        st.markdown(f'<div style="font-size:10px;color:#888;margin-top:4px;text-align:center">Email: {email}</div>', unsafe_allow_html=True)
