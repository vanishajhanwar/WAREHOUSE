"""
admin.py — Admin Panel: Manage All Master Data From the Dashboard
Warehouse Rental Management Analytics — Data Analytics MGB Project

Pages:
  1. Business Profile  — your name, phone, email, bank details, GST settings
  2. Owners           — add / edit / remove family owners
  3. Warehouses       — add / edit / remove warehouse properties
  4. Tenants          — add / edit / remove tenant contacts
  5. Rentals          — add / edit / remove active lease agreements
  6. Data Preview     — see the live transaction dataset built from masters
"""

import streamlit as st
import pandas as pd
from datetime import datetime, date

from data_manager import (
    get_business, get_owners, get_warehouses, get_tenants, get_rentals,
    save_business, save_owners, save_warehouses, save_tenants, save_rentals,
    get_transaction_df, _next_id,
    DEFAULT_BUSINESS,
)

# ── Shared style helpers ──────────────────────────────────────────────────────
def _info(msg):  st.markdown(f'<div style="background:#EBF2FA;border:1px solid #BDD5EE;border-radius:8px;padding:10px 14px;font-size:13px;color:#1A3C5E;margin-bottom:12px">{msg}</div>', unsafe_allow_html=True)
def _success(msg): st.markdown(f'<div style="background:#E8F6F0;border:1px solid #A8DDD8;border-radius:8px;padding:10px 14px;font-size:13px;color:#1D8A5F;margin-bottom:12px">{msg}</div>', unsafe_allow_html=True)
def _warn(msg):  st.markdown(f'<div style="background:#FDF6E3;border:1px solid #F0DFA0;border-radius:8px;padding:10px 14px;font-size:13px;color:#D97706;margin-bottom:12px">{msg}</div>', unsafe_allow_html=True)

WH_TYPES  = ["Cold Storage", "Dry Warehouse", "Distribution Hub", "General"]
WH_SIZES  = ["Small", "Medium", "Large"]
TNT_TYPES = ["Business", "Individual"]
INDUSTRIES = ["Retail", "Agriculture", "Logistics", "Textile", "Pharma", "FMCG",
              "Electronics", "Food & Bev", "Cold Chain", "Chemicals", "Trading",
              "E-Commerce", "Construction", "Auto Parts", "Personal", "Other"]
STATES = ["Rajasthan", "Gujarat", "Maharashtra", "Madhya Pradesh", "Uttar Pradesh",
          "Punjab", "Haryana", "Delhi", "Karnataka", "Tamil Nadu", "Other"]


# ════════════════════════════════════════════════════════════════════════════
# MAIN RENDER
# ════════════════════════════════════════════════════════════════════════════

def render_admin_page():
    st.markdown(
        '<div style="font-family:DM Serif Display,serif;font-size:22px;color:#0F1923;'
        'letter-spacing:-.02em;margin-bottom:4px">🗂️ Admin Panel — Manage Your Data</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div style="font-size:13px;color:#64748B;margin-bottom:20px">'
        'Add or update owners, warehouses, tenants, rentals, and your business profile — '
        'all changes reflect instantly in the dashboard</div>',
        unsafe_allow_html=True,
    )

    tab_biz, tab_own, tab_wh, tab_tnt, tab_rent, tab_preview = st.tabs([
        "🏢 Business Profile",
        "👨‍👩‍👧 Owners",
        "🏭 Warehouses",
        "🤝 Tenants",
        "📄 Rentals",
        "📊 Data Preview",
    ])

    # ════════════════════════════════
    # TAB 1 — BUSINESS PROFILE
    # ════════════════════════════════
    with tab_biz:
        _render_business_profile()

    # ════════════════════════════════
    # TAB 2 — OWNERS
    # ════════════════════════════════
    with tab_own:
        _render_owners()

    # ════════════════════════════════
    # TAB 3 — WAREHOUSES
    # ════════════════════════════════
    with tab_wh:
        _render_warehouses()

    # ════════════════════════════════
    # TAB 4 — TENANTS
    # ════════════════════════════════
    with tab_tnt:
        _render_tenants()

    # ════════════════════════════════
    # TAB 5 — RENTALS
    # ════════════════════════════════
    with tab_rent:
        _render_rentals()

    # ════════════════════════════════
    # TAB 6 — DATA PREVIEW
    # ════════════════════════════════
    with tab_preview:
        _render_data_preview()


