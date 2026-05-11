# app/forecasting.py
"""
Forecasting Engine - Project future collections
"""

import numpy as np
import pandas as pd


def forecast_recovery(df, days_ahead=30):
    """
    Forecast recovery/collections for next N days
    
    Parameters:
    - df: Customer dataframe (must have Weekly_Payment, Risk_Category)
    - days_ahead: Number of days to forecast (default 30)
    
    Returns:
    - Dictionary with forecast data
    """
    
    if "Weekly_Payment" not in df.columns:
        return {"daily_avg": 0, f"forecast_{days_ahead}_days": 0}
    
    active = df[df["State"].isin(["good", "active"])] if "State" in df.columns else df
    
    # Current weekly expectation
    total_weekly = active["Weekly_Payment"].sum()
    daily_avg = total_weekly / 7  # Average per day
    
    # Adjust for risk (Critical/High Risk customers less likely to pay)
    if "Risk_Category" in active.columns:
        on_track = len(active[active["Risk_Category"] == "On Track"])
        total_active = len(active)
        collection_rate = (on_track / total_active) if total_active > 0 else 0.5
        daily_avg = daily_avg * collection_rate
    
    # Forecast for period
    forecast_amount = daily_avg * days_ahead
    
    # Confidence level (based on risk distribution)
    if "Risk_Category" in active.columns:
        critical_count = len(active[active["Risk_Category"].isin(["Critical", "High Risk"])])
        confidence = 100 - (critical_count / total_active * 50) if total_active > 0 else 50
    else:
        confidence = 50
    
    return {
        "daily_avg": round(daily_avg, 2),
        f"forecast_{days_ahead}_days": round(forecast_amount, 2),
        "confidence_percent": round(confidence, 2),
        "weekly_projection": round(total_weekly * 0.7, 2),  # Conservative estimate
        "monthly_projection": round(total_weekly * 4 * 0.7, 2)
    }


def forecast_by_contractor(df, contractor_name, days_ahead=30):
    """
    Forecast collections for a specific contractor
    """
    contractor_df = df[df["Assigned to contractor"] == contractor_name].copy()
    active = contractor_df[contractor_df["State"].isin(["good", "active"])]
    
    if len(active) == 0:
        return {}
    
    if "Weekly_Payment" not in active.columns:
        return {}
    
    total_weekly = active["Weekly_Payment"].sum()
    daily_avg = total_weekly / 7
    
    # Risk adjustment
    if "Risk_Category" in active.columns:
        on_track = len(active[active["Risk_Category"] == "On Track"])
        collection_rate = (on_track / len(active))
        daily_avg = daily_avg * collection_rate
    
    forecast_amount = daily_avg * days_ahead
    
    return {
        "contractor": contractor_name,
        "daily_projection": round(daily_avg, 2),
        f"forecast_{days_ahead}_days": round(forecast_amount, 2),
        "active_customers": len(active)
    }


def get_collection_trend(df, historical_days=90):
    """
    Analyze collection trends over historical period
    
    Note: This requires actual collected amounts in data
    Can be enhanced with real transaction history
    """
    
    # For now, return expected vs risk projection
    if "Risk_Category" not in df.columns:
        return {}
    
    active = df[df["State"].isin(["good", "active"])] if "State" in df.columns else df
    
    # Simulate trend based on risk category improvement needed
    risk_dist = active["Risk_Category"].value_counts().to_dict()
    
    trend = {
        "reporting_period": "Last 90 days",
        "risk_distribution": risk_dist,
        "trend_indicator": "Stable",  # Can be updated with real data
        "customers_moved_to_on_track": 0,  # Needs real transaction data
        "customers_moved_to_risk": 0  # Needs real transaction data
    }
    
    return trend


def scenario_analysis(df, scenario_type="conservative"):
    """
    Run scenario analysis for different payment collection scenarios
    
    Scenarios:
    - optimistic: 100% of on-track customers pay
    - realistic: 70% of on-track + 20% of at-risk pay
    - conservative: 50% of on-track + 5% of at-risk pay
    """
    
    active = df[df["State"].isin(["good", "active"])] if "State" in df.columns else df
    
    if "Risk_Category" not in active.columns or "Weekly_Payment" not in active.columns:
        return {}
    
    on_track = active[active["Risk_Category"] == "On Track"]
    at_risk = active[active["Risk_Category"].isin(["High Risk", "Critical", "Medium Risk"])]
    
    on_track_collection = on_track["Weekly_Payment"].sum()
    at_risk_collection = at_risk["Weekly_Payment"].sum()
    
    scenarios = {
        "optimistic": {
            "on_track_rate": 1.0,
            "at_risk_rate": 0.3,
            "weekly_collection": on_track_collection * 1.0 + at_risk_collection * 0.3,
            "monthly_projection": (on_track_collection * 1.0 + at_risk_collection * 0.3) * 4
        },
        "realistic": {
            "on_track_rate": 0.8,
            "at_risk_rate": 0.2,
            "weekly_collection": on_track_collection * 0.8 + at_risk_collection * 0.2,
            "monthly_projection": (on_track_collection * 0.8 + at_risk_collection * 0.2) * 4
        },
        "conservative": {
            "on_track_rate": 0.6,
            "at_risk_rate": 0.05,
            "weekly_collection": on_track_collection * 0.6 + at_risk_collection * 0.05,
            "monthly_projection": (on_track_collection * 0.6 + at_risk_collection * 0.05) * 4
        }
    }
    
    return scenarios.get(scenario_type, scenarios["realistic"])
