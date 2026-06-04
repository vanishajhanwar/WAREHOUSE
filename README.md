# 🏭 WareHub Analytics — Warehouse Rental Management Dashboard

**Data Analytics MGB Project | Family Business Use Case**

A complete data analytics platform for family-owned warehouse rental businesses.
Manage tenants, send invoices via WhatsApp & Email, and get ML-powered insights.

---

## 🚀 Deploy on Streamlit Cloud (3 steps)

1. **Upload to GitHub** — Create a new public repo, upload all files to the root (no subfolders)
2. **Go to** [share.streamlit.io](https://share.streamlit.io) → New App → select repo → main file: `app.py`
3. **Deploy** — live in ~2 minutes

---

## 📁 Files (all at root level)

| File | Purpose |
|------|---------|
| `app.py` | Main Streamlit app — all 12 pages |
| `utils.py` | ML models, data loading, helper functions |
| `charts.py` | All 25+ Plotly chart functions |
| `notifications.py` | Invoice & reminder generator + sender |
| `settings.py` | WhatsApp (UltraMsg) & Gmail credential management |
| `data_manager.py` | JSON-based persistent data store |
| `admin.py` | Admin panel — manage owners, warehouses, tenants |
| `warehouse_data.csv` | Sample dataset (fallback if no admin data yet) |
| `requirements.txt` | All Python dependencies |
| `.streamlit/config.toml` | Theme settings |

---

## 🗂️ How to Use the Admin Panel

Go to **🗂️ Admin — Manage Data** in the sidebar:

1. **Business Profile** — Enter your name, phone (+91 9571789145), email, bank details, GSTIN. These auto-fill the invoice templates and Settings page.
2. **Owners** — Add all family members who own warehouses
3. **Warehouses** — Add each property with location, type, size
4. **Tenants** — Add each tenant with their WhatsApp number and email
5. **Rentals** — Link tenants to warehouses with rent amount and dates

The analytics dataset rebuilds automatically from this data.

---

## 📨 Invoice & Reminder Workflow

1. Go to **⚙️ Settings** — paste your Gmail App Password and UltraMsg token
2. Go to **📨 Invoice & Reminders** — select month → send invoices
3. Overdue tenants are automatically detected → one-click reminder send

### WhatsApp Setup (UltraMsg — 5 minutes)
- Sign up at [ultramsg.com](https://ultramsg.com)
- Create instance → scan QR with your phone (+91 9571789145)
- Copy Instance ID and Token → paste in ⚙️ Settings

### Gmail Setup (3 minutes)
- Go to [myaccount.google.com/security](https://myaccount.google.com/security)
- Enable 2-Step Verification → Search "App Passwords" → Generate → paste in ⚙️ Settings

---

## 📊 Analytics Modules

| Page | Analysis Type | Techniques |
|------|--------------|-----------|
| Overview | Descriptive | KPIs, trends, segments |
| Revenue Analysis | Descriptive | Owner/location/quarterly |
| Diagnostic Analysis | Diagnostic | Pearson r, correlation heatmap |
| Classification | Predictive | Random Forest — Accuracy, Precision, Recall, F1, ROC-AUC |
| Regression | Predictive | Ridge Regression — rent & delay prediction |
| Clustering | Predictive | K-Means K=4 with elbow method |
| Association Rules | Predictive | Support, Confidence, Lift |
| Prospect Scoring | Prescriptive | Upload CSV → ML scoring |

---

*Data Analytics MGB Project — Family Warehouse Rental Management System*
