"""
utils.py — Shared data loading, preprocessing, and ML training utilities
Warehouse Rental Management Analytics — Data Analytics MGB Project
"""

import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings("ignore")

from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, roc_curve, confusion_matrix, classification_report,
    r2_score, mean_absolute_error, mean_squared_error
)
import streamlit as st

# ── COLOUR PALETTE ────────────────────────────────────────────────────────────
COLORS = {
    "blue":   "#1A3C5E",
    "orange": "#E8612C",
    "teal":   "#2A9D8F",
    "gold":   "#D4A017",
    "green":  "#1D8A5F",
    "red":    "#C0392B",
    "purple": "#6C3483",
    "grey":   "#64748B",
}
PALETTE = list(COLORS.values())
PLOTLY_TEMPLATE = "plotly_white"


# ── DATA LOADING ──────────────────────────────────────────────────────────────
@st.cache_data
def load_data(path: str = "warehouse_data.csv") -> pd.DataFrame:
    df = pd.read_csv(path)
    df["Month"] = pd.to_datetime(df["Month"], errors="coerce")
    df["Payment_Date"] = pd.to_datetime(df["Payment_Date"], errors="coerce")
    df["Invoice_Date"] = pd.to_datetime(df["Invoice_Date"], errors="coerce")
    df["Due_Date"] = pd.to_datetime(df["Due_Date"], errors="coerce")

    # Ensure encoded columns exist
    size_map = {"Small": 1, "Medium": 2, "Large": 3}
    type_map = {"General": 1, "Dry Warehouse": 2, "Cold Storage": 3, "Distribution Hub": 4}
    ttype_map = {"Individual": 0, "Business": 1}
    beh_map = {"On-time": 1, "Slightly Delayed": 2, "Delayed": 3, "Defaulted": 4}

    if "Size_Encoded" not in df.columns:
        df["Size_Encoded"] = df["Warehouse_Size"].map(size_map).fillna(2)
    if "Type_Encoded" not in df.columns:
        df["Type_Encoded"] = df["Warehouse_Type"].map(type_map).fillna(2)
    if "TenantType_Encoded" not in df.columns:
        df["TenantType_Encoded"] = df["Tenant_Type"].map(ttype_map).fillna(1)
    if "Behavior_Encoded" not in df.columns:
        df["Behavior_Encoded"] = df["Payment_Behavior"].map(beh_map).fillna(1)
    if "Is_Paid_Binary" not in df.columns:
        df["Is_Paid_Binary"] = (df["Payment_Status"] == "Paid").astype(int)
    if "Is_Delayed_Binary" not in df.columns:
        df["Is_Delayed_Binary"] = (df["Delay_Days"] > 0).astype(int)
    if "Risk_Score" not in df.columns:
        df["Risk_Score"] = (
            (df["Delay_Days"].clip(0, 90) / 90 * 40) +
            (df.get("Behavior_Encoded", 1) / 4 * 40) +
            ((1 - df["Customer_Tenure_Months"].clip(0, 48) / 48) * 20)
        ).round(1)
    if "Month_Num" not in df.columns:
        df["Month_Num"] = (df["Month"].dt.year - 2023) * 12 + df["Month"].dt.month
    if "Revenue_Collected_INR" not in df.columns:
        df["Revenue_Collected_INR"] = df.get("Amount_Paid_INR", df["Monthly_Rent_INR"] * df["Is_Paid_Binary"])
    if "Tenant_Segment" not in df.columns:
        def segment(row):
            if row.get("Payment_Behavior") in ["On-time", "Slightly Delayed"] and row.get("Monthly_Rent_INR", 0) >= 50000:
                return "High-Value Regular"
            elif row.get("Payment_Behavior") == "On-time":
                return "Regular Payer"
            elif row.get("Payment_Behavior") in ["Delayed", "Slightly Delayed"]:
                return "Late Payer"
            return "Defaulter"
        df["Tenant_Segment"] = df.apply(segment, axis=1)

    return df


# ── FILTER HELPER ─────────────────────────────────────────────────────────────
def apply_filters(df: pd.DataFrame, owner=None, location=None, wh_type=None,
                  pay_status=None, year=None) -> pd.DataFrame:
    out = df.copy()
    if owner and owner != "All":
        out = out[out["Owner_Name"] == owner]
    if location and location != "All":
        out = out[out["Warehouse_Location"] == location]
    if wh_type and wh_type != "All":
        out = out[out["Warehouse_Type"] == wh_type]
    if pay_status and pay_status != "All":
        out = out[out["Payment_Status"] == pay_status]
    if year and year != "All":
        out = out[out["Month"].dt.year == int(year)]
    return out


