"""
notifications.py — Invoice & Reminder Notification Engine
Warehouse Rental Management Analytics — Data Analytics MGB Project

Handles:
  1. Invoice generation (HTML + text format)
  2. Reminder generation for overdue tenants
  3. Gmail SMTP sending (real emails)
  4. WhatsApp deep-link sending (wa.me)
  5. Notification log tracking
"""

import smtplib
import ssl
import re
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import streamlit as st
import streamlit.components.v1 as components
from utils import inr_fmt, COLORS

# ── BUSINESS INFO ─────────────────────────────────────────────────────────────
BUSINESS_NAME    = "WareHub Family Properties"
BUSINESS_ADDRESS = "123, Industrial Estate, Udaipur, Rajasthan — 313001"
BUSINESS_GSTIN   = "08AABCW1234F1ZX"
BUSINESS_PAN     = "AABCW1234F"
BUSINESS_PHONE   = "+91-9876543210"
BUSINESS_EMAIL   = "billing@warehub.in"
BANK_NAME        = "State Bank of India"
BANK_ACCOUNT     = "32145678901234"
BANK_IFSC        = "SBIN0001234"
BANK_BRANCH      = "Udaipur Main Branch"
UPI_ID           = "warehub@sbi"


# ════════════════════════════════════════════════════════════════════════════
# INVOICE GENERATOR
# ════════════════════════════════════════════════════════════════════════════

