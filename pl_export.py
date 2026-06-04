"""
pl_export.py — Annual P&L Report & Excel Export (Upgrade #8)

Generates a properly formatted Excel workbook with:
  1. Summary sheet — total revenue, GST collected, outstanding, by owner
  2. Monthly breakdown — month-by-month for the selected year
  3. Tenant ledger — full payment history per tenant
  4. GST statement — GST collected by quarter (for GSTR filing)

Uses openpyxl for proper Excel formatting.
"""

import streamlit as st
import pandas as pd
import io
from datetime import datetime
from data_manager import get_business, get_transaction_df
from utils import inr_fmt


def _fmt_inr_num(n):
    """Return plain number for Excel cells (not string)."""
    try:
        return round(float(n), 2)
    except Exception:
        return 0.0


def generate_pl_excel(df: pd.DataFrame, year: int) -> bytes:
    """Build a full P&L workbook for the given year. Returns bytes."""
    try:
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        from openpyxl.utils import get_column_letter
    except ImportError:
        st.error("openpyxl not installed. Run: pip install openpyxl")
        return b""

    biz = get_business()

    year_df = df[df["Month"].dt.year == year].copy()
    if year_df.empty:
        return b""

    wb = openpyxl.Workbook()

    # ── Styles ───────────────────────────────────────────────────────────────
    DARK_BLUE   = "0F1923"
    MID_BLUE    = "1A3C5E"
    LIGHT_BLUE  = "EBF2FA"
    GREEN_BG    = "E8F6F0"
    GREEN_FG    = "1D8A5F"
    RED_BG      = "FCEAEA"
    RED_FG      = "C0392B"
    AMBER_BG    = "FDF6E3"
    HEADER_FONT = Font(name="Calibri", bold=True, color="FFFFFF", size=11)
    TITLE_FONT  = Font(name="Calibri", bold=True, color=DARK_BLUE, size=14)
    SUB_FONT    = Font(name="Calibri", color="64748B", size=10)
    BODY_FONT   = Font(name="Calibri", size=10)
    NUM_FONT    = Font(name="Calibri", size=10)
    HEADER_FILL = PatternFill("solid", fgColor=MID_BLUE)
    ALT_FILL    = PatternFill("solid", fgColor="F7F4EF")
    CENTER      = Alignment(horizontal="center", vertical="center")
    RIGHT       = Alignment(horizontal="right", vertical="center")
    LEFT        = Alignment(horizontal="left",  vertical="center")
    THIN        = Border(
        bottom=Side(style="thin", color="E5E0D8"),
        top=Side(style="thin",    color="E5E0D8"),
    )
    INR_FMT = '#,##0.00'

    def _header_row(ws, row, values, widths=None):
        for col, val in enumerate(values, 1):
            cell = ws.cell(row=row, column=col, value=val)
            cell.font  = HEADER_FONT
            cell.fill  = HEADER_FILL
            cell.alignment = CENTER
            if widths and col <= len(widths):
                ws.column_dimensions[get_column_letter(col)].width = widths[col-1]

    def _data_row(ws, row, values, number_cols=None, alt=False):
        fill = ALT_FILL if alt else None
        for col, val in enumerate(values, 1):
            cell = ws.cell(row=row, column=col, value=val)
            cell.font = BODY_FONT
            cell.alignment = RIGHT if (number_cols and col in number_cols) else LEFT
            if number_cols and col in number_cols and isinstance(val, (int, float)):
                cell.number_format = INR_FMT
            if fill:
                cell.fill = fill

    # ════════════════════════════════════════════════════════════════════════
    # SHEET 1 — SUMMARY
    # ════════════════════════════════════════════════════════════════════════
    ws1 = wb.active
    ws1.title = "P&L Summary"

    # Title block
    ws1.merge_cells("A1:G1")
    t = ws1["A1"]
    t.value     = f"{biz.get('business_name','WareHub')} — Annual P&L Report {year}"
    t.font      = TITLE_FONT
    t.alignment = LEFT

    ws1.merge_cells("A2:G2")
    s = ws1["A2"]
    s.value     = f"Generated: {datetime.today().strftime('%d %b %Y')} | GSTIN: {biz.get('gstin','')} | PAN: {biz.get('pan','')}"
    s.font      = SUB_FONT
    s.alignment = LEFT

    ws1.append([])

    # KPI block
    total_inv = year_df["Total_Invoice_INR"].sum()
    total_col = year_df["Revenue_Collected_INR"].sum()
    total_out = year_df["Balance_Due_INR"].sum()
    total_gst = year_df["GST_18pct_INR"].sum()
    total_rent= year_df["Monthly_Rent_INR"].sum()
    pay_rate  = year_df["Is_Paid_Binary"].mean() * 100

    kpis = [
        ("Total Invoiced (incl. GST)",     _fmt_inr_num(total_inv)),
        ("Revenue Collected",               _fmt_inr_num(total_col)),
        ("Outstanding Balance",             _fmt_inr_num(total_out)),
        ("Base Rent Revenue",               _fmt_inr_num(total_rent)),
        ("GST Collected (18%)",             _fmt_inr_num(total_gst)),
        ("Payment Rate",                    f"{pay_rate:.1f}%"),
    ]

    ws1.append(["Key Metrics", ""])
    ws1["A4"].font = Font(name="Calibri", bold=True, color=MID_BLUE, size=11)

    for kp_label, kp_val in kpis:
        row_idx = ws1.max_row + 1
        ws1.append([kp_label, kp_val])
        ws1.cell(row=row_idx, column=1).font = BODY_FONT
        ws1.cell(row=row_idx, column=2).font = Font(name="Calibri", bold=True, size=10)
        if isinstance(kp_val, float):
            ws1.cell(row=row_idx, column=2).number_format = INR_FMT
            ws1.cell(row=row_idx, column=2).alignment = RIGHT

    ws1.append([])

    # Owner breakdown
    owner_tbl = (
        year_df.groupby("Owner_Name")
        .agg(
            Invoiced=("Total_Invoice_INR",      "sum"),
            Collected=("Revenue_Collected_INR", "sum"),
            Outstanding=("Balance_Due_INR",     "sum"),
            GST_Collected=("GST_18pct_INR",     "sum"),
            Transactions=("Row_ID",             "count"),
            Paid_Rate=("Is_Paid_Binary",        "mean"),
        )
        .reset_index()
    )

    header_row = ws1.max_row + 1
    ws1.append(["Owner-wise Breakdown"])
    ws1[f"A{header_row}"].font = Font(name="Calibri", bold=True, color=MID_BLUE, size=11)
    ws1.append([])

    col_headers = ["Owner", "Total Invoiced", "Collected", "Outstanding", "GST Collected", "Transactions", "Payment Rate"]
    _header_row(ws1, ws1.max_row + 1, col_headers, widths=[22, 16, 16, 16, 16, 14, 14])

    for idx, (_, row) in enumerate(owner_tbl.iterrows()):
        _data_row(ws1, ws1.max_row + 1, [
            row["Owner_Name"],
            _fmt_inr_num(row["Invoiced"]),
            _fmt_inr_num(row["Collected"]),
            _fmt_inr_num(row["Outstanding"]),
            _fmt_inr_num(row["GST_Collected"]),
            int(row["Transactions"]),
            f"{row['Paid_Rate']*100:.1f}%",
        ], number_cols={2,3,4,5}, alt=idx%2==1)

    ws1.row_dimensions[1].height = 22
    ws1.column_dimensions["A"].width = 28
    ws1.column_dimensions["B"].width = 18

    # ════════════════════════════════════════════════════════════════════════
    # SHEET 2 — MONTHLY BREAKDOWN
    # ════════════════════════════════════════════════════════════════════════
    ws2 = wb.create_sheet("Monthly Breakdown")
    ws2.merge_cells("A1:F1")
    ws2["A1"].value = f"Monthly Revenue Breakdown — {year}"
    ws2["A1"].font  = TITLE_FONT

    monthly_tbl = (
        year_df.groupby("Month_Name")
        .agg(
            Invoiced=("Total_Invoice_INR",       "sum"),
            Collected=("Revenue_Collected_INR",  "sum"),
            Outstanding=("Balance_Due_INR",      "sum"),
            GST=("GST_18pct_INR",               "sum"),
            Paid_Count=("Is_Paid_Binary",        "sum"),
            Total_Count=("Row_ID",               "count"),
        )
        .reset_index()
    )

    # Sort months
    month_order = [f"{m}-{year}" for m in ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]]
    monthly_tbl["_sort"] = monthly_tbl["Month_Name"].map(lambda x: month_order.index(x) if x in month_order else 99)
    monthly_tbl = monthly_tbl.sort_values("_sort").drop(columns=["_sort"])

    ws2.append([])
    _header_row(ws2, 3, ["Month", "Invoiced", "Collected", "Outstanding", "GST", "Payment Rate"],
                widths=[14, 16, 16, 16, 14, 14])

    for idx, (_, row) in enumerate(monthly_tbl.iterrows()):
        rate = f"{row['Paid_Count']/max(row['Total_Count'],1)*100:.1f}%"
        _data_row(ws2, ws2.max_row + 1, [
            row["Month_Name"],
            _fmt_inr_num(row["Invoiced"]),
            _fmt_inr_num(row["Collected"]),
            _fmt_inr_num(row["Outstanding"]),
            _fmt_inr_num(row["GST"]),
            rate,
        ], number_cols={2,3,4,5}, alt=idx%2==1)

    # Totals row
    last = ws2.max_row + 1
    ws2.append(["TOTAL",
                _fmt_inr_num(monthly_tbl["Invoiced"].sum()),
                _fmt_inr_num(monthly_tbl["Collected"].sum()),
                _fmt_inr_num(monthly_tbl["Outstanding"].sum()),
                _fmt_inr_num(monthly_tbl["GST"].sum()),
                ""])
    for col in range(1, 7):
        cell = ws2.cell(row=last, column=col)
        cell.font = Font(name="Calibri", bold=True, size=10)
        if col in {2,3,4,5}:
            cell.number_format = INR_FMT
            cell.alignment = RIGHT

    # ════════════════════════════════════════════════════════════════════════
    # SHEET 3 — TENANT LEDGER
    # ════════════════════════════════════════════════════════════════════════
    ws3 = wb.create_sheet("Tenant Ledger")
    ws3.merge_cells("A1:I1")
    ws3["A1"].value = f"Tenant Payment Ledger — {year}"
    ws3["A1"].font  = TITLE_FONT

    ws3.append([])
    _header_row(ws3, 3,
        ["Tenant", "Warehouse", "Month", "Rent", "GST", "Total Invoice", "Status", "Amount Paid", "Balance"],
        widths=[22, 20, 12, 12, 10, 14, 12, 14, 12])

    ledger_df = year_df.sort_values(["Tenant_Name", "Month"]).reset_index(drop=True)
    for idx, (_, row) in enumerate(ledger_df.iterrows()):
        _data_row(ws3, ws3.max_row + 1, [
            row["Tenant_Name"],
            row.get("Warehouse_Location",""),
            row["Month_Name"],
            _fmt_inr_num(row["Monthly_Rent_INR"]),
            _fmt_inr_num(row["GST_18pct_INR"]),
            _fmt_inr_num(row["Total_Invoice_INR"]),
            row["Payment_Status"],
            _fmt_inr_num(row["Amount_Paid_INR"]),
            _fmt_inr_num(row["Balance_Due_INR"]),
        ], number_cols={4,5,6,8,9}, alt=idx%2==1)

    # ════════════════════════════════════════════════════════════════════════
    # SHEET 4 — GST STATEMENT
    # ════════════════════════════════════════════════════════════════════════
    ws4 = wb.create_sheet("GST Statement")
    ws4.merge_cells("A1:F1")
    ws4["A1"].value = f"GST Collected — {year} (For GSTR Filing)"
    ws4["A1"].font  = TITLE_FONT

    ws4.merge_cells("A2:F2")
    ws4["A2"].value = f"GSTIN: {biz.get('gstin','')} | PAN: {biz.get('pan','')} | Rate: {biz.get('gst_rate',18)}%"
    ws4["A2"].font  = SUB_FONT

    gst_tbl = (
        year_df.groupby("Quarter")
        .agg(
            Base_Rent=("Monthly_Rent_INR",    "sum"),
            GST_Collected=("GST_18pct_INR",   "sum"),
            Transactions=("Row_ID",           "count"),
        )
        .reset_index()
    )

    ws4.append([])
    ws4.append([])
    _header_row(ws4, 5, ["Quarter", "Taxable Value (Base Rent)", "GST @ 18%", "Transactions"],
                widths=[14, 26, 18, 16])

    for idx, (_, row) in enumerate(gst_tbl.iterrows()):
        _data_row(ws4, ws4.max_row + 1, [
            row["Quarter"],
            _fmt_inr_num(row["Base_Rent"]),
            _fmt_inr_num(row["GST_Collected"]),
            int(row["Transactions"]),
        ], number_cols={2,3}, alt=idx%2==1)

    last = ws4.max_row + 1
    ws4.append(["ANNUAL TOTAL",
                _fmt_inr_num(gst_tbl["Base_Rent"].sum()),
                _fmt_inr_num(gst_tbl["GST_Collected"].sum()),
                int(gst_tbl["Transactions"].sum())])
    for col in range(1, 5):
        cell = ws4.cell(row=last, column=col)
        cell.font = Font(name="Calibri", bold=True, size=10)
        if col in {2,3}:
            cell.number_format = INR_FMT
            cell.alignment = RIGHT

    # ── Freeze panes on all sheets ────────────────────────────────────────
    for ws in [ws1, ws2, ws3, ws4]:
        ws.freeze_panes = "A4"

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.read()