# ── CLASSIFICATION MODEL ──────────────────────────────────────────────────────
CLASSIFICATION_FEATURES = [
    "Monthly_Rent_INR", "Size_Encoded", "Type_Encoded",
    "TenantType_Encoded", "Customer_Tenure_Months",
    "Lease_Duration_Months", "Month_Num", "Risk_Score"
]

@st.cache_resource
def train_classifier(df: pd.DataFrame):
    feat = [f for f in CLASSIFICATION_FEATURES if f in df.columns]
    X = df[feat].fillna(0)
    y = df["Is_Paid_Binary"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=y
    )
    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s  = scaler.transform(X_test)

    model = RandomForestClassifier(n_estimators=150, max_depth=8,
                                   random_state=42, class_weight="balanced")
    model.fit(X_train_s, y_train)

    y_pred      = model.predict(X_test_s)
    y_prob      = model.predict_proba(X_test_s)[:, 1]
    fpr, tpr, thresholds = roc_curve(y_test, y_prob)

    metrics = {
        "accuracy":  round(accuracy_score(y_test, y_pred), 4),
        "precision": round(precision_score(y_test, y_pred, zero_division=0), 4),
        "recall":    round(recall_score(y_test, y_pred, zero_division=0), 4),
        "f1":        round(f1_score(y_test, y_pred, zero_division=0), 4),
        "roc_auc":   round(roc_auc_score(y_test, y_prob), 4),
        "fpr": fpr, "tpr": tpr,
        "cm": confusion_matrix(y_test, y_pred),
        "feature_names": feat,
        "feature_importance": model.feature_importances_,
        "report": classification_report(y_test, y_pred, output_dict=True),
        "X_test": X_test, "y_test": y_test, "y_pred": y_pred,
    }
    return model, scaler, metrics, feat


# ── REGRESSION MODEL ──────────────────────────────────────────────────────────
REGRESSION_FEATURES = ["Size_Encoded", "Type_Encoded", "Month_Num",
                        "Customer_Tenure_Months", "Lease_Duration_Months"]

@st.cache_resource
def train_rent_regressor(df: pd.DataFrame):
    feat = [f for f in REGRESSION_FEATURES if f in df.columns]
    X = df[feat].fillna(0)
    y = df["Monthly_Rent_INR"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=42
    )
    model = Ridge(alpha=1.0)
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)

    metrics = {
        "r2":   round(r2_score(y_test, y_pred), 4),
        "mae":  round(mean_absolute_error(y_test, y_pred), 2),
        "rmse": round(np.sqrt(mean_squared_error(y_test, y_pred)), 2),
        "feature_names": feat,
        "coef": model.coef_,
        "y_test": y_test, "y_pred": y_pred,
    }
    return model, metrics, feat


@st.cache_resource
def train_delay_regressor(df: pd.DataFrame):
    feat = [f for f in ["Size_Encoded", "Type_Encoded", "TenantType_Encoded",
                         "Customer_Tenure_Months", "Monthly_Rent_INR", "Risk_Score"]
            if f in df.columns]
    delayed = df[df["Delay_Days"] > 0].copy()
    if len(delayed) < 20:
        return None, {}, feat
    X = delayed[feat].fillna(0)
    y = delayed["Delay_Days"]
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=42
    )
    model = Ridge(alpha=1.0)
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)
    metrics = {
        "r2":   round(r2_score(y_test, y_pred), 4),
        "mae":  round(mean_absolute_error(y_test, y_pred), 2),
        "rmse": round(np.sqrt(mean_squared_error(y_test, y_pred)), 2),
        "y_test": y_test, "y_pred": y_pred,
    }
    return model, metrics, feat


# ── CLUSTERING ────────────────────────────────────────────────────────────────
CLUSTER_FEATURES = ["Monthly_Rent_INR", "Delay_Days",
                    "Customer_Tenure_Months", "Risk_Score", "Is_Paid_Binary"]