# ════════════════════════════════════════════════════════════════════════════
# BUSINESS PROFILE
# ════════════════════════════════════════════════════════════════════════════

def _render_business_profile():
    st.markdown("#### Your Business & Contact Details")
    _info("These details appear on every invoice and reminder message sent to tenants. "
          "Your phone and email are used as sender credentials in ⚙️ Settings.")

    biz = get_business()

    with st.form("biz_form"):
        st.markdown("**👤 Your Personal Details**")
        c1, c2 = st.columns(2)
        with c1:
            b_name = st.text_input("Business / Family Name",
                value=biz.get("business_name", ""), placeholder="WareHub Family Properties")
            b_owner = st.text_input("Your Name (Primary Owner)",
                value=biz.get("owner_name", ""), placeholder="Rajesh Shah")
        with c2:
            b_phone = st.text_input("Your WhatsApp Number",
                value=biz.get("phone", "9571789145"),
                placeholder="9571789145 — no +91 prefix",
                help="This number will be pre-filled in the WhatsApp settings. "
                     "Format: 10-digit number without country code.")
            b_email = st.text_input("Your Email Address",
                value=biz.get("email", ""),
                placeholder="yourname@gmail.com",
                help="This will be pre-filled in the Gmail settings.")

        st.markdown("**🏢 Business Details**")
        c1, c2 = st.columns(2)
        with c1:
            b_addr   = st.text_area("Business Address", value=biz.get("address",""), height=80)
            b_gstin  = st.text_input("GSTIN", value=biz.get("gstin",""), placeholder="08AABCW1234F1ZX")
        with c2:
            b_pan    = st.text_input("PAN Number", value=biz.get("pan",""), placeholder="AABCW1234F")
            c_gst, c_due, c_pen = st.columns(3)
            with c_gst:
                b_gst_rate = st.number_input("GST Rate %", value=int(biz.get("gst_rate",18)), min_value=0, max_value=28, step=1)
            with c_due:
                b_due_days = st.number_input("Due Days", value=int(biz.get("due_days",10)), min_value=1, max_value=30, step=1,
                    help="Invoice due N days after the 1st of month")
            with c_pen:
                b_penalty  = st.number_input("Penalty %/month", value=float(biz.get("penalty_pct",2)), min_value=0.0, max_value=5.0, step=0.5)

        st.markdown("**🏦 Bank & Payment Details**")
        c1, c2 = st.columns(2)
        with c1:
            b_bank    = st.text_input("Bank Name",    value=biz.get("bank_name",""),    placeholder="State Bank of India")
            b_acct    = st.text_input("Account No.",  value=biz.get("bank_account",""), placeholder="32145678901234")
        with c2:
            b_ifsc    = st.text_input("IFSC Code",    value=biz.get("bank_ifsc",""),    placeholder="SBIN0001234")
            b_upi     = st.text_input("UPI ID",       value=biz.get("upi_id",""),       placeholder="yourname@sbi")
        b_branch  = st.text_input("Bank Branch",  value=biz.get("bank_branch",""), placeholder="Udaipur Main Branch")

        saved = st.form_submit_button("💾 Save Business Profile", type="primary")

    if saved:
        new_biz = {
            "business_name": b_name, "owner_name": b_owner,
            "phone": b_phone.strip(), "email": b_email.strip(),
            "address": b_addr, "gstin": b_gstin, "pan": b_pan,
            "bank_name": b_bank, "bank_account": b_acct,
            "bank_ifsc": b_ifsc, "bank_branch": b_branch, "upi_id": b_upi,
            "gst_rate": b_gst_rate, "due_days": b_due_days, "penalty_pct": b_penalty,
        }
        save_business(new_biz)
        # Auto-fill settings session state
        if b_phone:
            import re
            ph = re.sub(r"\D","",b_phone)
            if not ph.startswith("91"): ph = "91"+ph
            st.session_state["sender_phone"] = ph
        if b_email:
            st.session_state["gmail_user_prefill"] = b_email
        _success("✅ Business profile saved! Invoice templates will now use these details.")
        st.rerun()