def render_pl_export():
    st.markdown('<div class="section-header">📊 Annual P&L Report</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">One-click export for your accountant — revenue, GST, tenant ledger, quarterly breakdown</div>', unsafe_allow_html=True)

    df  = get_transaction_df()
    biz = get_business()

    if df.empty:
        st.info("No transaction data available.")
        return

    available_years = sorted(df["Month"].dt.year.unique(), reverse=True)

    c1, c2 = st.columns([1, 3])
    with c1:
        selected_year = st.selectbox("Select financial year", available_years)

    year_df = df[df["Month"].dt.year == selected_year]

    # Quick summary
    total_inv = year_df["Total_Invoice_INR"].sum()
    total_col = year_df["Revenue_Collected_INR"].sum()
    total_gst = year_df["GST_18pct_INR"].sum()
    total_out = year_df["Balance_Due_INR"].sum()
    pay_rate  = year_df["Is_Paid_Binary"].mean() * 100

    st.markdown("<br>", unsafe_allow_html=True)
    c1, c2, c3, c4, c5 = st.columns(5)
    for col, val, label, bg, fg in [
        (c1, inr_fmt(total_inv), "Total invoiced",    "#EBF2FA", "#185FA5"),
        (c2, inr_fmt(total_col), "Revenue collected", "#E8F6F0", "#1D8A5F"),
        (c3, inr_fmt(total_gst), "GST collected",     "#FDF6E3", "#854F0B"),
        (c4, inr_fmt(total_out), "Outstanding",       "#FCEAEA", "#A32D2D"),
        (c5, f"{pay_rate:.1f}%", "Payment rate",      "#F7F4EF", "#444"),
    ]:
        with col:
            st.markdown(
                f'<div style="background:{bg};border-radius:10px;padding:12px 14px;text-align:center;">'
                f'<div style="font-size:18px;font-weight:600;color:{fg}">{val}</div>'
                f'<div style="font-size:10px;color:{fg};text-transform:uppercase;letter-spacing:.06em">{label}</div>'
                f'</div>', unsafe_allow_html=True,
            )

    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown(
        '<div class="alert-info">📋 The Excel file contains 4 sheets: <strong>P&L Summary</strong>, '
        '<strong>Monthly Breakdown</strong>, <strong>Tenant Ledger</strong>, and '
        '<strong>GST Statement</strong> — ready to hand to your CA.</div>',
        unsafe_allow_html=True,
    )

    if st.button("⬇️ Download Excel Report", type="primary", use_container_width=False):
        with st.spinner(f"Building P&L report for {selected_year}..."):
            excel_bytes = generate_pl_excel(df, selected_year)
        if excel_bytes:
            fname = f"WareHub_PL_{selected_year}_{biz.get('business_name','').replace(' ','_')}.xlsx"
            st.download_button(
                label=f"📥 {fname}",
                data=excel_bytes,
                file_name=fname,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
            st.success("Report ready! Click the button above to download.")

    # Quarterly table preview
    st.markdown("#### Quarterly preview")
    q_tbl = (
        year_df.groupby("Quarter")
        .agg(
            Invoiced=("Total_Invoice_INR",      "sum"),
            Collected=("Revenue_Collected_INR", "sum"),
            GST=("GST_18pct_INR",              "sum"),
            Outstanding=("Balance_Due_INR",     "sum"),
        )
        .reset_index()
    )
    q_tbl["Invoiced"]    = q_tbl["Invoiced"].apply(inr_fmt)
    q_tbl["Collected"]   = q_tbl["Collected"].apply(inr_fmt)
    q_tbl["GST"]         = q_tbl["GST"].apply(inr_fmt)
    q_tbl["Outstanding"] = q_tbl["Outstanding"].apply(inr_fmt)
    q_tbl.columns = ["Quarter", "Invoiced", "Collected", "GST (18%)", "Outstanding"]
    st.dataframe(q_tbl, use_container_width=True, hide_index=True)