@st.cache_resource
def train_clustering(df: pd.DataFrame, k: int = 4):
    feat = [f for f in CLUSTER_FEATURES if f in df.columns]
    X = df[feat].fillna(0)
    scaler = StandardScaler()
    X_s = scaler.fit_transform(X)

    # Elbow data
    inertias = []
    for ki in range(2, 9):
        km = KMeans(n_clusters=ki, random_state=42, n_init=10)
        km.fit(X_s)
        inertias.append(km.inertia_)

    km_final = KMeans(n_clusters=k, random_state=42, n_init=10)
    labels = km_final.fit_predict(X_s)
    df_out = df.copy()
    df_out["KMeans_Cluster"] = labels

    # Label clusters by profile
    profile = df_out.groupby("KMeans_Cluster").agg(
        Avg_Rent=("Monthly_Rent_INR", "mean"),
        Avg_Delay=("Delay_Days", "mean"),
        Paid_Rate=("Is_Paid_Binary", "mean"),
        Count=("Row_ID", "count") if "Row_ID" in df.columns else ("Is_Paid_Binary", "count"),
    ).round(2)

    def auto_label(row):
        if row["Paid_Rate"] >= 0.9 and row["Avg_Rent"] >= 50000:
            return "High-Value Regular"
        elif row["Paid_Rate"] >= 0.85 and row["Avg_Delay"] <= 5:
            return "Regular Payer"
        elif row["Avg_Delay"] > 15:
            return "Late Payer"
        else:
            return "At-Risk"

    profile["Label"] = profile.apply(auto_label, axis=1)
    cluster_map = profile["Label"].to_dict()
    df_out["Cluster_Label"] = df_out["KMeans_Cluster"].map(cluster_map)

    return km_final, scaler, df_out, profile, inertias, feat


# ── ASSOCIATION RULES (manual — no mlxtend needed) ────────────────────────────
def compute_association_rules(df: pd.DataFrame, min_support: float = 0.05):
    """
    Compute association rules manually:
    Antecedent: Tenant_Type + Warehouse_Type
    Consequent: Payment_Behavior (Paid / Not Paid)
    Returns: support, confidence, lift
    """
    total = len(df)
    rows = []

    for ttype in df["Tenant_Type"].unique():
        for wtype in df["Warehouse_Type"].unique():
            for beh in df["Payment_Status"].unique():
                mask_ant  = (df["Tenant_Type"] == ttype) & (df["Warehouse_Type"] == wtype)
                mask_full = mask_ant & (df["Payment_Status"] == beh)

                sup_ant  = mask_ant.sum() / total
                sup_full = mask_full.sum() / total
                sup_con  = (df["Payment_Status"] == beh).sum() / total

                if sup_ant == 0 or sup_full < min_support:
                    continue

                confidence = sup_full / sup_ant
                lift       = confidence / sup_con if sup_con > 0 else 0

                rows.append({
                    "Antecedent":  f"{ttype} + {wtype}",
                    "Consequent":  beh,
                    "Support":     round(sup_full, 4),
                    "Confidence":  round(confidence, 4),
                    "Lift":        round(lift, 4),
                    "Count":       int(mask_full.sum()),
                    "Tenant_Type": ttype,
                    "WH_Type":     wtype,
                })

    rules_df = pd.DataFrame(rows).sort_values("Lift", ascending=False)
    return rules_df


# ── PROSPECT SCORING ──────────────────────────────────────────────────────────
PROSPECT_SCHEMA = {
    "Tenant_Name":            "string",
    "Tenant_Type":            ["Business", "Individual"],
    "Industry_Type":          "string",
    "Warehouse_Type":         ["Cold Storage", "Dry Warehouse", "Distribution Hub", "General"],
    "Warehouse_Size":         ["Small", "Medium", "Large"],
    "Monthly_Rent_INR":       "numeric",
    "Customer_Tenure_Months": "numeric",
    "Lease_Duration_Months":  "numeric",
}

SIZE_MAP  = {"Small": 1, "Medium": 2, "Large": 3}
TYPE_MAP  = {"General": 1, "Dry Warehouse": 2, "Cold Storage": 3, "Distribution Hub": 4}
TTYPE_MAP = {"Individual": 0, "Business": 1}

