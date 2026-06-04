"""
data_manager.py — SQLite-backed Persistent Data Store (Upgrade #7)
Warehouse Rental Management Analytics
"""

import sqlite3
import os
import json
from datetime import datetime
from contextlib import contextmanager
import pandas as pd
import numpy as np
import streamlit as st

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(DATA_DIR, "warehub.db")

DEFAULT_BUSINESS = {
    "business_name":"WareHub Family Properties","owner_name":"Rajesh Shah",
    "phone":"9571789145","email":"","address":"123, Industrial Estate, Udaipur, Rajasthan — 313001",
    "gstin":"08AABCW1234F1ZX","pan":"AABCW1234F","bank_name":"State Bank of India",
    "bank_account":"32145678901234","bank_ifsc":"SBIN0001234","bank_branch":"Udaipur Main Branch",
    "upi_id":"warehub@sbi","gst_rate":18,"due_days":10,"penalty_pct":2,
}
DEFAULT_OWNERS = [
    {"id":"OWN-01","name":"Rajesh Shah","phone":"9876543210","email":"rajesh.shah@warehub.in","city":"Udaipur"},
    {"id":"OWN-02","name":"Meena Joshi","phone":"9823456789","email":"meena.joshi@warehub.in","city":"Jaipur"},
    {"id":"OWN-03","name":"Amit Patel","phone":"9812345678","email":"amit.patel@warehub.in","city":"Ahmedabad"},
    {"id":"OWN-04","name":"Sunita Gupta","phone":"9898765432","email":"sunita.gupta@warehub.in","city":"Surat"},
]
DEFAULT_WAREHOUSES = [
    {"id":"WH-01","name":"Udaipur Cold Hub","location":"Udaipur","state":"Rajasthan","type":"Cold Storage","size":"Medium","owner_id":"OWN-01","base_rent":32000,"capacity_mt":120,"area_sqft":8000},
    {"id":"WH-02","name":"Jaipur Dry Store","location":"Jaipur","state":"Rajasthan","type":"Dry Warehouse","size":"Large","owner_id":"OWN-02","base_rent":45000,"capacity_mt":200,"area_sqft":12000},
    {"id":"WH-03","name":"Ahmedabad Mega Hub","location":"Ahmedabad","state":"Gujarat","type":"Distribution Hub","size":"Large","owner_id":"OWN-03","base_rent":72000,"capacity_mt":350,"area_sqft":20000},
    {"id":"WH-04","name":"Surat Textile WH","location":"Surat","state":"Gujarat","type":"Dry Warehouse","size":"Medium","owner_id":"OWN-04","base_rent":28000,"capacity_mt":160,"area_sqft":9500},
    {"id":"WH-05","name":"Jaipur Pharma Store","location":"Jaipur","state":"Rajasthan","type":"Cold Storage","size":"Small","owner_id":"OWN-02","base_rent":22000,"capacity_mt":80,"area_sqft":6000},
    {"id":"WH-06","name":"Udaipur Dist Hub","location":"Udaipur","state":"Rajasthan","type":"Distribution Hub","size":"Large","owner_id":"OWN-01","base_rent":65000,"capacity_mt":260,"area_sqft":15000},
]
DEFAULT_TENANTS = [
    {"id":"TNT-01","name":"FreshMart Retail","type":"Business","industry":"Retail","contact":"Suresh Kumar","phone":"9871234560","email":"procurement@freshmart.in","tenure_months":36,"wh_id":"WH-01"},
    {"id":"TNT-02","name":"GrainCorp Ltd","type":"Business","industry":"Agriculture","contact":"Priya Sharma","phone":"9812345670","email":"accounts@graincorp.co.in","tenure_months":28,"wh_id":"WH-02"},
    {"id":"TNT-03","name":"QuickShip Logistics","type":"Business","industry":"Logistics","contact":"Vikram Singh","phone":"9834567890","email":"finance@quickship.in","tenure_months":42,"wh_id":"WH-03"},
    {"id":"TNT-04","name":"TextilePro Exports","type":"Business","industry":"Textile","contact":"Anita Desai","phone":"9845678901","email":"admin@textilepro.com","tenure_months":18,"wh_id":"WH-04"},
    {"id":"TNT-05","name":"PharmaPlus India","type":"Business","industry":"Pharma","contact":"Dr. R. Mehta","phone":"9856789012","email":"ap@pharmaplus.in","tenure_months":30,"wh_id":"WH-05"},
    {"id":"TNT-06","name":"Metro Distributors","type":"Business","industry":"FMCG","contact":"Rajan Gupta","phone":"9867890123","email":"accounts@metrodist.co.in","tenure_months":24,"wh_id":"WH-06"},
]
DEFAULT_RENTALS = [
    {"id":"RNT-01","tenant_id":"TNT-01","wh_id":"WH-01","start_date":"2023-03-01","end_date":"2025-02-28","monthly_rent":85000,"status":"Active"},
    {"id":"RNT-02","tenant_id":"TNT-02","wh_id":"WH-02","start_date":"2022-07-01","end_date":"2024-06-30","monthly_rent":72000,"status":"Active"},
    {"id":"RNT-03","tenant_id":"TNT-03","wh_id":"WH-03","start_date":"2024-01-01","end_date":"2026-12-31","monthly_rent":145000,"status":"Active"},
    {"id":"RNT-04","tenant_id":"TNT-04","wh_id":"WH-04","start_date":"2023-09-01","end_date":"2025-08-31","monthly_rent":58000,"status":"Active"},
    {"id":"RNT-05","tenant_id":"TNT-05","wh_id":"WH-05","start_date":"2024-03-01","end_date":"2025-02-28","monthly_rent":65000,"status":"Active"},
    {"id":"RNT-06","tenant_id":"TNT-06","wh_id":"WH-06","start_date":"2023-11-01","end_date":"2025-10-31","monthly_rent":110000,"status":"Active"},
]

