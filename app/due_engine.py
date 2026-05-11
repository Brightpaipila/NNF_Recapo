# app/due_engine.py
"""
Due Engine - Identifies customers due for payment
"""

import pandas as pd


def daily_due_customers(df):
    """
    Identify customers with payments due today or overdue
    
    Returns:
    - Sorted list of customers due for payment
    """
    
    df = df.copy()
    
    # Customers due = those with charged_until <= today
    if "Is_Due_Today" in df.columns and "Expected Status" in df.columns:
        due = df[
            (df["Is_Due_Today"] == True) | 
            (df["Expected Status"] == "At Risk")
        ]
    else:
        # Fallback: use Days system off
        due = df[
            (df["Days system off"] > 7) if "Days system off" in df.columns else False
        ]
    
    if len(due) == 0:
        return pd.DataFrame()
    
    # Sort by arrears (highest first)
    if "Expected_Arrears" in due.columns:
        return due.sort_values("Expected_Arrears", ascending=False)
    elif "Collection Gap" in due.columns:
        return due.sort_values("Collection Gap", ascending=False)
    else:
        return due


def get_urgent_followups(df, top_n=20):
    """
    Get top customers requiring urgent follow-up
    
    Parameters:
    - df: Customer dataframe
    - top_n: Number of top customers to return
    
    Returns:
    - Top customers sorted by urgency (arrears amount)
    """
    
    active = df[df["State"].isin(["good", "active"])] if "State" in df.columns else df
    
    if len(active) == 0:
        return pd.DataFrame()
    
    urgent = active[active["Risk_Category"].isin(["Critical", "High Risk"])]
    
    if len(urgent) == 0:
        return pd.DataFrame()
    
    result = urgent[[
        "Customer",
        "Assigned to contractor",
        "Plan_Type",
        "Weekly_Payment",
        "Expected_Arrears",
        "Days system off",
        "Risk_Category"
    ]].sort_values("Expected_Arrears", ascending=False).head(top_n)
    
    return result


def get_by_risk_category(df):
    """
    Segment customers by risk category
    """
    if "Risk_Category" not in df.columns:
        return {}
    
    result = {}
    
    for category in df["Risk_Category"].unique():
        category_df = df[df["Risk_Category"] == category]
        active = category_df[category_df["State"].isin(["good", "active"])]
        
        result[category] = {
            "count": len(category_df),
            "active_count": len(active),
            "total_arrears": active["Expected_Arrears"].sum() if "Expected_Arrears" in active.columns else 0,
            "customers": active["Customer"].tolist() if len(active) > 0 else []
        }
    
    return result


def get_payment_schedule_summary(df):
    """
    Get summary of upcoming payments
    """
    active = df[df["State"].isin(["good", "active"])] if "State" in df.columns else df
    
    if "Days_Until_Due" not in active.columns:
        return {}
    
    # Group by days_until_due ranges
    summary = {
        "due_today": len(active[active["Days_Until_Due"] <= 0]),
        "due_this_week": len(active[(active["Days_Until_Due"] > 0) & (active["Days_Until_Due"] <= 7)]),
        "due_this_month": len(active[(active["Days_Until_Due"] > 7) & (active["Days_Until_Due"] <= 30)]),
        "due_later": len(active[active["Days_Until_Due"] > 30])
    }
    
    return summary