def encode_prospect(row: dict, month_num: int = 24) -> dict:
    """Encode a single prospect dict into model-ready features."""
    return {
        "Monthly_Rent_INR":       float(row.get("Monthly_Rent_INR", 0)),
        "Size_Encoded":           SIZE_MAP.get(row.get("Warehouse_Size", "Medium"), 2),
        "Type_Encoded":           TYPE_MAP.get(row.get("Warehouse_Type", "Dry Warehouse"), 2),
        "TenantType_Encoded":     TTYPE_MAP.get(row.get("Tenant_Type", "Business"), 1),
        "Customer_Tenure_Months": float(row.get("Customer_Tenure_Months", 12)),
        "Lease_Duration_Months":  float(row.get("Lease_Duration_Months", 12)),
        "Month_Num":              month_num,
        "Risk_Score":             float(row.get("Risk_Score", 30)),
    }


def score_prospects(prospects_df: pd.DataFrame, model, scaler, feat: list) -> pd.DataFrame:
    """Score a dataframe of prospects through the trained classifier."""
    size_map  = {"Small": 1, "Medium": 2, "Large": 3}
    type_map  = {"General": 1, "Dry Warehouse": 2, "Cold Storage": 3, "Distribution Hub": 4}
    ttype_map = {"Individual": 0, "Business": 1}

    df = prospects_df.copy()
    df["Size_Encoded"]      = df["Warehouse_Size"].map(size_map).fillna(2)
    df["Type_Encoded"]      = df["Warehouse_Type"].map(type_map).fillna(2)
    df["TenantType_Encoded"]= df["Tenant_Type"].map(ttype_map).fillna(1)
    df["Month_Num"]         = 25  # future period
    df["Risk_Score"]        = (
        ((1 - df["Customer_Tenure_Months"].clip(0, 48) / 48) * 40) + 20
    ).round(1)
    df["Lease_Duration_Months"] = df.get("Lease_Duration_Months", 12)

    present = [f for f in feat if f in df.columns]
    missing = [f for f in feat if f not in df.columns]
    X = df[present].copy()
    for m in missing:
        X[m] = 0
    X = X[feat].fillna(0)
    X_s = scaler.transform(X)

    proba      = model.predict_proba(X_s)[:, 1]
    prediction = model.predict(X_s)

    df["Pay_Probability"]    = proba.round(4)
    df["Predicted_Payment"]  = ["Will Pay" if p == 1 else "At Risk" for p in prediction]
    df["Risk_Tier"] = pd.cut(
        proba,
        bins=[0, 0.4, 0.7, 1.0],
        labels=["High Risk", "Medium Risk", "Low Risk"]
    )
    df["Recommended_Action"] = df["Pay_Probability"].apply(lambda p:
        "✅ Proceed — standard contract" if p >= 0.75 else
        "⚠️ Proceed with caution — increase security deposit" if p >= 0.5 else
        "🚫 High risk — require 3-month advance or decline"
    )
    return df


# ── KPI HELPERS ───────────────────────────────────────────────────────────────
def compute_kpis(df: pd.DataFrame) -> dict:
    total_inv   = df["Total_Invoice_INR"].sum()
    total_col   = df["Revenue_Collected_INR"].sum()
    total_out   = df["Balance_Due_INR"].sum()
    paid_rate   = df["Is_Paid_Binary"].mean() * 100
    avg_rent    = df["Monthly_Rent_INR"].mean()
    high_risk   = (df["Risk_Score"] > 70).sum()
    avg_delay   = df[df["Delay_Days"] > 0]["Delay_Days"].mean()
    col_rate    = (total_col / total_inv * 100) if total_inv > 0 else 0

    return {
        "total_inv":  total_inv,
        "total_col":  total_col,
        "total_out":  total_out,
        "paid_rate":  round(paid_rate, 1),
        "avg_rent":   round(avg_rent, 0),
        "high_risk":  int(high_risk),
        "avg_delay":  round(avg_delay, 1) if not np.isnan(avg_delay) else 0.0,
        "col_rate":   round(col_rate, 1),
        "n_tenants":  df["Tenant_ID"].nunique() if "Tenant_ID" in df.columns else 0,
        "n_owners":   df["Owner_ID"].nunique() if "Owner_ID" in df.columns else 0,
        "n_wh":       df["WH_ID"].nunique() if "WH_ID" in df.columns else 0,
        "total_gst":  df["GST_18pct_INR"].sum() if "GST_18pct_INR" in df.columns else 0,
    }


def inr_fmt(n: float) -> str:
    if n >= 1e7:
        return f"₹{n/1e7:.2f} Cr"
    elif n >= 1e5:
        return f"₹{n/1e5:.1f}L"
    elif n >= 1e3:
        return f"₹{n/1e3:.0f}K"
    return f"₹{n:.0f}"