# ════════════════════════════════════════════════════════════════════════════
# OWNERS
# ════════════════════════════════════════════════════════════════════════════

def _render_owners():
    st.markdown("#### Family Owners")
    _info("Each owner is a family member who owns one or more warehouses. "
          "Their email is CC'd on invoices for their properties.")

    owners = get_owners()

    # ── Existing owners table ──
    if owners:
        st.markdown(f"**{len(owners)} owner(s) in portfolio**")
        for i, own in enumerate(owners):
            with st.expander(f"🧑 {own.get('name','Unnamed')}  —  {own.get('id','')}"):
                with st.form(f"own_edit_{i}"):
                    ec1, ec2, ec3 = st.columns(3)
                    with ec1:
                        n_name  = st.text_input("Full Name",  value=own.get("name",""),  key=f"on_{i}")
                        n_city  = st.text_input("City",       value=own.get("city",""),  key=f"oc_{i}")
                    with ec2:
                        n_phone = st.text_input("Phone",      value=own.get("phone",""), key=f"op_{i}")
                        n_email = st.text_input("Email",      value=own.get("email",""), key=f"oe_{i}")
                    with ec3:
                        st.markdown("**Actions**")
                        save_btn   = st.form_submit_button("💾 Save",   type="primary")
                        delete_btn = st.form_submit_button("🗑️ Delete")

                if save_btn:
                    owners[i].update({"name":n_name,"city":n_city,"phone":n_phone,"email":n_email})
                    save_owners(owners)
                    _success(f"✅ {n_name} updated.")
                    st.rerun()
                if delete_btn:
                    removed = owners.pop(i)
                    save_owners(owners)
                    st.warning(f"🗑️ {removed.get('name','')} removed.")
                    st.rerun()

    st.markdown("---")
    st.markdown("#### ➕ Add New Owner")
    with st.form("own_add_form"):
        ac1, ac2 = st.columns(2)
        with ac1:
            a_name  = st.text_input("Full Name*",  placeholder="Ramesh Shah")
            a_city  = st.text_input("City*",       placeholder="Udaipur")
        with ac2:
            a_phone = st.text_input("Phone*",      placeholder="9876543210")
            a_email = st.text_input("Email*",      placeholder="ramesh@gmail.com")
        add_btn = st.form_submit_button("➕ Add Owner", type="primary")

    if add_btn:
        if not a_name or not a_phone:
            st.error("Name and phone are required.")
        else:
            owners = get_owners()
            new_id = _next_id(owners, "OWN")
            owners.append({"id":new_id,"name":a_name,"city":a_city,"phone":a_phone,"email":a_email})
            save_owners(owners)
            _success(f"✅ {a_name} added as owner {new_id}.")
            st.rerun()


# ════════════════════════════════════════════════════════════════════════════
# WAREHOUSES
# ════════════════════════════════════════════════════════════════════════════

