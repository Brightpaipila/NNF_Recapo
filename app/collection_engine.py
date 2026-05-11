# app/collection_engine.py
"""
Collection Engine - Calculates actual collection metrics
"""

import pandas as pd


def _paid_amount(df):
    """Estimate lifetime amount collected from the account export."""
    if "Payoff amount" in df.columns and "Left to pay" in df.columns:
        payoff = pd.to_numeric(df["Payoff amount"], errors="coerce").fillna(0)
        left_to_pay = pd.to_numeric(df["Left to pay"], errors="coerce").fillna(0)
        return (payoff - left_to_pay).clip(lower=0)

    if "Balance" in df.columns:
        return pd.to_numeric(df["Balance"], errors="coerce").fillna(0).clip(lower=0)

    return pd.Series([0] * len(df), index=df.index)


def _financed_amount(df):
    if "Payoff amount" not in df.columns:
        return pd.Series([0] * len(df), index=df.index)

    return pd.to_numeric(df["Payoff amount"], errors="coerce").fillna(0).clip(lower=0)


def calculate_collection_metrics(df):
    """
    Calculate collection metrics from actual data
    
    Returns:
    - Dictionary with actual collection data
    """
    
    # Total weekly expected collection from the expected engine
    expected = df["Weekly_Payment"].sum() if "Weekly_Payment" in df.columns else 0

    # Lifetime recovered value from the raw account export.
    collected = _paid_amount(df).sum()
    financed = _financed_amount(df).sum()

    # Portfolio collection efficiency: how much of total financed value is already paid.
    efficiency = (collected / financed * 100) if financed > 0 else 0
    
    # By risk category
    risk_breakdown = {}
    if "Risk_Category" in df.columns:
        for risk_cat in df["Risk_Category"].unique():
            risk_df = df[df["Risk_Category"] == risk_cat]
            risk_collected = _paid_amount(risk_df).sum()
            risk_financed = _financed_amount(risk_df).sum()
            risk_breakdown[risk_cat] = {
                "count": len(risk_df),
                "expected": risk_df["Weekly_Payment"].sum(),
                "collected": risk_collected,
                "financed": risk_financed,
                "efficiency_percent": (risk_collected / risk_financed * 100) if risk_financed > 0 else 0
            }
    
    return {
        "expected_total": expected,
        "collected_total": collected,
        "financed_total": financed,
        "efficiency_percent": efficiency,
        "arrears_total": df["Expected_Arrears"].sum() if "Expected_Arrears" in df.columns else 0,
        "by_risk_category": risk_breakdown,
        "customers_count": len(df)
    }


def calculate_contractor_collection(df, contractor_name):
    """
    Calculate collection metrics for a specific contractor
    """
    contractor_df = df[df["Assigned to contractor"] == contractor_name]
    
    if len(contractor_df) == 0:
        return {}
    
    expected = contractor_df["Weekly_Payment"].sum() if "Weekly_Payment" in contractor_df.columns else 0
    collected = _paid_amount(contractor_df).sum()
    financed = _financed_amount(contractor_df).sum()
    efficiency = (collected / financed * 100) if financed > 0 else 0
    
    return {
        "contractor": contractor_name,
        "customers_count": len(contractor_df),
        "expected_total": expected,
        "collected_total": collected,
        "financed_total": financed,
        "efficiency_percent": efficiency,
        "arrears": contractor_df["Expected_Arrears"].sum() if "Expected_Arrears" in contractor_df.columns else 0
    }


def get_all_contractors_collection(df):
    """
    Get collection metrics for all contractors
    """
    if "Assigned to contractor" not in df.columns:
        return pd.DataFrame()
    
    contractors = df["Assigned to contractor"].dropna().unique()
    
    metrics = []
    for contractor in contractors:
        m = calculate_contractor_collection(df, contractor)
        if m:
            metrics.append(m)
    
    return pd.DataFrame(metrics).sort_values("efficiency_percent", ascending=False)
