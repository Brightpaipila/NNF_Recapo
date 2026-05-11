# app/recovery_engine.py
"""
Recovery Engine - Tracks recovery metrics and outstanding amounts
"""

import pandas as pd


def recovery_metrics(df):
    """
    Calculate recovery metrics
    
    Returns:
    - Outstanding amounts by status
    - Recovery rate
    - Projected recovery
    """
    
    active = df[df["State"].isin(["good", "active"])] if "State" in df.columns else df
    paid_off = df[df["State"].isin(["paid_off", "inactive"])] if "State" in df.columns else pd.DataFrame()
    
    total_outstanding = active["Left to pay"].sum() if "Left to pay" in active.columns else 0
    total_paid = paid_off["Payoff amount"].sum() if "Payoff amount" in paid_off.columns else 0
    
    # Arrears breakdown
    total_arrears = active["Expected_Arrears"].sum() if "Expected_Arrears" in active.columns else 0
    
    # Recovery by plan type
    recovery_by_plan = {}
    if "Plan_Type" in active.columns:
        for plan in active["Plan_Type"].unique():
            plan_df = active[active["Plan_Type"] == plan]
            recovery_by_plan[plan] = {
                "customers": len(plan_df),
                "outstanding": plan_df["Left to pay"].sum() if "Left to pay" in plan_df.columns else 0,
                "arrears": plan_df["Expected_Arrears"].sum() if "Expected_Arrears" in plan_df.columns else 0
            }
    
    # Recovery rate (% of original amount recovered)
    total_financed = len(df) * 155000  # Total financed amount
    recovery_rate = (total_paid / total_financed * 100) if total_financed > 0 else 0
    
    return {
        "outstanding": total_outstanding,
        "paid_off": total_paid,
        "recovery_rate_percent": recovery_rate,
        "total_arrears": total_arrears,
        "active_customers": len(active),
        "paid_off_customers": len(paid_off),
        "by_plan_type": recovery_by_plan
    }


def get_recovery_by_contractor(df):
    """
    Get recovery metrics by contractor
    """
    if "Assigned to contractor" not in df.columns:
        return pd.DataFrame()
    
    recovery_data = []
    
    for contractor in df["Assigned to contractor"].unique():
        contractor_df = df[df["Assigned to contractor"] == contractor]
        active = contractor_df[contractor_df["State"].isin(["good", "active"])]
        
        if len(contractor_df) == 0:
            continue
        
        recovery_data.append({
            "contractor": contractor,
            "assigned_customers": len(contractor_df),
            "outstanding": active["Left to pay"].sum() if "Left to pay" in active.columns else 0,
            "arrears": active["Expected_Arrears"].sum() if "Expected_Arrears" in active.columns else 0,
            "customers_at_risk": len(active[active["Risk_Category"].isin(["Critical", "High Risk"])]) if "Risk_Category" in active.columns else 0
        })
    
    return pd.DataFrame(recovery_data).sort_values("outstanding", ascending=False)


def get_critical_cases(df, threshold_days=180):
    """
    Get critical cases (customers with excessive arrears)
    
    Parameters:
    - df: Customer dataframe
    - threshold_days: Days threshold for critical status
    
    Returns:
    - Dataframe with critical customers sorted by arrears
    """
    
    critical = df[
        (df["State"].isin(["good", "active"])) & 
        (df["Days system off"] >= threshold_days)
    ].copy()
    
    if len(critical) == 0:
        return pd.DataFrame()
    
    return critical[[
        "Customer",
        "Assigned to contractor",
        "Plan_Type",
        "Expected_Arrears",
        "Days system off",
        "Risk_Category",
        "Left to pay"
    ]].sort_values("Expected_Arrears", ascending=False)