def _render_warehouses():
    st.markdown("#### Warehouse Properties")
    _info("Each warehouse is linked to an owner. Base rent here is the starting point — "
          "actual rent per lease is set in the Rentals tab.")

    warehouses = get_warehouses()
    owners     = get_owners()
    owner_opts = {o["id"]: o["name"] for o in owners}

    if warehouses:
        st.markdown(f"**{len(warehouses)} warehouse(s) in portfolio**")
        for i, wh in enumerate(warehouses):
            own_name = owner_opts.get(wh.get("owner_id",""),"Unknown")
            with st.expander(f"🏭 {wh.get('name','Unnamed')}  —  {wh.get('location','')}  |  Owner: {own_name}"):
                with st.form(f"wh_edit_{i}"):
                    wc1, wc2, wc3 = st.columns(3)
                    with wc1:
                        w_name  = st.text_input("Warehouse Name",   value=wh.get("name",""),     key=f"wn_{i}")
                        w_loc   = st.text_input("Location/City",    value=wh.get("location",""), key=f"wl_{i}")
                        w_state = st.selectbox("State", STATES,
                            index=STATES.index(wh.get("state","Rajasthan")) if wh.get("state") in STATES else 0,
                            key=f"ws_{i}")
                    with wc2:
                        w_type  = st.selectbox("Warehouse Type", WH_TYPES,
                            index=WH_TYPES.index(wh.get("type","Dry Warehouse")) if wh.get("type") in WH_TYPES else 1,
                            key=f"wt_{i}")
                        w_size  = st.selectbox("Size", WH_SIZES,
                            index=WH_SIZES.index(wh.get("size","Medium")) if wh.get("size") in WH_SIZES else 1,
                            key=f"wz_{i}")
                        w_owner = st.selectbox("Owner", list(owner_opts.keys()),
                            format_func=lambda x: owner_opts.get(x,x),
                            index=list(owner_opts.keys()).index(wh.get("owner_id","OWN-01")) if wh.get("owner_id") in owner_opts else 0,
                            key=f"wo_{i}")
                    with wc3:
                        w_rent  = st.number_input("Base Rent (₹/mo)", value=int(wh.get("base_rent",30000)), min_value=0, step=500, key=f"wr_{i}")
                        w_area  = st.number_input("Area (sq.ft)",      value=int(wh.get("area_sqft",5000)),  min_value=0, step=100, key=f"wa_{i}")
                        w_cap   = st.number_input("Capacity (MT)",     value=int(wh.get("capacity_mt",100)), min_value=0, step=10,  key=f"wc_{i}")
                        sv = st.form_submit_button("💾 Save", type="primary")
                        dl = st.form_submit_button("🗑️ Delete")

                if sv:
                    warehouses[i].update({"name":w_name,"location":w_loc,"state":w_state,
                        "type":w_type,"size":w_size,"owner_id":w_owner,
                        "base_rent":w_rent,"area_sqft":w_area,"capacity_mt":w_cap})
                    save_warehouses(warehouses)
                    _success(f"✅ {w_name} updated.")
                    st.rerun()
                if dl:
                    removed = warehouses.pop(i)
                    save_warehouses(warehouses)
                    st.warning(f"🗑️ {removed.get('name','')} removed.")
                    st.rerun()

    st.markdown("---")
    st.markdown("#### ➕ Add New Warehouse")
    with st.form("wh_add_form"):
        nc1, nc2, nc3 = st.columns(3)
        with nc1:
            n_name  = st.text_input("Warehouse Name*", placeholder="Jodhpur Cold Store")
            n_loc   = st.text_input("Location/City*",  placeholder="Jodhpur")
            n_state = st.selectbox("State", STATES, key="wh_add_state")
        with nc2:
            n_type  = st.selectbox("Type",  WH_TYPES, key="wh_add_type")
            n_size  = st.selectbox("Size",  WH_SIZES, index=1, key="wh_add_size")
            n_owner = st.selectbox("Owner", list(owner_opts.keys()),
                format_func=lambda x: owner_opts.get(x,x), key="wh_add_owner")
        with nc3:
            n_rent  = st.number_input("Base Rent (₹/mo)", min_value=0, value=30000, step=500)
            n_area  = st.number_input("Area (sq.ft)",     min_value=0, value=5000,  step=100)
            n_cap   = st.number_input("Capacity (MT)",    min_value=0, value=100,   step=10)
        add_wh = st.form_submit_button("➕ Add Warehouse", type="primary")

    if add_wh:
        if not n_name or not n_loc:
            st.error("Name and location are required.")
        else:
            warehouses = get_warehouses()
            new_id = _next_id(warehouses, "WH")
            warehouses.append({"id":new_id,"name":n_name,"location":n_loc,"state":n_state,
                "type":n_type,"size":n_size,"owner_id":n_owner,
                "base_rent":n_rent,"area_sqft":n_area,"capacity_mt":n_cap})
            save_warehouses(warehouses)
            _success(f"✅ {n_name} added as {new_id}.")
            st.rerun()


# ════════════════════════════════════════════════════════════════════════════
# TENANTS
# ════════════════════════════════════════════════════════════════════════════

