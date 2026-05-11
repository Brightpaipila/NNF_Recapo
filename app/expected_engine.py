# app/expected_engine.py
"""
Expected Collection Engine - Core KPI Calculation

This engine calculates:
1. Expected collection amount for each customer based on their plan and payment history
2. Daily expected collection (total expected from all customers due that day)
3. Overdue amounts and arrears
4. Customers expected to pay on any given day
"""

import pandas as pd
import numpy as np
from datetime import datetime
import sys
from pathlib import Path

root = Path(__file__).parent.parent
sys.path.insert(0, str(root))

from utils.helpers import (
    detect_plan,
    get_plan_config,
    calculate_weeks_overdue,
    calculate_expected_arrears,
    is_payment_due_today,
    get_days_until_due,
    get_risk_category,
    get_payment_schedule_info
)


def generate_expected_metrics(df, current_date=None):
    """
    Main function to generate expected collection metrics
    
    This enriches the dataframe with:
    - Plan detection
    - Weekly payment amount
    - Weeks overdue calculation
    - Expected arrears
    - Days until due
    - Payment due status
    - Risk category
    """
    if current_date is None:
        current_date = pd.Timestamp.now("UTC")
    
    df = df.copy()
    
    # Normalize raw export field names
    df.columns = df.columns.str.strip()
    rename_map = {
        "Pay off amount": "Payoff amount",
        "Percentage paid off": "Percentage paid",
        "Sales price": "Sales price",
        "Days system off": "Days system off",
        "Assigned to contractor": "Assigned to contractor",
        "Left to pay": "Left to pay",
        "Charged until": "Charged until"
    }
    df = df.rename(columns=rename_map)

    # Detect plan type from Sales price column
    if "Sales price" in df.columns:
        df["Plan_Type"] = df["Sales price"].apply(detect_plan)
    else:
        df["Plan_Type"] = None
    
    # Ensure date columns are datetime
    if "Charged until" in df.columns:
        df["Charged until"] = pd.to_datetime(df["Charged until"], errors="coerce", utc=True)
    
    if "Last token time" in df.columns:
        df["Last token time"] = pd.to_datetime(df["Last token time"], errors="coerce", utc=True)
    
    # Initialize expected collection columns
    df["Weekly_Payment"] = 0.0
    df["Monthly_Payment"] = 0.0
    df["Weeks_Overdue"] = 0.0
    df["Expected_Arrears"] = 0.0
    df["Days_Until_Due"] = 0
    df["Is_Due_Today"] = False
    df["Risk_Category"] = "Unknown"
    df["Expected Status"] = "Unknown"
    df["Collection Gap"] = 0.0
    
    # Only calculate for ACTIVE customers
    if "State" in df.columns:
        active_mask = df["State"].isin(["good", "active"])
    else:
        active_mask = pd.Series([True] * len(df))
    
    # Process active customers
    for idx in df[active_mask].index:
        plan_type = df.loc[idx, "Plan_Type"]
        
        if not plan_type or pd.isna(plan_type):
            continue
        
        plan = get_plan_config(plan_type)
        if not plan:
            continue
        
        # Set payment amounts
        df.loc[idx, "Weekly_Payment"] = plan.get("weekly_payment", 0)
        df.loc[idx, "Monthly_Payment"] = plan.get("monthly_payment", 0)
        
        # Calculate weeks overdue
        if "Charged until" in df.columns and pd.notna(df.loc[idx, "Charged until"]):
            weeks_overdue = calculate_weeks_overdue(df.loc[idx, "Charged until"], current_date)
            df.loc[idx, "Weeks_Overdue"] = weeks_overdue
            
            # Calculate expected arrears
            df.loc[idx, "Expected_Arrears"] = weeks_overdue * plan.get("weekly_payment", 0)
            
            # Days until due
            df.loc[idx, "Days_Until_Due"] = get_days_until_due(df.loc[idx, "Charged until"], current_date)
            
            # Is due today
            df.loc[idx, "Is_Due_Today"] = is_payment_due_today(df.loc[idx, "Charged until"], current_date)
            
            # Collection Gap (arrears as % of total plan)
            if plan.get("total_amount", 0) > 0:
                df.loc[idx, "Collection Gap"] = (df.loc[idx, "Expected_Arrears"] / plan.get("total_amount", 1) * 100)
        
        # Risk category
        if "Days system off" in df.columns:
            days_off = df.loc[idx, "Days system off"]
            if pd.notna(days_off):
                risk = get_risk_category(int(days_off))
                df.loc[idx, "Risk_Category"] = risk
                
                # Expected Status
                if risk == "On Track":
                    df.loc[idx, "Expected Status"] = "On Track"
                else:
                    df.loc[idx, "Expected Status"] = "At Risk"

    # Mark completed loans explicitly
    if "State" in df.columns:
        completed_mask = df["State"] == "paid_off"
        df.loc[completed_mask, "Risk_Category"] = "Completed"
        df.loc[completed_mask, "Expected Status"] = "Completed"
    
    return df


