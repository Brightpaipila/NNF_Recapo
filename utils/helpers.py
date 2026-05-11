import pandas as pd
import numpy as np
from datetime import datetime
import sys
from pathlib import Path

# Add parent to path for imports
root = Path(__file__).parent.parent
sys.path.insert(0, str(root))

from utils.config import PLAN_RULES, RISK_CATEGORIES

def clean_currency(value):
    """Convert MWK currency string to float"""
    try:
        return float(
            str(value)
            .replace("MK", "")
            .replace(",", "")
            .strip()
        )
    except:
        return 0

def detect_plan(sales_price_text):
    """Extract plan type from sales price field"""
    text = str(sales_price_text).upper()
    
    if "12" in text and "MONTHS" in text:
        return "12"
    elif "18" in text and "MONTHS" in text:
        return "18"
    return None

def get_plan_config(plan_type):
    """Get plan configuration by type"""
    return PLAN_RULES.get(plan_type, {})

def calculate_weeks_overdue(charged_until_date, current_date=None):
    """Calculate number of weeks overdue"""
    if current_date is None:
        current_date = pd.Timestamp.now("UTC")
    
    try:
        charged_until = pd.to_datetime(charged_until_date, utc=True)
        weeks = (current_date - charged_until).days / 7
        return max(0, weeks)
    except:
        return 0

def calculate_expected_arrears(plan_type, charged_until_date, current_date=None):
    """
    Calculate expected arrears based on plan and charged_until date
    Expected Arrears = weeks_overdue × weekly_payment
    """
    plan = get_plan_config(plan_type)
    if not plan:
        return 0
    
    weeks_overdue = calculate_weeks_overdue(charged_until_date, current_date)
    weekly_payment = plan.get("weekly_payment", 0)
    
    return weeks_overdue * weekly_payment

def is_payment_due_today(charged_until_date, current_date=None):
    """Check if customer payment is due today"""
    if current_date is None:
        current_date = pd.Timestamp.now("UTC").normalize()
    
    try:
        charged_until = pd.to_datetime(charged_until_date, utc=True).normalize()
        return charged_until <= current_date
    except:
        return False

def get_days_until_due(charged_until_date, current_date=None):
    """Get number of days until payment is due (negative if overdue)"""
    if current_date is None:
        current_date = pd.Timestamp.now("UTC")
    
    try:
        charged_until = pd.to_datetime(charged_until_date, utc=True)
        days = (charged_until - current_date).days
        return days
    except:
        return 0

def get_risk_category(days_system_off):
    """Categorize customer risk based on days system off"""
    for category, (min_days, max_days) in RISK_CATEGORIES.items():
        if min_days <= days_system_off <= max_days:
            return category
    return "Unknown"

def determine_flag(days_system_off):
    """Determine flag based on days system off"""
    if days_system_off >= 180:
        return "!!!"
    elif days_system_off >= 90:
        return "!!"
    elif days_system_off >= 30:
        return "!"
    return ""

def calculate_default(days_system_off):
    """Determine default status"""
    risk = get_risk_category(days_system_off)
    return risk

def extract_amount_from_sales_price(sales_price_text):
    """Extract numeric amount from sales price field like '18 MONTHS PLAN (Paygo, 155000.00 MWK)'"""
    try:
        # Find numbers in the text
        import re
        amounts = re.findall(r'[\d,]+\.?\d*', str(sales_price_text))
        if amounts:
            # Get the last (and typically largest) amount
            return float(amounts[-1].replace(",", ""))
    except:
        pass
    return 0

def get_payment_schedule_info(plan_type, charged_until_date, current_date=None):
    """Get comprehensive payment schedule information"""
    if current_date is None:
        current_date = pd.Timestamp.now("UTC")
    
    plan = get_plan_config(plan_type)
    if not plan:
        return {}
    
    weeks_overdue = calculate_weeks_overdue(charged_until_date, current_date)
    expected_arrears = weeks_overdue * plan.get("weekly_payment", 0)
    days_until = get_days_until_due(charged_until_date, current_date)
    is_due = is_payment_due_today(charged_until_date, current_date)
    
    return {
        "plan_type": plan_type,
        "plan_name": plan.get("name"),
        "weekly_payment": plan.get("weekly_payment"),
        "monthly_payment": plan.get("monthly_payment"),
        "weeks_overdue": weeks_overdue,
        "expected_arrears": expected_arrears,
        "days_until_due": days_until,
        "is_payment_due": is_due,
        "payment_frequency": plan.get("payment_frequency")
    }