def _render_tenants():
    st.markdown("#### Tenants")
    _info("Add each tenant with their contact details. Phone and email are used "
          "for sending invoices and reminders. Contact Person is the name used "
          "in the salutation of emails and WhatsApp messages.")

    tenants    = get_tenants()
    warehouses = get_warehouses()
    wh_opts    = {w["id"]: f"{w['name']} ({w['location']})" for w in warehouses}

    if tenants:
        st.markdown(f"**{len(tenants)} tenant(s) in system**")
        for i, tnt in enumerate(tenants):
            wh_label = wh_opts.get(tnt.get("wh_id",""), "Not assigned")
            with st.expander(f"🤝 {tnt.get('name','Unnamed')}  |  📍 {wh_label}  |  📱 {tnt.get('phone','')}"):
                with st.form(f"tnt_edit_{i}"):
                    tc1, tc2, tc3 = st.columns(3)
                    with tc1:
                        t_name    = st.text_input("Company/Tenant Name",  value=tnt.get("name",""),    key=f"tn_{i}")
                        t_contact = st.text_input("Contact Person Name",  value=tnt.get("contact",""), key=f"tcp_{i}",
                            help="Used in 'Dear [Name]' in emails and WhatsApp messages")
                        t_type    = st.selectbox("Tenant Type", TNT_TYPES,
                            index=TNT_TYPES.index(tnt.get("type","Business")) if tnt.get("type") in TNT_TYPES else 0,
                            key=f"tt_{i}")
                    with tc2:
                        t_phone   = st.text_input("WhatsApp Number*",  value=tnt.get("phone",""), key=f"tp_{i}",
                            placeholder="9876543210 — 10 digits without +91")
                        t_email   = st.text_input("Email Address*",    value=tnt.get("email",""), key=f"te_{i}",
                            placeholder="tenant@company.com")
                        t_ind     = st.selectbox("Industry", INDUSTRIES,
                            index=INDUSTRIES.index(tnt.get("industry","Retail")) if tnt.get("industry") in INDUSTRIES else 0,
                            key=f"ti_{i}")
                    with tc3:
                        wh_keys   = list(wh_opts.keys())
                        curr_wh   = tnt.get("wh_id","")
                        wh_idx    = wh_keys.index(curr_wh) if curr_wh in wh_keys else 0
                        t_wh      = st.selectbox("Assigned Warehouse", wh_keys,
                            format_func=lambda x: wh_opts.get(x,x),
                            index=wh_idx, key=f"tw_{i}")
                        t_tenure  = st.number_input("Tenure (months)", value=int(tnt.get("tenure_months",12)),
                            min_value=0, max_value=120, key=f"tm_{i}",
                            help="How long this tenant has been with you")
                        sv2 = st.form_submit_button("💾 Save", type="primary")
                        dl2 = st.form_submit_button("🗑️ Delete")

                if sv2:
                    tenants[i].update({"name":t_name,"contact":t_contact,"type":t_type,
                        "phone":t_phone,"email":t_email,"industry":t_ind,
                        "wh_id":t_wh,"tenure_months":t_tenure})
                    save_tenants(tenants)
                    _success(f"✅ {t_name} updated.")
                    st.rerun()
                if dl2:
                    removed = tenants.pop(i)
                    save_tenants(tenants)
                    st.warning(f"🗑️ {removed.get('name','')} removed.")
                    st.rerun()

    st.markdown("---")
    st.markdown("#### ➕ Add New Tenant")
    _info("💡 You can add fewer tenants than warehouses — just add the ones you have. "
          "The analytics will automatically work with whatever data you enter.")

    with st.form("tnt_add_form"):
        ac1, ac2, ac3 = st.columns(3)
        with ac1:
            a_name    = st.text_input("Company/Tenant Name*", placeholder="Sunrise Foods Ltd")
            a_contact = st.text_input("Contact Person Name*", placeholder="Rahul Mehta",
                help="The person's name used in invoice salutations")
            a_type    = st.selectbox("Tenant Type", TNT_TYPES, key="tnt_add_type")
        with ac2:
            a_phone   = st.text_input("WhatsApp Number*", placeholder="9876543210",
                help="10-digit number — invoices and reminders go to this number")
            a_email   = st.text_input("Email Address*",   placeholder="rahul@sunrise.com",
                help="Invoice and reminder emails go here")
            a_ind     = st.selectbox("Industry", INDUSTRIES, key="tnt_add_ind")
        with ac3:
            wh_keys = list(wh_opts.keys())
            a_wh    = st.selectbox("Assigned Warehouse*", wh_keys,
                format_func=lambda x: wh_opts.get(x,x), key="tnt_add_wh")
            a_tenure = st.number_input("Tenure (months)", value=0, min_value=0, max_value=120,
                help="Enter 0 for brand new tenants")
        add_tnt = st.form_submit_button("➕ Add Tenant", type="primary")

    if add_tnt:
        if not a_name or not a_phone or not a_email:
            st.error("Name, phone, and email are required.")
        else:
            tenants = get_tenants()
            new_id = _next_id(tenants, "TNT")
            tenants.append({"id":new_id,"name":a_name,"contact":a_contact,"type":a_type,
                "phone":a_phone,"email":a_email,"industry":a_ind,
                "wh_id":a_wh,"tenure_months":a_tenure})
            save_tenants(tenants)
            _success(f"✅ {a_name} added as tenant {new_id}.")
            st.rerun()


