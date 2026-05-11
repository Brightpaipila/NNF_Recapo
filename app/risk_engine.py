# app/risk_engine.py
"""
Risk Engine - Risk categorization and analysis
"""

import pandas as pd


def apply_risk_logic(df):
    """
    Apply risk categorization logic based on days system off
    
    Risk Categories:
    - On Track (0-29 days): Current on payments
    - Watchlist (30-89 days): Moderate risk
    - Medium Risk (90-179 days): Requires attention
    - High Risk (180-364 days): Serious concern
    - Critical (365+ days): Likely default
    """
    
    df = df.copy()
    
    # If Risk_Category already calculated, use it; otherwise calculate
    if "Risk_Category" not in df.columns:
        def categorize_risk(days):
            if pd.isna(days):
                return "Unknown"
            days = int(days)
            if days >= 76:
                return "76+ days"
            elif days >= 61:
                return "61-75 days"
            elif days >= 46:
                return "46-60 days"
            elif days >= 31:
                return "31-45 days"
            else:
                return "0-30 days"
        
        df["Risk_Category"] = df["Days system off"].fillna(0).apply(categorize_risk)
    
    # Add risk flags
    def get_flag(days):
        if pd.isna(days):
            return ""
        days = int(days)
        if days >= 76:
            return "!!!"
        elif days >= 61:
            return "!!"
        elif days >= 31:
            return "!"
        return ""
    
    df["Risk_Flag"] = df["Days system off"].fillna(0).apply(get_flag)
    
    # Risk score (0-100)
    df["Risk_Score"] = 0
    for idx, row in df.iterrows():
        if row["Risk_Category"] == "0-30 days":
            df.loc[idx, "Risk_Score"] = 10
        elif row["Risk_Category"] == "31-45 days":
            df.loc[idx, "Risk_Score"] = 30
        elif row["Risk_Category"] == "46-60 days":
            df.loc[idx, "Risk_Score"] = 50
        elif row["Risk_Category"] == "61-75 days":
            df.loc[idx, "Risk_Score"] = 70
        elif row["Risk_Category"] == "76+ days":
            df.loc[idx, "Risk_Score"] = 90
    
    return df


def get_risk_distribution(df):
    """
    Get distribution of customers across risk categories
    """
    if "Risk_Category" not in df.columns:
        return {}
    
    distribution = df["Risk_Category"].value_counts().to_dict()
    
    # Calculate percentages
    total = len(df)
    percentages = {k: (v/total*100) for k, v in distribution.items()}
    
    return {
        "distribution": distribution,
        "percentages": percentages,
        "total_customers": total
    }


def get_portfolio_health_score(df):
    """
    Calculate overall portfolio health score (0-100)
    Lower score = healthier portfolio
    """
    if "Risk_Score" not in df.columns:
        return 0
    
    active = df[df["State"].isin(["good", "active"])] if "State" in df.columns else df
    
    if len(active) == 0:
        return 0
    
    avg_risk_score = active["Risk_Score"].mean()
    
    return round(avg_risk_score, 2)


def get_customers_by_risk(df, risk_category):
    """
    Get all customers in a specific risk category
    """
    customers = df[df["Risk_Category"] == risk_category].copy()
    
    if len(customers) == 0:
        return pd.DataFrame()
    
    return customers[[
        "Customer",
        "Assigned to contractor",
        "Plan_Type",
        "Expected_Arrears",
        "Days system off",
        "Risk_Score",
        "Left to pay"
    ]].sort_values("Expected_Arrears", ascending=False)


def identify_recovery_opportunities(df):
    """
    Identify customers who are at risk but might be recoverable
    (Recently entered high-risk but not yet critical)
    """
    active = df[df["State"].isin(["good", "active"])] if "State" in df.columns else df
    
    # Customers in High Risk or Medium Risk category
    opportunities = active[active["Risk_Category"].isin(["High Risk", "Medium Risk"])].copy()
    
    if len(opportunities) == 0:
        return pd.DataFrame()
    
    return opportunities[[
        "Customer",
        "Assigned to contractor",
        "Plan_Type",
        "Weekly_Payment",
        "Expected_Arrears",
        "Days system off",
        "Risk_Category"
    ]].sort_values("Days system off", ascending=True).head(20)
