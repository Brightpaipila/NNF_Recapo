# app/collection_engine.py
"""
Collection Engine - Calculates actual collection metrics
"""

import pandas as pd


def calculate_collection_metrics(df):
    """
    Calculate collection metrics from actual data
    
    Returns:
    - Dictionary with actual collection data
    """
    
    # Total expected (from expected engine)
    expected = df["Weekly_Payment"].sum() if "Weekly_Payment" in df.columns else 0
    
    # Actual collected (from Balance reduction)
    if "Balance" in df.columns and "Payoff amount" in df.columns:
        collected = df["Payoff amount"].sum() - df["Balance"].sum()
    else:
        collected = 0
    
    # Collection efficiency
    efficiency = (collected / expected * 100) if expected > 0 else 0
    
    # By risk category
    risk_breakdown = {}
    if "Risk_Category" in df.columns:
        for risk_cat in df["Risk_Category"].unique():
            risk_df = df[df["Risk_Category"] == risk_cat]
            risk_breakdown[risk_cat] = {
                "count": len(risk_df),
                "expected": risk_df["Weekly_Payment"].sum(),
                "collected": (risk_df["Payoff amount"].sum() - risk_df["Balance"].sum()) if "Payoff amount" in risk_df.columns else 0
            }
    
    return {
        "expected_total": expected,
        "collected_total": collected,
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
    
    if "Balance" in contractor_df.columns and "Payoff amount" in contractor_df.columns:
        collected = contractor_df["Payoff amount"].sum() - contractor_df["Balance"].sum()
    else:
        collected = 0
    
    efficiency = (collected / expected * 100) if expected > 0 else 0
    
    return {
        "contractor": contractor_name,
        "customers_count": len(contractor_df),
        "expected_total": expected,
        "collected_total": collected,
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