def generate_invoice_html(row: dict) -> str:
    """Generate a professional HTML invoice for one tenant-month row."""
    inv_date     = row.get("Invoice_Date", datetime.today().strftime("%Y-%m-%d"))
    due_date     = row.get("Due_Date",     (datetime.today() + timedelta(days=10)).strftime("%Y-%m-%d"))
    base_rent    = float(row.get("Monthly_Rent_INR", 0))
    gst_amt      = float(row.get("GST_18pct_INR",    0))
    total        = float(row.get("Total_Invoice_INR", base_rent + gst_amt))
    inv_id       = row.get("Row_ID", f"INV-{datetime.today().strftime('%Y%m%d')}")
    month_name   = row.get("Month_Name", datetime.today().strftime("%b-%Y"))

    html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
  body {{ font-family: Arial, sans-serif; color: #1A1A1A; margin: 0; padding: 0; background: #f5f5f5; }}
  .wrapper {{ max-width: 700px; margin: 30px auto; background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 2px 16px rgba(0,0,0,.10); }}
  .header {{ background: #1A3C5E; color: white; padding: 32px 36px; }}
  .header h1 {{ margin: 0 0 4px; font-size: 26px; letter-spacing: -.02em; }}
  .header p {{ margin: 0; font-size: 13px; color: rgba(255,255,255,.7); }}
  .inv-meta {{ display: flex; justify-content: space-between; padding: 24px 36px; background: #F7F4EF; border-bottom: 1px solid #E5E0D8; }}
  .inv-meta div {{ font-size: 13px; }}
  .inv-meta .label {{ color: #888; font-size: 11px; text-transform: uppercase; letter-spacing: .06em; margin-bottom: 3px; }}
  .inv-meta .value {{ font-weight: 600; color: #1A3C5E; font-size: 15px; }}
  .body {{ padding: 28px 36px; }}
  .to-from {{ display: flex; gap: 40px; margin-bottom: 28px; }}
  .to-from div {{ flex: 1; }}
  .to-from .section-lbl {{ font-size: 10px; font-weight: 700; color: #888; text-transform: uppercase; letter-spacing: .08em; border-bottom: 2px solid #E8612C; padding-bottom: 6px; margin-bottom: 10px; }}
  .to-from p {{ margin: 3px 0; font-size: 13px; line-height: 1.6; color: #333; }}
  .to-from strong {{ color: #0F1923; font-size: 15px; }}
  table {{ width: 100%; border-collapse: collapse; margin: 20px 0; font-size: 13px; }}
  th {{ background: #1A3C5E; color: white; padding: 10px 14px; text-align: left; font-size: 11px; text-transform: uppercase; letter-spacing: .05em; }}
  td {{ padding: 12px 14px; border-bottom: 1px solid #F0EDE8; }}
  tr:last-child td {{ border: none; }}
  .subtotal-row td {{ font-weight: 600; background: #F7F4EF; }}
  .total-row td {{ font-weight: 700; font-size: 16px; background: #1A3C5E; color: white; border-radius: 0; }}
  .payment-box {{ background: #E8F6F0; border: 1px solid #A8DDD8; border-radius: 10px; padding: 18px 22px; margin: 20px 0; }}
  .payment-box h3 {{ margin: 0 0 12px; color: #1D8A5F; font-size: 14px; }}
  .payment-box p {{ margin: 4px 0; font-size: 13px; color: #333; }}
  .payment-box .upi {{ font-size: 18px; font-weight: 700; color: #1D8A5F; letter-spacing: .03em; }}
  .due-badge {{ display: inline-block; background: #E8612C; color: white; padding: 5px 14px; border-radius: 20px; font-size: 12px; font-weight: 600; }}
  .footer {{ background: #F7F4EF; padding: 20px 36px; text-align: center; font-size: 11px; color: #999; border-top: 1px solid #E5E0D8; }}
  .footer strong {{ color: #1A3C5E; }}
</style>
</head>
<body>
<div class="wrapper">

  <!-- HEADER -->
  <div class="header">
    <h1>🏭 {BUSINESS_NAME}</h1>
    <p>{BUSINESS_ADDRESS}</p>
    <p>GSTIN: {BUSINESS_GSTIN} &nbsp;|&nbsp; PAN: {BUSINESS_PAN} &nbsp;|&nbsp; {BUSINESS_EMAIL}</p>
  </div>

  <!-- META -->
  <div class="inv-meta">
    <div>
      <div class="label">Invoice No.</div>
      <div class="value">{inv_id}</div>
    </div>
    <div>
      <div class="label">Invoice Date</div>
      <div class="value">{inv_date}</div>
    </div>
    <div>
      <div class="label">Billing Period</div>
      <div class="value">{month_name}</div>
    </div>
    <div>
      <div class="label">Due Date</div>
      <div class="value"><span class="due-badge">📅 {due_date}</span></div>
    </div>
  </div>

  <div class="body">

    <!-- TO / FROM -->
    <div class="to-from">
      <div>
        <div class="section-lbl">Invoice To</div>
        <p><strong>{row.get("Tenant_Name", "")}</strong></p>
        <p>Contact: {row.get("Contact_Person", "—")}</p>
        <p>{row.get("Warehouse_Location", "")} — {row.get("Warehouse_State", "")}</p>
        <p>📧 {row.get("Tenant_Email", "—")}</p>
        <p>📱 +91-{row.get("Tenant_Phone", "—")}</p>
      </div>
      <div>
        <div class="section-lbl">Property Owner</div>
        <p><strong>{row.get("Owner_Name", "")}</strong></p>
        <p>WareHub Family Properties</p>
        <p>📧 {row.get("Owner_Email", BUSINESS_EMAIL)}</p>
        <p>📱 +91-{row.get("Owner_Phone", BUSINESS_PHONE)}</p>
      </div>
    </div>

    <!-- DETAILS TABLE -->
    <table>
      <thead>
        <tr>
          <th>Description</th>
          <th>Warehouse</th>
          <th>Period</th>
          <th style="text-align:right">Amount (₹)</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td>Warehouse Rental Charges</td>
          <td>{row.get("WH_ID", "")} — {row.get("Warehouse_Type", "")} ({row.get("Warehouse_Size", "")})</td>
          <td>{month_name}</td>
          <td style="text-align:right; font-weight:600">₹{base_rent:,.0f}</td>
        </tr>
        <tr class="subtotal-row">
          <td colspan="3" style="text-align:right; color:#555">Sub-Total</td>
          <td style="text-align:right">₹{base_rent:,.0f}</td>
        </tr>
        <tr class="subtotal-row">
          <td colspan="3" style="text-align:right; color:#555">GST @ 18%</td>
          <td style="text-align:right">₹{gst_amt:,.0f}</td>
        </tr>
        <tr class="total-row">
          <td colspan="3" style="text-align:right">TOTAL AMOUNT DUE</td>
          <td style="text-align:right">₹{total:,.0f}</td>
        </tr>
      </tbody>
    </table>

    <!-- PAYMENT DETAILS -->
    <div class="payment-box">
      <h3>💳 Payment Details</h3>
      <p><strong>Bank:</strong> {BANK_NAME} &nbsp;|&nbsp; <strong>A/C:</strong> {BANK_ACCOUNT} &nbsp;|&nbsp; <strong>IFSC:</strong> {BANK_IFSC}</p>
      <p><strong>Branch:</strong> {BANK_BRANCH}</p>
      <p style="margin-top:10px"><strong>UPI / Instant Payment:</strong></p>
      <p class="upi">📲 {UPI_ID}</p>
    </div>

    <p style="font-size:12px;color:#888;margin-top:16px">
      ⚠️ Please pay by <strong>{due_date}</strong> to avoid late payment charges. 
      Payments received after the due date may attract a penalty of 2% per month.
      For queries, contact: <strong>{BUSINESS_EMAIL}</strong> | <strong>{BUSINESS_PHONE}</strong>
    </p>

  </div>

  <div class="footer">
    <strong>{BUSINESS_NAME}</strong> — This is a computer-generated invoice and does not require a physical signature.<br>
    Thank you for your continued association with us.
  </div>
</div>
</body>
</html>
"""
    return html


def generate_invoice_text(row: dict) -> str:
    """Plain-text invoice for WhatsApp messages."""
    base_rent = float(row.get("Monthly_Rent_INR", 0))
    gst_amt   = float(row.get("GST_18pct_INR",    0))
    total     = float(row.get("Total_Invoice_INR", base_rent + gst_amt))
    inv_date  = row.get("Invoice_Date", datetime.today().strftime("%Y-%m-%d"))
    due_date  = row.get("Due_Date",     (datetime.today() + timedelta(days=10)).strftime("%Y-%m-%d"))
    month_name = row.get("Month_Name",  datetime.today().strftime("%b-%Y"))

    return f"""🏭 *{BUSINESS_NAME}*
📄 *RENTAL INVOICE — {month_name}*
─────────────────────────────
*Invoice No:*  {row.get('Row_ID', 'INV-001')}
*Invoice Date:* {inv_date}
*Due Date:*     {due_date}
─────────────────────────────
*Tenant:*   {row.get('Tenant_Name', '')}
*Attn:*     {row.get('Contact_Person', '')}
*Property:* {row.get('WH_ID', '')} — {row.get('Warehouse_Type', '')}
*Location:* {row.get('Warehouse_Location', '')}
─────────────────────────────
*Base Rent:*    ₹{base_rent:,.0f}
*GST (18%):*    ₹{gst_amt:,.0f}
*TOTAL DUE:*    ₹{total:,.0f}
─────────────────────────────
💳 *Payment:*
UPI: {UPI_ID}
Bank: {BANK_NAME}
A/C: {BANK_ACCOUNT}
IFSC: {BANK_IFSC}

Please pay by *{due_date}* to avoid late charges.
Queries: {BUSINESS_EMAIL} | {BUSINESS_PHONE}

_{BUSINESS_NAME}_"""


# ════════════════════════════════════════════════════════════════════════════
# REMINDER GENERATOR
# ════════════════════════════════════════════════════════════════════════════

def generate_reminder_html(row: dict, days_overdue: int = 0) -> str:
    """Generate an overdue reminder HTML email."""
    base_rent  = float(row.get("Monthly_Rent_INR", 0))
    gst_amt    = float(row.get("GST_18pct_INR",    0))
    total      = float(row.get("Total_Invoice_INR", base_rent + gst_amt))
    balance    = float(row.get("Balance_Due_INR",   total))
    due_date   = row.get("Due_Date", "")
    month_name = row.get("Month_Name", datetime.today().strftime("%b-%Y"))
    inv_id     = row.get("Row_ID", "INV-001")

    urgency_color  = "#C0392B" if days_overdue > 15 else "#D97706"
    urgency_label  = "URGENT REMINDER" if days_overdue > 15 else "PAYMENT REMINDER"
    urgency_badge  = f"{'🔴' if days_overdue > 15 else '🟡'} {days_overdue} days overdue"

    html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
  body {{ font-family: Arial, sans-serif; color: #1A1A1A; margin: 0; padding: 0; background: #f5f5f5; }}
  .wrapper {{ max-width: 700px; margin: 30px auto; background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 2px 16px rgba(0,0,0,.10); }}
  .header {{ background: {urgency_color}; color: white; padding: 28px 36px; }}
  .header h1 {{ margin: 0 0 4px; font-size: 22px; }}
  .header p {{ margin: 0; font-size: 13px; opacity: .85; }}
  .overdue-banner {{ background: #FFF3CD; border-left: 5px solid {urgency_color}; padding: 16px 24px; font-size: 14px; color: #856404; }}
  .body {{ padding: 28px 36px; }}
  .amount-box {{ background: {urgency_color}; color: white; border-radius: 10px; padding: 20px 24px; margin: 20px 0; text-align: center; }}
  .amount-box .label {{ font-size: 12px; opacity: .8; text-transform: uppercase; letter-spacing: .06em; }}
  .amount-box .amount {{ font-size: 36px; font-weight: 700; margin: 8px 0; }}
  .payment-box {{ background: #E8F6F0; border: 1px solid #A8DDD8; border-radius: 10px; padding: 18px 22px; margin: 20px 0; }}
  .payment-box h3 {{ margin: 0 0 12px; color: #1D8A5F; font-size: 14px; }}
  .payment-box p {{ margin: 4px 0; font-size: 13px; }}
  .payment-box .upi {{ font-size: 18px; font-weight: 700; color: #1D8A5F; }}
  .warning {{ background: #FCEAEA; border: 1px solid #F5C4C4; border-radius: 8px; padding: 14px 18px; font-size: 12px; color: #C0392B; margin: 16px 0; }}
  .footer {{ background: #F7F4EF; padding: 18px 36px; text-align: center; font-size: 11px; color: #999; border-top: 1px solid #E5E0D8; }}
</style>
</head>
<body>
<div class="wrapper">
  <div class="header">
    <h1>⚠️ {urgency_label}</h1>
    <p>{BUSINESS_NAME} — Rental Invoice Outstanding</p>
  </div>

  <div class="overdue-banner">
    📋 Invoice <strong>{inv_id}</strong> for <strong>{month_name}</strong> is <strong>{urgency_badge}</strong>. 
    Original due date: <strong>{due_date}</strong>
  </div>

  <div class="body">
    <p>Dear <strong>{row.get('Contact_Person', row.get('Tenant_Name', ''))}</strong>,</p>
    <p>This is a reminder that your warehouse rental payment for <strong>{month_name}</strong> 
    remains outstanding. Kindly arrange payment at the earliest to avoid further penalties.</p>

    <div class="amount-box">
      <div class="label">Outstanding Balance Due</div>
      <div class="amount">₹{balance:,.0f}</div>
      <div style="font-size:13px;opacity:.85">Invoice: {inv_id} &nbsp;|&nbsp; Period: {month_name}</div>
    </div>

    <table style="width:100%;font-size:13px;border-collapse:collapse;margin:16px 0">
      <tr style="background:#F7F4EF"><td style="padding:8px 12px;color:#888">Tenant</td><td style="padding:8px 12px;font-weight:600">{row.get('Tenant_Name','')}</td></tr>
      <tr><td style="padding:8px 12px;color:#888">Property</td><td style="padding:8px 12px">{row.get('WH_ID','')} — {row.get('Warehouse_Type','')}, {row.get('Warehouse_Location','')}</td></tr>
      <tr style="background:#F7F4EF"><td style="padding:8px 12px;color:#888">Base Rent</td><td style="padding:8px 12px">₹{base_rent:,.0f}</td></tr>
      <tr><td style="padding:8px 12px;color:#888">GST (18%)</td><td style="padding:8px 12px">₹{gst_amt:,.0f}</td></tr>
      <tr style="background:#F7F4EF;font-weight:700"><td style="padding:8px 12px">Total Due</td><td style="padding:8px 12px;color:{urgency_color}">₹{balance:,.0f}</td></tr>
    </table>

    <div class="payment-box">
      <h3>💳 Pay Now</h3>
      <p><strong>UPI (Instant):</strong> <span class="upi">{UPI_ID}</span></p>
      <p><strong>Bank:</strong> {BANK_NAME} &nbsp;|&nbsp; A/C: {BANK_ACCOUNT} &nbsp;|&nbsp; IFSC: {BANK_IFSC}</p>
    </div>

    <div class="warning">
      ⚠️ <strong>Please Note:</strong> Continued non-payment may result in a late fee of 2% per month 
      on outstanding amounts and may affect your lease renewal. If payment has already been made, 
      please share the UTR/transaction reference to {BUSINESS_EMAIL}.
    </div>

    <p style="font-size:13px">For any queries or payment confirmation:<br>
    📧 {BUSINESS_EMAIL} &nbsp;|&nbsp; 📱 {BUSINESS_PHONE}</p>
  </div>

  <div class="footer">
    <strong>{BUSINESS_NAME}</strong> — {BUSINESS_ADDRESS}
  </div>
</div>
</body>
</html>
"""
    return html


def generate_reminder_text(row: dict, days_overdue: int = 0) -> str:
    """Plain-text reminder for WhatsApp."""
    base_rent  = float(row.get("Monthly_Rent_INR", 0))
    gst_amt    = float(row.get("GST_18pct_INR",    0))
    total      = float(row.get("Total_Invoice_INR", base_rent + gst_amt))
    balance    = float(row.get("Balance_Due_INR",   total))
    month_name = row.get("Month_Name", "")
    due_date   = row.get("Due_Date", "")

    emoji = "🔴" if days_overdue > 15 else "🟡"
    label = "URGENT REMINDER" if days_overdue > 15 else "PAYMENT REMINDER"

    return f"""{emoji} *{label}*
🏭 *{BUSINESS_NAME}*
─────────────────────────────
Dear *{row.get('Contact_Person', row.get('Tenant_Name', ''))}*,

Your warehouse rental payment for *{month_name}* is outstanding.

*Invoice:* {row.get('Row_ID', 'INV-001')}
*Original Due Date:* {due_date}
*Days Overdue:* {days_overdue} days
─────────────────────────────
*OUTSTANDING AMOUNT: ₹{balance:,.0f}*

  Base Rent:   ₹{base_rent:,.0f}
  GST (18%):   ₹{gst_amt:,.0f}
─────────────────────────────
💳 *Pay Now:*
UPI: {UPI_ID}
Bank: {BANK_NAME}
A/C: {BANK_ACCOUNT} | IFSC: {BANK_IFSC}

Please confirm payment to:
📧 {BUSINESS_EMAIL}
📱 {BUSINESS_PHONE}

_Delayed payment may attract 2% monthly penalty._
_{BUSINESS_NAME}_"""


# ════════════════════════════════════════════════════════════════════════════
# EMAIL SENDER (Gmail SMTP)
# ════════════════════════════════════════════════════════════════════════════

# NOTE: send_email_gmail and send_whatsapp_ultramsg are imported from settings.py
# to avoid duplicating credential logic. All sending goes through settings.py.


# ════════════════════════════════════════════════════════════════════════════
# WHATSAPP DEEP LINK
# ════════════════════════════════════════════════════════════════════════════

def whatsapp_url(phone: str, message: str) -> str:
    """
    Generate a wa.me deep link.
    Opens WhatsApp Web / WhatsApp app with message pre-filled.
    Works without any API or cost.
    """
    import urllib.parse
    phone_clean = re.sub(r"\D", "", str(phone))
    if not phone_clean.startswith("91"):
        phone_clean = "91" + phone_clean
    encoded = urllib.parse.quote(message)
    return f"https://wa.me/{phone_clean}?text={encoded}"


# ════════════════════════════════════════════════════════════════════════════
# NOTIFICATION LOG (session state)
# ════════════════════════════════════════════════════════════════════════════

def init_notification_log():
    if "notification_log" not in st.session_state:
        st.session_state.notification_log = []


def log_notification(action: str, tenant: str, channel: str, status: str, month: str):
    init_notification_log()
    st.session_state.notification_log.append({
        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Action":    action,
        "Tenant":    tenant,
        "Channel":   channel,
        "Month":     month,
        "Status":    status,
    })


def get_notification_log() -> pd.DataFrame:
    init_notification_log()
    if st.session_state.notification_log:
        return pd.DataFrame(st.session_state.notification_log)
    return pd.DataFrame(columns=["Timestamp", "Action", "Tenant", "Channel", "Month", "Status"])


# ════════════════════════════════════════════════════════════════════════════
# STREAMLIT NOTIFICATION PAGE RENDERER
# ════════════════════════════════════════════════════════════════════════════

def render_notification_page(df: pd.DataFrame):
    """Full Streamlit page for invoice and reminder management."""

    st.markdown(
        '<div style="font-family:DM Serif Display,serif;font-size:22px;color:#0F1923;'
        'letter-spacing:-.02em;margin-bottom:4px">📨 Invoice & Reminder Centre</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div style="font-size:13px;color:#64748B;margin-bottom:20px">'
        'Generate invoices, send payment reminders via Email and WhatsApp</div>',
        unsafe_allow_html=True,
    )

    # ── TABS ──────────────────────────────────────────────────────────────────
    tab1, tab2, tab3, tab4 = st.tabs([
        "📋 Generate Invoices",
        "⚠️ Reminders (Overdue)",
        "✉️ Email Setup (Gmail)",
        "📜 Notification Log",
    ])

    # ════════════════════════
    # TAB 1 — INVOICES
    # ════════════════════════
    with tab1:
        st.markdown("#### Select Month to Generate Invoices")

        months = sorted(df["Month_Name"].dropna().unique().tolist(), reverse=True)
        sel_month = st.selectbox("Billing Month", months, key="inv_month")

        month_df = df[df["Month_Name"] == sel_month].copy()
        tenants_in_month = month_df.drop_duplicates(subset=["Tenant_ID"])

        st.info(
            f"📦 **{len(tenants_in_month)}** invoices to generate for **{sel_month}** "
            f"| Total Invoice Value: **{inr_fmt(month_df['Total_Invoice_INR'].sum())}**"
        )

        # Invoice preview
        st.markdown("#### Invoice Preview")
        sel_tenant = st.selectbox(
            "Preview invoice for tenant",
            tenants_in_month["Tenant_Name"].tolist(),
            key="inv_preview_tenant",
        )
        preview_row = tenants_in_month[tenants_in_month["Tenant_Name"] == sel_tenant].iloc[0].to_dict()

        col_prev, col_text = st.columns(2)
        with col_prev:
            st.markdown("**HTML Invoice (Email)**")
            html_inv = generate_invoice_html(preview_row)
            components.html(html_inv, height=680, scrolling=True)

        with col_text:
            st.markdown("**WhatsApp Message**")
            wa_text = generate_invoice_text(preview_row)
            st.text_area("Message Preview", wa_text, height=380, key="wa_inv_preview")

            phone = str(preview_row.get("Tenant_Phone", ""))
            wa_link = whatsapp_url(phone, wa_text)
            st.markdown(
                f'<a href="{wa_link}" target="_blank">'
                f'<button style="background:#25D366;color:white;border:none;padding:10px 20px;'
                f'border-radius:8px;font-size:14px;cursor:pointer;width:100%;margin-top:8px">'
                f'📱 Open in WhatsApp Web</button></a>',
                unsafe_allow_html=True,
            )
            log_notification("Invoice", sel_tenant, "WhatsApp Link", "Link Generated", sel_month)

        # Bulk send section
        st.markdown("---")
        st.markdown("#### Bulk Invoice Actions")

        bulk_col1, bulk_col2 = st.columns(2)
        with bulk_col1:
            st.markdown("**Send All Invoices via WhatsApp**")
            from settings import is_whatsapp_configured, send_whatsapp_ultramsg
            if is_whatsapp_configured():
                if st.button("📤 Send All via WhatsApp (Auto)", key="bulk_wa_inv_auto"):
                    prog = st.progress(0)
                    ok = 0
                    for i, (_, row) in enumerate(tenants_in_month.iterrows()):
                        rdict  = row.to_dict()
                        phone  = str(rdict.get("Tenant_Phone", ""))
                        msg    = generate_invoice_text(rdict)
                        result = send_whatsapp_ultramsg(phone, msg)
                        if result["success"]:
                            ok += 1
                        log_notification("Invoice", rdict.get("Tenant_Name",""), "WhatsApp",
                                         "Sent ✓" if result["success"] else "Failed", sel_month)
                        prog.progress((i + 1) / len(tenants_in_month))
                    st.success(f"✅ {ok}/{len(tenants_in_month)} WhatsApp messages sent.")
            else:
                st.caption("⚙️ Configure UltraMsg in Settings for auto-send, or use quick-send links below.")
                if st.button("📤 Generate All WhatsApp Links", key="bulk_wa_inv"):
                    for _, row in tenants_in_month.iterrows():
                        rdict   = row.to_dict()
                        phone   = str(rdict.get("Tenant_Phone", ""))
                        msg     = generate_invoice_text(rdict)
                        wa_link = whatsapp_url(phone, msg)
                        tenant  = rdict.get("Tenant_Name", "")
                        col_a, col_b = st.columns([2, 1])
                        with col_a:
                            st.write(f"**{tenant}** — {rdict.get('Tenant_Email','')}")
                        with col_b:
                            st.markdown(
                                f'<a href="{wa_link}" target="_blank">'
                                f'<button style="background:#25D366;color:white;border:none;'
                                f'padding:6px 14px;border-radius:6px;cursor:pointer;font-size:12px">'
                                f'WhatsApp ↗</button></a>',
                                unsafe_allow_html=True,
                            )
                        log_notification("Invoice", tenant, "WhatsApp Link", "Link Generated", sel_month)

        with bulk_col2:
            st.markdown("**Send All Invoices via Email (Gmail)**")
            st.caption("Configure Gmail in ⚙️ Settings first.")
            if st.button("📧 Send All via Email", key="bulk_email_inv"):
                from settings import send_email_gmail, is_gmail_configured
                if not is_gmail_configured():
                    st.error("⚠️ Gmail not configured — go to ⚙️ Settings page first.")
                else:
                    results = []
                    prog = st.progress(0)
                    for i, (_, row) in enumerate(tenants_in_month.iterrows()):
                        rdict     = row.to_dict()
                        html_body = generate_invoice_html(rdict)
                        subject   = (
                            f"Rental Invoice — {sel_month} | "
                            f"{rdict.get('WH_ID','')} | "
                            f"₹{rdict.get('Total_Invoice_INR',0):,.0f} Due"
                        )
                        result = send_email_gmail(
                            rdict.get("Tenant_Email", ""),
                            subject, html_body,
                            cc_email=rdict.get("Owner_Email", ""),
                        )
                        results.append((rdict.get("Tenant_Name", ""), result))
                        log_notification(
                            "Invoice", rdict.get("Tenant_Name", ""), "Email",
                            "Sent ✓" if result["success"] else f"Failed: {result['message']}",
                            sel_month,
                        )
                        prog.progress((i + 1) / len(tenants_in_month))

                    sent_ok = sum(1 for _, r in results if r["success"])
                    st.success(f"✅ {sent_ok}/{len(results)} invoices sent successfully.")
                    for t, r in results:
                        if not r["success"]:
                            st.warning(f"⚠️ {t}: {r['message']}")

    # ════════════════════════
    # TAB 2 — REMINDERS
    # ════════════════════════
    with tab2:
        st.markdown("#### Tenants with Outstanding Payments")

        today = pd.Timestamp.today()
        overdue = df[df["Balance_Due_INR"] > 0].copy()
        overdue["Due_Date_dt"] = pd.to_datetime(overdue["Due_Date"], errors="coerce")
        overdue["Days_Overdue_Calc"] = (today - overdue["Due_Date_dt"]).dt.days.clip(lower=0)

        # Deduplicate to one row per tenant (worst overdue)
        overdue_latest = (
            overdue.sort_values("Days_Overdue_Calc", ascending=False)
            .drop_duplicates(subset=["Tenant_ID"])
            .reset_index(drop=True)
        )

        if overdue_latest.empty:
            st.success("🎉 No outstanding payments — all tenants are up to date!")
        else:
            st.error(
                f"⚠️ **{len(overdue_latest)} tenants** have outstanding balances totalling "
                f"**{inr_fmt(overdue_latest['Balance_Due_INR'].sum())}**"
            )

            # Summary table
            disp = overdue_latest[[
                "Tenant_Name", "Contact_Person", "Tenant_Email", "Tenant_Phone",
                "Month_Name", "Balance_Due_INR", "Days_Overdue_Calc", "Payment_Behavior"
            ]].copy()
            disp["Balance_Due_INR"] = disp["Balance_Due_INR"].apply(inr_fmt)
            disp.columns = [
                "Tenant", "Contact", "Email", "Phone",
                "Month", "Balance Due", "Days Overdue", "Behaviour"
            ]
            st.dataframe(disp, use_container_width=True, hide_index=True)

            # Per-tenant reminder
            st.markdown("---")
            st.markdown("#### Send Reminders")

            rem_tenant = st.selectbox(
                "Select tenant",
                overdue_latest["Tenant_Name"].tolist(),
                key="rem_tenant_sel",
            )
            rem_row = overdue_latest[overdue_latest["Tenant_Name"] == rem_tenant].iloc[0].to_dict()
            days_ov = int(rem_row.get("Days_Overdue_Calc", 0))

            rc1, rc2 = st.columns(2)
            with rc1:
                st.markdown("**Reminder Email Preview**")
                html_rem = generate_reminder_html(rem_row, days_overdue=days_ov)
                components.html(html_rem, height=620, scrolling=True)

            with rc2:
                st.markdown("**WhatsApp Reminder Message**")
                wa_rem_text = generate_reminder_text(rem_row, days_overdue=days_ov)
                st.text_area("Message", wa_rem_text, height=340, key="wa_rem_prev")

                phone   = str(rem_row.get("Tenant_Phone", ""))
                wa_link = whatsapp_url(phone, wa_rem_text)
                st.markdown(
                    f'<a href="{wa_link}" target="_blank">'
                    f'<button style="background:#25D366;color:white;border:none;padding:10px 20px;'
                    f'border-radius:8px;font-size:14px;cursor:pointer;width:100%;margin-top:8px">'
                    f'📱 Send WhatsApp Reminder</button></a>',
                    unsafe_allow_html=True,
                )
                log_notification("Reminder", rem_tenant, "WhatsApp Link", "Link Generated",
                                 str(rem_row.get("Month_Name", "")))

                st.markdown("---")
                st.markdown("**Send Reminder via WhatsApp**")
                from settings import is_whatsapp_configured, send_whatsapp_ultramsg
                phone_rem = str(rem_row.get("Tenant_Phone", ""))
                if is_whatsapp_configured():
                    if st.button("📱 Send WhatsApp Reminder (Auto)", key="send_wa_rem_auto"):
                        with st.spinner("Sending..."):
                            result_wa = send_whatsapp_ultramsg(phone_rem, wa_rem_text)
                        if result_wa["success"]:
                            st.success(f"✅ {result_wa['message']}")
                            log_notification("Reminder", rem_tenant, "WhatsApp", "Sent ✓",
                                             str(rem_row.get("Month_Name","")))
                        else:
                            st.error(f"❌ {result_wa['message']}")
                else:
                    wa_link = whatsapp_url(phone_rem, wa_rem_text)
                    st.markdown(
                        f'<a href="{wa_link}" target="_blank">'
                        f'<button style="background:#25D366;color:white;border:none;padding:10px 20px;'
                        f'border-radius:8px;font-size:14px;cursor:pointer;width:100%;margin-top:8px">'
                        f'📱 Open in WhatsApp Web</button></a>',
                        unsafe_allow_html=True,
                    )
                    log_notification("Reminder", rem_tenant, "WhatsApp Link", "Link Generated",
                                     str(rem_row.get("Month_Name", "")))

                st.markdown("---")
                st.markdown("**Send Reminder via Email**")
                from settings import send_email_gmail, is_gmail_configured
                if st.button("📧 Send Reminder Email", key="send_rem_email"):
                    if not is_gmail_configured():
                        st.error("Configure Gmail in ⚙️ Settings first.")
                    else:
                        subject = (
                            f"{'⚠️ URGENT: ' if days_ov > 15 else ''}Payment Reminder — "
                            f"{rem_row.get('Month_Name','')} | "
                            f"{inr_fmt(rem_row.get('Balance_Due_INR', 0))} Outstanding"
                        )
                        result = send_email_gmail(
                            rem_row.get("Tenant_Email", ""),
                            subject, html_rem,
                            cc_email=rem_row.get("Owner_Email", ""),
                        )
                        if result["success"]:
                            st.success(f"✅ Reminder sent to {rem_row.get('Tenant_Email','')}")
                            log_notification("Reminder", rem_tenant, "Email", "Sent ✓",
                                             str(rem_row.get("Month_Name","")))
                        else:
                            st.error(f"❌ Failed: {result['message']}")

            # Bulk reminders
            st.markdown("---")
            st.markdown("#### Bulk Reminders — All Overdue Tenants")
            bulk_r1, bulk_r2 = st.columns(2)

            with bulk_r1:
                from settings import is_whatsapp_configured, send_whatsapp_ultramsg
                if is_whatsapp_configured():
                    if st.button("📱 Send All WhatsApp Reminders (Auto)", key="bulk_wa_rem_auto"):
                        prog = st.progress(0)
                        ok = 0
                        for i, (_, row) in enumerate(overdue_latest.iterrows()):
                            rdict    = row.to_dict()
                            days_ov2 = int(rdict.get("Days_Overdue_Calc", 0))
                            msg2     = generate_reminder_text(rdict, days_overdue=days_ov2)
                            result   = send_whatsapp_ultramsg(str(rdict.get("Tenant_Phone","")), msg2)
                            if result["success"]: ok += 1
                            log_notification("Reminder", rdict.get("Tenant_Name",""), "WhatsApp",
                                             "Sent ✓" if result["success"] else "Failed",
                                             str(rdict.get("Month_Name","")))
                            prog.progress((i + 1) / len(overdue_latest))
                        st.success(f"✅ {ok}/{len(overdue_latest)} WhatsApp reminders sent.")
                else:
                    if st.button("📱 Generate All WhatsApp Reminder Links", key="bulk_wa_rem"):
                        for _, row in overdue_latest.iterrows():
                            rdict    = row.to_dict()
                            days_ov2 = int(rdict.get("Days_Overdue_Calc", 0))
                            phone2   = str(rdict.get("Tenant_Phone", ""))
                            msg2     = generate_reminder_text(rdict, days_overdue=days_ov2)
                            wa_link2 = whatsapp_url(phone2, msg2)
                            t_name   = rdict.get("Tenant_Name", "")
                            ca, cb   = st.columns([3, 1])
                            with ca:
                                st.write(f"**{t_name}** — {days_ov2}d overdue — {inr_fmt(rdict.get('Balance_Due_INR',0))}")
                            with cb:
                                st.markdown(
                                    f'<a href="{wa_link2}" target="_blank">'
                                    f'<button style="background:#25D366;color:white;border:none;'
                                    f'padding:6px 14px;border-radius:6px;cursor:pointer;font-size:12px">'
                                    f'WhatsApp ↗</button></a>',
                                    unsafe_allow_html=True,
                                )
                            log_notification("Reminder", t_name, "WhatsApp Link", "Link Generated",
                                             str(rdict.get("Month_Name","")))

            with bulk_r2:
                if st.button("📧 Send All Reminder Emails", key="bulk_email_rem"):
                    from settings import send_email_gmail, is_gmail_configured
                    if not is_gmail_configured():
                        st.error("Configure Gmail in ⚙️ Settings first.")
                    else:
                        prog = st.progress(0)
                        ok_count = 0
                        for i, (_, row) in enumerate(overdue_latest.iterrows()):
                            rdict    = row.to_dict()
                            days_ov2 = int(rdict.get("Days_Overdue_Calc", 0))
                            subject  = (
                                f"{'⚠️ URGENT: ' if days_ov2 > 15 else ''}Payment Reminder — "
                                f"{rdict.get('Month_Name','')} | "
                                f"{inr_fmt(rdict.get('Balance_Due_INR',0))} Outstanding"
                            )
                            html_body = generate_reminder_html(rdict, days_overdue=days_ov2)
                            result = send_email_gmail(
                                rdict.get("Tenant_Email", ""),
                                subject, html_body,
                                cc_email=rdict.get("Owner_Email", ""),
                            )
                            if result["success"]:
                                ok_count += 1
                            log_notification(
                                "Reminder", rdict.get("Tenant_Name",""), "Email",
                                "Sent ✓" if result["success"] else "Failed",
                                str(rdict.get("Month_Name","")),
                            )
                            prog.progress((i + 1) / len(overdue_latest))
                        st.success(f"✅ {ok_count}/{len(overdue_latest)} reminder emails sent.")

    # ════════════════════════
    # TAB 3 — EMAIL SETUP
    # ════════════════════════
    with tab3:
        from settings import get_channel_status
        status = get_channel_status()
        st.markdown(
            '<div style="background:#EBF2FA;border:1px solid #BDD5EE;border-radius:12px;'
            'padding:20px 24px;font-size:14px;color:#1A3C5E;margin-bottom:16px">'
            '⚙️ <strong>Email and WhatsApp credentials are managed in the Settings page.</strong><br><br>'
            'Go to <strong>⚙️ Settings</strong> in the sidebar to:<br>'
            '&nbsp;&nbsp;✉️ Connect your Gmail account (App Password setup guide included)<br>'
            '&nbsp;&nbsp;📱 Connect your WhatsApp number (+91 9571789145) via UltraMsg QR scan<br>'
            '&nbsp;&nbsp;🧪 Test both connections before sending live messages'
            '</div>',
            unsafe_allow_html=True,
        )
        ec1, ec2 = st.columns(2)
        with ec1:
            bg = "#E8F6F0" if status["email_ok"] else "#FDF6E3"
            fg = "#1D8A5F" if status["email_ok"] else "#D97706"
            st.markdown(
                f'<div style="background:{bg};border-radius:10px;padding:16px;font-size:13px;color:{fg}">'
                f'✉️ <strong>Gmail Status</strong><br>{status["email"]}<br>'
                f'<span style="font-size:11px">{st.session_state.get("gmail_user","Not configured")}</span>'
                f'</div>', unsafe_allow_html=True,
            )
        with ec2:
            bg = "#E8F6F0" if status["whatsapp_ok"] else "#FDF6E3"
            fg = "#1D8A5F" if status["whatsapp_ok"] else "#D97706"
            st.markdown(
                f'<div style="background:{bg};border-radius:10px;padding:16px;font-size:13px;color:{fg}">'
                f'📱 <strong>WhatsApp Status</strong><br>{status["whatsapp"]}<br>'
                f'<span style="font-size:11px">+{st.session_state.get("sender_phone","919571789145")}</span>'
                f'</div>', unsafe_allow_html=True,
            )

    # ════════════════════════
    # TAB 4 — LOG
    # ════════════════════════
    with tab4:
        st.markdown("#### Notification Activity Log")
        log_df = get_notification_log()

        if log_df.empty:
            st.info("No notifications sent yet in this session. Send invoices or reminders to see logs here.")
        else:
            sent    = len(log_df[log_df["Status"].str.contains("✓", na=False)])
            failed  = len(log_df[log_df["Status"].str.contains("Failed", na=False)])
            links   = len(log_df[log_df["Channel"] == "WhatsApp Link"])
            lc1, lc2, lc3 = st.columns(3)
            lc1.metric("Emails Sent", sent)
            lc2.metric("WhatsApp Links", links)
            lc3.metric("Failures", failed, delta=f"-{failed}" if failed else "0")
            st.dataframe(log_df, use_container_width=True, hide_index=True)

            # Download log
            import io
            buf = io.BytesIO()
            log_df.to_csv(buf, index=False)
            buf.seek(0)
            st.download_button("⬇️ Download Log CSV", buf, "notification_log.csv", "text/csv")