# ════════════════════════════════════════════════════════════════════════════
# RENTALS
# ════════════════════════════════════════════════════════════════════════════

def _render_rentals():
    st.markdown("#### Rental Agreements / Leases")
    _info("Each rental links a tenant to a warehouse with a specific rent amount and duration. "
          "This drives the invoice generation and the analytics dataset.")

    rentals    = get_rentals()
    tenants    = get_tenants()
    warehouses = get_warehouses()
    tnt_opts   = {t["id"]: t["name"] for t in tenants}
    wh_opts    = {w["id"]: f"{w['name']} ({w['location']})" for w in warehouses}

    STATUS_OPTS = ["Active", "Expired", "Terminated"]

    if rentals:
        st.markdown(f"**{len(rentals)} lease(s) on record**")
        for i, rent in enumerate(rentals):
            tnt_name = tnt_opts.get(rent.get("tenant_id",""), "Unknown")
            wh_name  = wh_opts.get(rent.get("wh_id",""),      "Unknown")
            status   = rent.get("status","Active")
            badge_bg = {"Active":"#E8F6F0","Expired":"#FDF6E3","Terminated":"#FCEAEA"}.get(status,"#F7F4EF")
            badge_fg = {"Active":"#1D8A5F","Expired":"#D97706","Terminated":"#C0392B"}.get(status,"#333")

            with st.expander(
                f"📄 {tnt_name}  ↔  {wh_name}  |  "
                f"₹{int(rent.get('monthly_rent',0)):,}/mo  |  "
                f"{rent.get('start_date','')} → {rent.get('end_date','')}"
            ):
                with st.form(f"rent_edit_{i}"):
                    rc1, rc2, rc3 = st.columns(3)
                    with rc1:
                        tnt_keys = list(tnt_opts.keys())
                        curr_tnt = rent.get("tenant_id","")
                        r_tnt = st.selectbox("Tenant", tnt_keys,
                            format_func=lambda x: tnt_opts.get(x,x),
                            index=tnt_keys.index(curr_tnt) if curr_tnt in tnt_keys else 0,
                            key=f"rt_{i}")
                        wh_keys = list(wh_opts.keys())
                        curr_wh = rent.get("wh_id","")
                        r_wh = st.selectbox("Warehouse", wh_keys,
                            format_func=lambda x: wh_opts.get(x,x),
                            index=wh_keys.index(curr_wh) if curr_wh in wh_keys else 0,
                            key=f"rw_{i}")
                    with rc2:
                        r_rent  = st.number_input("Monthly Rent (₹)", value=int(rent.get("monthly_rent",30000)),
                            min_value=0, step=500, key=f"rr_{i}")
                        r_start = st.text_input("Start Date (YYYY-MM-DD)",
                            value=str(rent.get("start_date","")), key=f"rs_{i}")
                        r_end   = st.text_input("End Date   (YYYY-MM-DD)",
                            value=str(rent.get("end_date","")),   key=f"re_{i}")
                    with rc3:
                        r_status = st.selectbox("Status", STATUS_OPTS,
                            index=STATUS_OPTS.index(status) if status in STATUS_OPTS else 0,
                            key=f"rstat_{i}")
                        sv3 = st.form_submit_button("💾 Save", type="primary")
                        dl3 = st.form_submit_button("🗑️ Delete")

                if sv3:
                    rentals[i].update({"tenant_id":r_tnt,"wh_id":r_wh,
                        "monthly_rent":r_rent,"start_date":r_start,
                        "end_date":r_end,"status":r_status})
                    save_rentals(rentals)
                    _success("✅ Rental updated.")
                    st.rerun()
                if dl3:
                    removed = rentals.pop(i)
                    save_rentals(rentals)
                    st.warning(f"🗑️ Rental for {tnt_name} removed.")
                    st.rerun()

    st.markdown("---")
    st.markdown("#### ➕ Add New Rental / Lease")
    with st.form("rent_add_form"):
        tnt_keys = list(tnt_opts.keys())
        wh_keys  = list(wh_opts.keys())

        if not tnt_keys:
            st.error("Add at least one tenant first (in the Tenants tab).")
        elif not wh_keys:
            st.error("Add at least one warehouse first (in the Warehouses tab).")
        else:
            rac1, rac2, rac3 = st.columns(3)
            with rac1:
                a_tnt   = st.selectbox("Tenant*", tnt_keys,
                    format_func=lambda x: tnt_opts.get(x,x), key="rent_add_tnt")
                a_wh    = st.selectbox("Warehouse*", wh_keys,
                    format_func=lambda x: wh_opts.get(x,x), key="rent_add_wh")
            with rac2:
                a_rent  = st.number_input("Monthly Rent (₹)*", min_value=0, value=50000, step=500)
                a_start = st.date_input("Lease Start Date*", value=date.today())
            with rac3:
                a_end   = st.date_input("Lease End Date*",
                    value=date(date.today().year + 1, date.today().month, date.today().day))
                a_stat  = st.selectbox("Status", STATUS_OPTS, key="rent_add_stat")

            add_rent = st.form_submit_button("➕ Add Rental", type="primary")

            if add_rent:
                rentals = get_rentals()
                new_id  = _next_id(rentals, "RNT")
                rentals.append({
                    "id": new_id,
                    "tenant_id": a_tnt,
                    "wh_id": a_wh,
                    "monthly_rent": a_rent,
                    "start_date": str(a_start),
                    "end_date":   str(a_end),
                    "status": a_stat,
                })
                save_rentals(rentals)
                _success(f"✅ New rental {new_id} added for {tnt_opts.get(a_tnt,a_tnt)}.")
                st.rerun()


