# app/agent_analytics.py
"""
Agent/Contractor Analytics - Performance metrics per agent
"""

import pandas as pd


def contractor_performance(df):
    """
    Calculate performance metrics for each contractor
    
    Metrics:
    - Customers assigned, active, paid-off
    - Expected recovery vs actual
    - Collection efficiency
    - Arrears/default rate
    """
    
    if "Assigned to contractor" not in df.columns:
        return pd.DataFrame()
    
    # Group by contractor
    grouped = df.groupby("Assigned to contractor").agg({
        "Customer": "count",
        "State": lambda x: sum(x.isin(["good", "active"])),
        "Weekly_Payment": "sum" if "Weekly_Payment" in df.columns else None,
        "Expected_Arrears": "sum" if "Expected_Arrears" in df.columns else None,
        "Left to pay": "sum" if "Left to pay" in df.columns else None,
        "Risk_Category": lambda x: sum(x.isin(["Critical", "High Risk"]))
    }).reset_index()
    
    # Rename columns
    grouped.columns = [
        "Contractor",
        "Customers Assigned",
        "Customers Active",
        "Expected Weekly",
        "Total Arrears",
        "Outstanding Balance",
        "High Risk Count"
    ]
    
    # Calculate derived metrics
    grouped["Paid Off"] = grouped["Customers Assigned"] - grouped["Customers Active"]
    grouped["Default Rate %"] = (grouped["High Risk Count"] / grouped["Customers Active"] * 100).round(2)
    
    # Calculate collection rate (% of active customers on track)
    on_track = df[df["Risk_Category"] == "On Track"].groupby("Assigned to contractor").size()
    grouped["On Track %"] = (on_track.values / grouped["Customers Active"].values * 100).round(2)
    
    return grouped.sort_values("Expected Weekly", ascending=False)


def get_top_performers(df, n=5):
    """Get top n performing contractors by expected recovery"""
    perf = contractor_performance(df)
    
    if len(perf) == 0:
        return pd.DataFrame()
    
    return perf.nlargest(n, "Expected Weekly")


def get_at_risk_contractors(df):
    """Get contractors with high default rates"""
    perf = contractor_performance(df)
    
    if len(perf) == 0:
        return pd.DataFrame()
    
    return perf[perf["Default Rate %"] > 20].sort_values("Default Rate %", ascending=False)


def get_contractor_customer_list(df, contractor_name):
    """Get all customers for a specific contractor with their status"""
    contractor_df = df[df["Assigned to contractor"] == contractor_name].copy()
    
    if len(contractor_df) == 0:
        return pd.DataFrame()
    
    return contractor_df[[
        "Customer",
        "State",
        "Plan_Type",
        "Weekly_Payment",
        "Expected_Arrears",
        "Risk_Category",
        "Days_Until_Due",
        "Left to pay"
    ]].sort_values("Expected_Arrears", ascending=False)