@contextmanager
def _db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db():
    with _db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS business_config (key TEXT PRIMARY KEY, value TEXT, updated_at TEXT DEFAULT (datetime('now')));
            CREATE TABLE IF NOT EXISTS owners (id TEXT PRIMARY KEY, name TEXT, phone TEXT, email TEXT, city TEXT, created_at TEXT DEFAULT (datetime('now')), updated_at TEXT DEFAULT (datetime('now')));
            CREATE TABLE IF NOT EXISTS warehouses (id TEXT PRIMARY KEY, name TEXT, location TEXT, state TEXT, type TEXT, size TEXT, owner_id TEXT, base_rent REAL, capacity_mt REAL, area_sqft REAL, is_vacant INTEGER DEFAULT 0, vacant_since TEXT, created_at TEXT DEFAULT (datetime('now')), updated_at TEXT DEFAULT (datetime('now')));
            CREATE TABLE IF NOT EXISTS tenants (id TEXT PRIMARY KEY, name TEXT, type TEXT, industry TEXT, contact TEXT, phone TEXT, email TEXT, tenure_months INTEGER DEFAULT 0, wh_id TEXT, created_at TEXT DEFAULT (datetime('now')), updated_at TEXT DEFAULT (datetime('now')));
            CREATE TABLE IF NOT EXISTS rentals (id TEXT PRIMARY KEY, tenant_id TEXT, wh_id TEXT, start_date TEXT, end_date TEXT, monthly_rent REAL, status TEXT DEFAULT 'Active', created_at TEXT DEFAULT (datetime('now')), updated_at TEXT DEFAULT (datetime('now')));
            CREATE TABLE IF NOT EXISTS payments (id TEXT PRIMARY KEY, rental_id TEXT, tenant_id TEXT, wh_id TEXT, month TEXT, amount_due REAL, amount_paid REAL DEFAULT 0, payment_status TEXT DEFAULT 'Pending', payment_date TEXT, reminder_sent_wa INTEGER DEFAULT 0, reminder_sent_email INTEGER DEFAULT 0, wa_sent_at TEXT, email_sent_at TEXT, receipt_sent INTEGER DEFAULT 0, notes TEXT, created_at TEXT DEFAULT (datetime('now')), updated_at TEXT DEFAULT (datetime('now')));
            CREATE TABLE IF NOT EXISTS audit_log (id INTEGER PRIMARY KEY AUTOINCREMENT, table_name TEXT, record_id TEXT, action TEXT, changes TEXT, ts TEXT DEFAULT (datetime('now')));
        """)
        if conn.execute("SELECT COUNT(*) FROM owners").fetchone()[0] == 0:
            _seed_defaults(conn)

def _seed_defaults(conn):
    for k, v in DEFAULT_BUSINESS.items():
        conn.execute("INSERT OR IGNORE INTO business_config (key, value) VALUES (?, ?)", (k, str(v)))
    for o in DEFAULT_OWNERS:
        conn.execute("INSERT OR IGNORE INTO owners (id, name, phone, email, city) VALUES (?,?,?,?,?)", (o["id"],o["name"],o["phone"],o["email"],o["city"]))
    for w in DEFAULT_WAREHOUSES:
        conn.execute("INSERT OR IGNORE INTO warehouses (id,name,location,state,type,size,owner_id,base_rent,capacity_mt,area_sqft) VALUES (?,?,?,?,?,?,?,?,?,?)", (w["id"],w["name"],w["location"],w["state"],w["type"],w["size"],w["owner_id"],w["base_rent"],w["capacity_mt"],w["area_sqft"]))
    for t in DEFAULT_TENANTS:
        conn.execute("INSERT OR IGNORE INTO tenants (id,name,type,industry,contact,phone,email,tenure_months,wh_id) VALUES (?,?,?,?,?,?,?,?,?)", (t["id"],t["name"],t["type"],t["industry"],t["contact"],t["phone"],t["email"],t["tenure_months"],t["wh_id"]))
    for r in DEFAULT_RENTALS:
        conn.execute("INSERT OR IGNORE INTO rentals (id,tenant_id,wh_id,start_date,end_date,monthly_rent,status) VALUES (?,?,?,?,?,?,?)", (r["id"],r["tenant_id"],r["wh_id"],r["start_date"],r["end_date"],r["monthly_rent"],r["status"]))

def _audit(conn, table, record_id, action, changes=None):
    conn.execute("INSERT INTO audit_log (table_name, record_id, action, changes) VALUES (?,?,?,?)", (table, record_id, action, json.dumps(changes or {}, default=str)))

def get_business():
    with _db() as conn:
        rows = conn.execute("SELECT key, value FROM business_config").fetchall()
        if not rows: return DEFAULT_BUSINESS.copy()
        result = DEFAULT_BUSINESS.copy()
        for row in rows:
            k, v = row["key"], row["value"]
            result[k] = int(v) if k in ("gst_rate","due_days","penalty_pct") else v
        return result

def get_owners():
    with _db() as conn:
        rows = conn.execute("SELECT * FROM owners ORDER BY id").fetchall()
        return [dict(r) for r in rows] if rows else list(DEFAULT_OWNERS)

def get_warehouses():
    with _db() as conn:
        rows = conn.execute("SELECT * FROM warehouses ORDER BY id").fetchall()
        return [dict(r) for r in rows] if rows else list(DEFAULT_WAREHOUSES)

def get_tenants():
    with _db() as conn:
        rows = conn.execute("SELECT * FROM tenants ORDER BY id").fetchall()
        return [dict(r) for r in rows] if rows else list(DEFAULT_TENANTS)

def get_rentals():
    with _db() as conn:
        rows = conn.execute("SELECT * FROM rentals ORDER BY id").fetchall()
        return [dict(r) for r in rows] if rows else list(DEFAULT_RENTALS)

def get_payments_for_month(year, month):
    month_str = f"{year}-{month:02d}"
    with _db() as conn:
        rows = conn.execute("SELECT * FROM payments WHERE month=? ORDER BY tenant_id", (month_str,)).fetchall()
        return [dict(r) for r in rows]

def get_payment_history(tenant_id=None):
    with _db() as conn:
        if tenant_id:
            rows = conn.execute("SELECT * FROM payments WHERE tenant_id=? ORDER BY month DESC", (tenant_id,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM payments ORDER BY month DESC").fetchall()
        return [dict(r) for r in rows]

def get_audit_log(limit=100):
    with _db() as conn:
        rows = conn.execute("SELECT * FROM audit_log ORDER BY ts DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]

def get_vacancy_stats():
    warehouses = get_warehouses()
    rentals    = get_rentals()
    active_wh  = {r["wh_id"] for r in rentals if r.get("status") == "Active"}
    today      = datetime.today()
    result     = []
    for wh in warehouses:
        is_vacant    = wh["id"] not in active_wh
        vacant_since = wh.get("vacant_since")
        days_vacant  = 0
        if is_vacant and vacant_since:
            try:
                days_vacant = (today - datetime.strptime(vacant_since, "%Y-%m-%d")).days
            except Exception: pass
        monthly_loss = wh.get("base_rent", 0)
        result.append({**wh, "is_vacant":is_vacant, "days_vacant":days_vacant,
                       "monthly_loss":monthly_loss, "revenue_lost":round(days_vacant/30*monthly_loss,0) if is_vacant else 0})
    return result

def get_expiring_leases(days_ahead=60):
    rentals    = get_rentals()
    tenants    = {t["id"]: t for t in get_tenants()}
    warehouses = {w["id"]: w for w in get_warehouses()}
    today      = datetime.today()
    result     = []
    for r in rentals:
        if r.get("status") != "Active": continue
        try:
            end = datetime.strptime(r["end_date"], "%Y-%m-%d")
            days_left = (end - today).days
            if 0 <= days_left <= days_ahead:
                tnt = tenants.get(r["tenant_id"], {})
                wh  = warehouses.get(r["wh_id"], {})
                result.append({**r, "days_left":days_left, "tenant_name":tnt.get("name","—"),
                                "tenant_phone":tnt.get("phone",""), "wh_name":wh.get("name","—"),
                                "wh_location":wh.get("location","—")})
        except Exception: pass
    return sorted(result, key=lambda x: x["days_left"])

def save_business(data):
    with _db() as conn:
        for k, v in data.items():
            conn.execute("INSERT OR REPLACE INTO business_config (key, value, updated_at) VALUES (?,?,datetime('now'))", (k, str(v)))
        _audit(conn, "business_config", "singleton", "UPDATE", data)
    st.cache_data.clear()

def save_owners(data):
    with _db() as conn:
        existing = {r["id"] for r in conn.execute("SELECT id FROM owners").fetchall()}
        for o in data:
            if o["id"] in existing:
                conn.execute("UPDATE owners SET name=?,phone=?,email=?,city=?,updated_at=datetime('now') WHERE id=?", (o["name"],o.get("phone",""),o.get("email",""),o.get("city",""),o["id"]))
            else:
                conn.execute("INSERT INTO owners (id,name,phone,email,city) VALUES (?,?,?,?,?)", (o["id"],o["name"],o.get("phone",""),o.get("email",""),o.get("city","")))
            _audit(conn, "owners", o["id"], "UPSERT", o)
    st.cache_data.clear()

def save_warehouses(data):
    with _db() as conn:
        existing = {r["id"] for r in conn.execute("SELECT id FROM warehouses").fetchall()}
        for w in data:
            if w["id"] in existing:
                conn.execute("UPDATE warehouses SET name=?,location=?,state=?,type=?,size=?,owner_id=?,base_rent=?,capacity_mt=?,area_sqft=?,is_vacant=?,vacant_since=?,updated_at=datetime('now') WHERE id=?", (w["name"],w.get("location",""),w.get("state",""),w.get("type",""),w.get("size",""),w.get("owner_id",""),w.get("base_rent",0),w.get("capacity_mt",0),w.get("area_sqft",0),int(w.get("is_vacant",0)),w.get("vacant_since"),w["id"]))
            else:
                conn.execute("INSERT INTO warehouses (id,name,location,state,type,size,owner_id,base_rent,capacity_mt,area_sqft,is_vacant,vacant_since) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", (w["id"],w["name"],w.get("location",""),w.get("state",""),w.get("type",""),w.get("size",""),w.get("owner_id",""),w.get("base_rent",0),w.get("capacity_mt",0),w.get("area_sqft",0),int(w.get("is_vacant",0)),w.get("vacant_since")))
            _audit(conn, "warehouses", w["id"], "UPSERT", w)
    st.cache_data.clear()

def save_tenants(data):
    with _db() as conn:
        existing = {r["id"] for r in conn.execute("SELECT id FROM tenants").fetchall()}
        for t in data:
            if t["id"] in existing:
                conn.execute("UPDATE tenants SET name=?,type=?,industry=?,contact=?,phone=?,email=?,tenure_months=?,wh_id=?,updated_at=datetime('now') WHERE id=?", (t["name"],t.get("type","Business"),t.get("industry",""),t.get("contact",""),t.get("phone",""),t.get("email",""),t.get("tenure_months",0),t.get("wh_id",""),t["id"]))
            else:
                conn.execute("INSERT INTO tenants (id,name,type,industry,contact,phone,email,tenure_months,wh_id) VALUES (?,?,?,?,?,?,?,?,?)", (t["id"],t["name"],t.get("type","Business"),t.get("industry",""),t.get("contact",""),t.get("phone",""),t.get("email",""),t.get("tenure_months",0),t.get("wh_id","")))
            _audit(conn, "tenants", t["id"], "UPSERT", t)
    st.cache_data.clear()

def save_rentals(data):
    with _db() as conn:
        existing = {r["id"] for r in conn.execute("SELECT id FROM rentals").fetchall()}
        for r in data:
            if r["id"] in existing:
                conn.execute("UPDATE rentals SET tenant_id=?,wh_id=?,start_date=?,end_date=?,monthly_rent=?,status=?,updated_at=datetime('now') WHERE id=?", (r["tenant_id"],r["wh_id"],r["start_date"],r["end_date"],r["monthly_rent"],r.get("status","Active"),r["id"]))
            else:
                conn.execute("INSERT INTO rentals (id,tenant_id,wh_id,start_date,end_date,monthly_rent,status) VALUES (?,?,?,?,?,?,?)", (r["id"],r["tenant_id"],r["wh_id"],r["start_date"],r["end_date"],r["monthly_rent"],r.get("status","Active")))
            _audit(conn, "rentals", r["id"], "UPSERT", r)
    st.cache_data.clear()

def ensure_payments_for_month(year, month):
    month_str = f"{year}-{month:02d}"
    month_ts  = pd.Timestamp(year=year, month=month, day=1)
    biz       = get_business()
    gst_rate  = biz.get("gst_rate", 18) / 100
    due_days  = biz.get("due_days", 10)
    rentals   = get_rentals()
    with _db() as conn:
        for rental in rentals:
            if rental.get("status") != "Active": continue
            try:
                start = pd.Timestamp(rental["start_date"])
                end   = pd.Timestamp(rental["end_date"])
            except Exception: continue
            if not (start <= month_ts <= end): continue
            existing = conn.execute("SELECT id FROM payments WHERE rental_id=? AND month=?", (rental["id"], month_str)).fetchone()
            if existing: continue
            rent   = float(rental["monthly_rent"])
            total  = rent + round(rent * gst_rate, 0)
            pay_id = f"PAY-{rental['id']}-{month_str}"
            conn.execute("INSERT OR IGNORE INTO payments (id,rental_id,tenant_id,wh_id,month,amount_due,payment_status) VALUES (?,?,?,?,?,?,?)", (pay_id, rental["id"], rental["tenant_id"], rental["wh_id"], month_str, total, "Pending"))
    return get_payments_for_month(year, month)

def mark_payment_paid(payment_id, amount=None):
    today = datetime.today().strftime("%Y-%m-%d")
    with _db() as conn:
        row = conn.execute("SELECT * FROM payments WHERE id=?", (payment_id,)).fetchone()
        if row:
            amt = amount if amount is not None else row["amount_due"]
            conn.execute("UPDATE payments SET payment_status='Paid',amount_paid=?,payment_date=?,updated_at=datetime('now') WHERE id=?", (amt, today, payment_id))
            _audit(conn, "payments", payment_id, "MARK_PAID", {"amount": amt, "date": today})
    st.cache_data.clear()

def mark_reminder_sent(payment_id, channel):
    now = datetime.now().isoformat()
    with _db() as conn:
        if channel == "wa":
            conn.execute("UPDATE payments SET reminder_sent_wa=1,wa_sent_at=?,updated_at=datetime('now') WHERE id=?", (now, payment_id))
        elif channel == "email":
            conn.execute("UPDATE payments SET reminder_sent_email=1,email_sent_at=?,updated_at=datetime('now') WHERE id=?", (now, payment_id))
        _audit(conn, "payments", payment_id, f"REMINDER_{channel.upper()}", {"sent_at": now})

def mark_receipt_sent(payment_id):
    with _db() as conn:
        conn.execute("UPDATE payments SET receipt_sent=1,updated_at=datetime('now') WHERE id=?", (payment_id,))
        _audit(conn, "payments", payment_id, "RECEIPT_SENT", {})

def delete_owner(owner_id):
    with _db() as conn:
        conn.execute("DELETE FROM owners WHERE id=?", (owner_id,))
        _audit(conn, "owners", owner_id, "DELETE", {})
    st.cache_data.clear()

def delete_warehouse(wh_id):
    with _db() as conn:
        conn.execute("DELETE FROM warehouses WHERE id=?", (wh_id,))
        _audit(conn, "warehouses", wh_id, "DELETE", {})
    st.cache_data.clear()

def delete_tenant(tenant_id):
    with _db() as conn:
        conn.execute("DELETE FROM tenants WHERE id=?", (tenant_id,))
        _audit(conn, "tenants", tenant_id, "DELETE", {})
    st.cache_data.clear()

def delete_rental(rental_id):
    with _db() as conn:
        conn.execute("DELETE FROM rentals WHERE id=?", (rental_id,))
        _audit(conn, "rentals", rental_id, "DELETE", {})
    st.cache_data.clear()

def _next_id(records, prefix):
    nums = []
    for r in records:
        try:
            nums.append(int(r.get("id","").replace(prefix+"-","")))
        except Exception: pass
    return f"{prefix}-{(max(nums)+1 if nums else 1):02d}"

def build_transaction_df():
    business=get_business(); owners_l=get_owners(); warehouses_l=get_warehouses()
    tenants_l=get_tenants(); rentals_l=get_rentals()
    if not rentals_l or not tenants_l: return pd.DataFrame()
    owner_map={o["id"]:o for o in owners_l}; wh_map={w["id"]:w for w in warehouses_l}
    tnt_map={t["id"]:t for t in tenants_l}
    gst_rate=business.get("gst_rate",18)/100
    size_map={"Small":1,"Medium":2,"Large":3}; type_map={"General":1,"Dry Warehouse":2,"Cold Storage":3,"Distribution Hub":4}
    ttype_map={"Individual":0,"Business":1}; rows=[]; row_num=1
    for rental in rentals_l:
        tnt_id=rental.get("tenant_id",""); wh_id=rental.get("wh_id","")
        tnt=tnt_map.get(tnt_id); wh=wh_map.get(wh_id)
        if not tnt or not wh: continue
        own=owner_map.get(wh.get("owner_id",""),{}); rent=float(rental.get("monthly_rent",0))
        gst=round(rent*gst_rate,0); total=rent+gst
        try:
            start=pd.Timestamp(rental.get("start_date","2023-01-01")); end=pd.Timestamp(rental.get("end_date","2024-12-31"))
        except Exception: continue
        months=pd.date_range(start,end,freq="MS")
        tenure=int(tnt.get("tenure_months",12))
        profile="on_time" if tenure>=36 else ("delayed" if tenure>=18 else "risky")
        np.random.seed(hash(tnt_id+wh_id)%(2**31))
        for mo in months:
            if mo>pd.Timestamp.today(): break
            due_date=mo+pd.Timedelta(days=business.get("due_days",10))
            if profile=="on_time": paid=np.random.choice([True,False],p=[0.92,0.08]); delay=0 if paid and np.random.random()>0.3 else (np.random.randint(1,8) if paid else 0)
            elif profile=="delayed": paid=np.random.choice([True,False],p=[0.78,0.22]); delay=np.random.randint(5,25) if paid else 0
            else: paid=np.random.choice([True,False],p=[0.55,0.45]); delay=np.random.randint(10,40) if paid else 0
            if paid:
                pay_date=due_date+pd.Timedelta(days=delay); pay_status="Paid"; amt_paid=int(total); balance=0
                beh="On-time" if delay==0 else ("Slightly Delayed" if delay<=10 else "Delayed")
            else:
                pay_date=None; pay_status="Not Paid"; amt_paid=0; balance=int(total); beh="Defaulted"
                delay=max(0,int((pd.Timestamp.today()-due_date).days))
            reminder="Yes" if (not paid or delay>10) else "No"
            lease_dur=max(1,int((pd.Timestamp(rental.get("end_date","2024-12-31"))-pd.Timestamp(rental.get("start_date","2023-01-01"))).days/30))
            risk=round((min(delay,90)/90*40)+({"On-time":1,"Slightly Delayed":2,"Delayed":3,"Defaulted":4}.get(beh,1)/4*40)+((1-min(tenure,48)/48)*20),1)
            if beh in ["On-time","Slightly Delayed"] and rent>=50000: seg="High-Value Regular"
            elif beh=="On-time": seg="Regular Payer"
            elif beh in ["Delayed","Slightly Delayed"]: seg="Late Payer"
            else: seg="Defaulter"
            rows.append({"Row_ID":f"TXN-{row_num:04d}","Tenant_ID":tnt_id,"Tenant_Name":tnt.get("name",""),"Owner_ID":wh.get("owner_id",""),"Owner_Name":own.get("name",""),"WH_ID":wh_id,"Warehouse_Location":wh.get("location",""),"Warehouse_State":wh.get("state",""),"Warehouse_Type":wh.get("type",""),"Warehouse_Size":wh.get("size",""),"Month":mo.strftime("%Y-%m-%d"),"Month_Name":mo.strftime("%b-%Y"),"Quarter":f"Q{((mo.month-1)//3)+1}-{mo.year}","Monthly_Rent_INR":int(rent),"GST_18pct_INR":int(gst),"Total_Invoice_INR":int(total),"Lease_Duration_Months":lease_dur,"Payment_Status":pay_status,"Payment_Date":pay_date.strftime("%Y-%m-%d") if pay_date else "","Delay_Days":int(delay),"Amount_Paid_INR":amt_paid,"Balance_Due_INR":balance,"Invoice_Sent":"Yes","Invoice_Date":mo.strftime("%Y-%m-%d"),"Due_Date":due_date.strftime("%Y-%m-%d"),"Reminder_Sent":reminder,"Email_Sent":"Yes","WhatsApp_Sent":"Yes","Tenant_Type":tnt.get("type","Business"),"Industry_Type":tnt.get("industry",""),"Payment_Behavior":beh,"Customer_Tenure_Months":tenure,"Is_Paid_Binary":1 if paid else 0,"Is_Delayed_Binary":1 if (paid and delay>0) else 0,"Revenue_Collected_INR":amt_paid,"Size_Encoded":size_map.get(wh.get("size","Medium"),2),"Type_Encoded":type_map.get(wh.get("type","Dry Warehouse"),2),"Behavior_Encoded":{"On-time":1,"Slightly Delayed":2,"Delayed":3,"Defaulted":4}.get(beh,1),"TenantType_Encoded":ttype_map.get(tnt.get("type","Business"),1),"Risk_Score":risk,"Tenant_Segment":seg,"Month_Num":(mo.year-2023)*12+mo.month,"KMeans_Cluster":0,"Cluster_Label":seg,"Tenant_Email":tnt.get("email",""),"Tenant_Phone":tnt.get("phone",""),"Contact_Person":tnt.get("contact",""),"Owner_Email":own.get("email",""),"Owner_Phone":own.get("phone","")})
            row_num+=1
    if not rows: return pd.DataFrame()
    df=pd.DataFrame(rows); df["Month"]=pd.to_datetime(df["Month"]); return df

@st.cache_data
def get_transaction_df():
    df = build_transaction_df()
    if df.empty:
        csv_path = os.path.join(DATA_DIR, "warehouse_data.csv")
        if os.path.exists(csv_path):
            df = pd.read_csv(csv_path)
            df["Month"] = pd.to_datetime(df["Month"], errors="coerce")
    return df

init_db()