# ════════════════════════════════════════════════════════════════════════════
# DATA PREVIEW
# ════════════════════════════════════════════════════════════════════════════

def _render_data_preview():
    st.markdown("#### Live Transaction Dataset")
    _info("This dataset is auto-built from your Owners → Warehouses → Tenants → Rentals data. "
          "Every time you make a change above, this updates automatically. "
          "All analytics, charts, and ML models run on this data.")

    df = get_transaction_df()

    if df.empty:
        _warn("No data yet — add at least one Owner, Warehouse, Tenant, and Rental to generate transactions.")
        return

    # Summary
    kc1, kc2, kc3, kc4, kc5 = st.columns(5)
    kc1.metric("Total Rows",     len(df))
    kc2.metric("Tenants",        df["Tenant_ID"].nunique() if "Tenant_ID" in df.columns else "—")
    kc3.metric("Warehouses",     df["WH_ID"].nunique() if "WH_ID" in df.columns else "—")
    kc4.metric("Months Covered", df["Month"].nunique() if "Month" in df.columns else "—")
    paid_rate = df["Is_Paid_Binary"].mean() * 100 if "Is_Paid_Binary" in df.columns else 0
    kc5.metric("Paid Rate",      f"{paid_rate:.1f}%")

    st.markdown("**Preview (first 50 rows)**")
    preview_cols = [c for c in [
        "Row_ID","Tenant_Name","Owner_Name","Warehouse_Location","Warehouse_Type",
        "Month_Name","Monthly_Rent_INR","Total_Invoice_INR","Payment_Status",
        "Delay_Days","Balance_Due_INR","Risk_Score","Tenant_Segment",
        "Tenant_Email","Tenant_Phone",
    ] if c in df.columns]
    st.dataframe(df[preview_cols].head(50), use_container_width=True, hide_index=True)

    # Download
    import io
    buf = io.BytesIO()
    df.to_csv(buf, index=False)
    buf.seek(0)
    st.download_button(
        "⬇️ Download Full Dataset (CSV)",
        data=buf,
        file_name="warehouse_transactions.csv",
        mime="text/csv",
    )