def calculate_daily_expected_collection(df, target_date=None):
    """
    Calculate total expected collection for a specific day
    
    This includes:
    - All customers where charged_until <= target_date
    - Expected payment amount = weekly_payment (based on plan)
    
    Parameters:
    - df: Enriched customer dataframe with expected collections calculated
    - target_date: Target collection date (default: today)
    
    Returns:
    - Dictionary with daily collection metrics
    """
    if target_date is None:
        target_date = pd.Timestamp.now("UTC").normalize()
    else:
        target_date = pd.to_datetime(target_date, utc=True).normalize()
    
    # Filter customers due for payment
    active_mask = df["State"].isin(["good", "active"]) if "State" in df.columns else pd.Series([True] * len(df))
    
    due_mask = (
        (df["Charged until"] <= target_date) & 
        active_mask
    )
    
    due_customers = df[due_mask]
    
    total_expected = due_customers["Weekly_Payment"].sum()
    total_monthly_expected = due_customers["Monthly_Payment"].sum()
    customer_count = len(due_customers)
    total_arrears = due_customers["Expected_Arrears"].sum()
    
    # Default rate (customers in high-risk categories)
    default_customers = len(due_customers[due_customers["Risk_Category"].isin(["Critical", "High Risk"])])
    default_rate = (default_customers / customer_count * 100) if customer_count > 0 else 0
    
    return {
        "date": target_date,
        "expected_collection": total_expected,
        "expected_customers": customer_count,
        "monthly_expected": total_monthly_expected,
        "total_arrears": total_arrears,
        "default_customers": default_customers,
        "default_rate": default_rate
    }


def get_contractor_expected_collection(df, contractor_name, current_date=None):
    """
    Calculate expected collection for a specific contractor/agent
    """
    if current_date is None:
        current_date = pd.Timestamp.now("UTC")
    
    # Filter by contractor
    contractor_df = df[df["Assigned to contractor"] == contractor_name].copy()
    
    if len(contractor_df) == 0:
        return {}
    
    # Active customers
    active = contractor_df[contractor_df["State"].isin(["good", "active"])]
    paid_off = contractor_df[contractor_df["State"].isin(["paid_off", "inactive"])]
    
    total_expected = active["Weekly_Payment"].sum()
    total_arrears = active["Expected_Arrears"].sum()
    customers_due = len(active[active["Is_Due_Today"]])
    
    return {
        "contractor": contractor_name,
        "customers_assigned": len(contractor_df),
        "customers_active": len(active),
        "customers_paid_off": len(paid_off),
        "total_expected_weekly": total_expected,
        "total_arrears": total_arrears,
        "customers_due_today": customers_due,
        "high_risk_count": len(active[active["Risk_Category"].isin(["Critical", "High Risk"])]),
        "on_track_rate": (len(active[active["Risk_Category"] == "On Track"]) / len(active) * 100) if len(active) > 0 else 0
    }


def get_collection_summary(df, current_date=None):
    """
    Get high-level collection summary statistics
    """
    if current_date is None:
        current_date = pd.Timestamp.now("UTC")
    
    active = df[df["State"].isin(["good", "active"])] if "State" in df.columns else df
    
    daily_metrics = calculate_daily_expected_collection(df, current_date)
    
    # Risk distribution
    risk_dist = active["Risk_Category"].value_counts().to_dict() if len(active) > 0 else {}
    
    summary = {
        "reporting_date": current_date,
        "total_customers": len(df),
        "active_customers": len(active),
        "total_outstanding": active["Left to pay"].sum() if "Left to pay" in df.columns else 0,
        "daily_expected": daily_metrics["expected_collection"],
        "monthly_expected": daily_metrics["monthly_expected"],
        "customers_due_today": daily_metrics["expected_customers"],
        "total_arrears": daily_metrics["total_arrears"],
        "default_rate": daily_metrics["default_rate"],
        "risk_distribution": risk_dist
    }
    
    return summary
