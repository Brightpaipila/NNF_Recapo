import pandas as pd
import numpy as np
import re
from datetime import datetime
from difflib import SequenceMatcher
import sys
from pathlib import Path
from typing import List, Optional

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


def normalize_text(value: object) -> str:
    """Normalize text for duplicate matching."""
    if pd.isna(value):
        return ""
    text = str(value).lower().strip()
    text = re.sub(r"[^a-z0-9\s]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text


def normalize_phone(value: object) -> str:
    """Normalize phone numbers for duplicate detection."""
    if pd.isna(value):
        return ""
    text = str(value)
    return re.sub(r"[^0-9]", "", text)


def safe_column(df: pd.DataFrame, candidates: List[str]) -> Optional[str]:
    """Find the best matching column name from the dataframe."""
    lower_columns = {col.lower().strip(): col for col in df.columns}
    for candidate in candidates:
        candidate_key = candidate.lower().strip()
        if candidate_key in lower_columns:
            return lower_columns[candidate_key]
    for col in df.columns:
        lower_col = col.lower()
        if any(candidate.lower().strip() in lower_col for candidate in candidates):
            return col
    return None


def build_duplicate_audit_table(
    df: pd.DataFrame,
    customer_column: Optional[str] = None,
    phone_column: Optional[str] = None,
    contractor_column: Optional[str] = None,
) -> pd.DataFrame:
    """Build a duplicate audit table for similar customer records."""
    if df is None or df.empty:
        return pd.DataFrame()

    customer_column = customer_column or safe_column(df, ["customer", "customer name"])
    phone_column = phone_column or safe_column(df, ["phone", "phone number", "customer phone", "mobile", "mobile number", "telephone"])
    contractor_column = contractor_column or safe_column(df, ["assigned to contractor", "contractor", "agent", "dsa"])

    display_columns = [
        "Duplicate Field",
        "Duplicate Value",
        "Customer",
        "Customer phone numbers",
        "Assigned to contractor",
        "State",
        "Balance",
        "Left to pay",
        "Days system off",
        "Location area 1",
        "Location area 2",
        "Location address",
    ]

    duplicate_rows = []

    def add_duplicate_entries(rows: pd.DataFrame, field: str, value: str):
        for _, row in rows.iterrows():
            duplicate_rows.append(
                {
                    "Duplicate Field": field,
                    "Duplicate Value": value,
                    "Customer": row.get(customer_column, "") if customer_column else "",
                    "Customer phone numbers": row.get(phone_column, "") if phone_column else "",
                    "Assigned to contractor": row.get(contractor_column, "") if contractor_column else "",
                    "State": row.get("State", ""),
                    "Balance": row.get("Balance", ""),
                    "Left to pay": row.get("Left to pay", ""),
                    "Days system off": row.get("Days system off", ""),
                    "Location area 1": row.get("Location area 1", ""),
                    "Location area 2": row.get("Location area 2", ""),
                    "Location address": row.get("Location address", ""),
                }
            )

    if phone_column:
        df["_norm_phone"] = df[phone_column].apply(normalize_phone)
        phone_counts = df["_norm_phone"].value_counts()
        duplicate_phone_values = phone_counts[phone_counts > 1].index.tolist()
        if duplicate_phone_values:
            phone_dups = df[df["_norm_phone"].isin(duplicate_phone_values)].copy()
            for phone_value in duplicate_phone_values:
                rows = phone_dups[phone_dups["_norm_phone"] == phone_value]
                add_duplicate_entries(rows, "Phone Number", rows.iloc[0].get(phone_column, ""))

    if customer_column:
        df["_norm_name"] = df[customer_column].apply(normalize_text)
        name_counts = df["_norm_name"].value_counts()
        duplicate_name_values = name_counts[name_counts > 1].index.tolist()
        if duplicate_name_values:
            name_dups = df[df["_norm_name"].isin(duplicate_name_values)].copy()
            for name_value in duplicate_name_values:
                rows = name_dups[name_dups["_norm_name"] == name_value]
                add_duplicate_entries(rows, "Customer", rows.iloc[0].get(customer_column, ""))

        unique_names = df["_norm_name"].dropna().unique().tolist()
        similar_pairs = []
        for i in range(len(unique_names)):
            for j in range(i + 1, len(unique_names)):
                name_a = unique_names[i]
                name_b = unique_names[j]
                if not name_a or not name_b:
                    continue
                if name_a.split(" ")[0] != name_b.split(" ")[0]:
                    continue
                ratio = SequenceMatcher(None, name_a, name_b).ratio()
                if ratio >= 0.72:
                    similar_pairs.append((name_a, name_b))

        for name_a, name_b in similar_pairs:
            rows = df[df["_norm_name"].isin([name_a, name_b])].copy()
            add_duplicate_entries(rows, "Similar Customer Name", f"{name_a} <> {name_b}")

    if not duplicate_rows:
        return pd.DataFrame(columns=display_columns)

    duplicate_df = pd.DataFrame(duplicate_rows)
    duplicate_df = duplicate_df.drop_duplicates().reset_index(drop=True)
    return duplicate_df.reindex(columns=display_columns).fillna("")


def build_duplicate_phones_table(
    df: pd.DataFrame,
    phone_column: Optional[str] = None,
    customer_column: Optional[str] = None,
    contractor_column: Optional[str] = None,
) -> pd.DataFrame:
    """Build a duplicate audit table for duplicate phone numbers only."""
    if df is None or df.empty:
        return pd.DataFrame()

    phone_column = phone_column or safe_column(df, ["phone", "phone number", "customer phone", "mobile", "mobile number", "telephone"])
    customer_column = customer_column or safe_column(df, ["customer", "customer name"])
    contractor_column = contractor_column or safe_column(df, ["assigned to contractor", "contractor", "agent", "dsa"])

    display_columns = [
        "Customer phone numbers",
        "Customer ",
        "Assigned to contractor",
        "State",
        "System",
        "Balance",
        "Left to pay",
        "Days system off",
        "Location area 1",
        "Location area 2",
        "Location address",
    ]

    duplicate_rows = []

    if phone_column:
        df = df.copy()
        df["_norm_phone"] = df[phone_column].apply(normalize_phone)
        phone_counts = df["_norm_phone"].value_counts()
        duplicate_phone_values = phone_counts[phone_counts > 1].index.tolist()
        
        if duplicate_phone_values:
            phone_dups = df[df["_norm_phone"].isin(duplicate_phone_values)].copy()
            for phone_value in duplicate_phone_values:
                rows = phone_dups[phone_dups["_norm_phone"] == phone_value]
                for _, row in rows.iterrows():
                    duplicate_rows.append(
                        {
                            "Customer phone numbers": row.get(phone_column, "") if phone_column else "",
                            "Customer": row.get(customer_column, "") if customer_column else "",
                            "Assigned to contractor": row.get(contractor_column, "") if contractor_column else "",
                            "State": row.get("State", ""),
                            "System": row.get("System", ""),
                            "Balance": row.get("Balance", ""),
                            "Left to pay": row.get("Left to pay", ""),
                            "Days system off": row.get("Days system off", ""),
                            "Location area 1": row.get("Location area 1", ""),
                            "Location area 2": row.get("Location area 2", ""),
                            "Location address": row.get("Location address", ""),
                        }
                    )

    if not duplicate_rows:
        return pd.DataFrame(columns=display_columns)

    duplicate_df = pd.DataFrame(duplicate_rows)
    duplicate_df = duplicate_df.drop_duplicates().reset_index(drop=True)
    return duplicate_df.reindex(columns=display_columns).fillna("")


def build_duplicate_names_table(
    df: pd.DataFrame,
    customer_column: Optional[str] = None,
    phone_column: Optional[str] = None,
    contractor_column: Optional[str] = None,
) -> pd.DataFrame:
    """Build a duplicate audit table for duplicate/similar customer only."""
    if df is None or df.empty:
        return pd.DataFrame()

    customer_column = customer_column or safe_column(df, ["customer", "customer name"])
    phone_column = phone_column or safe_column(df, ["phone", "phone number", "customer phone", "mobile", "mobile number", "telephone"])
    contractor_column = contractor_column or safe_column(df, ["assigned to contractor", "contractor", "agent", "dsa"])

    display_columns = [
        "Duplicate Type",
        "Customer",
        "Customer phone numbers",
        "Assigned to contractor",
        "State",
        "System",
        "Balance",
        "Left to pay",
        "Days system off",
        "Location area 1",
        "Location area 2",
        "Location address",
    ]

    duplicate_rows = []

    if customer_column:
        df = df.copy()
        df["_norm_name"] = df[customer_column].apply(normalize_text)
        
        # Exact matches
        name_counts = df["_norm_name"].value_counts()
        duplicate_name_values = name_counts[name_counts > 1].index.tolist()
        if duplicate_name_values:
            name_dups = df[df["_norm_name"].isin(duplicate_name_values)].copy()
            for name_value in duplicate_name_values:
                rows = name_dups[name_dups["_norm_name"] == name_value]
                for _, row in rows.iterrows():
                    duplicate_rows.append(
                        {
                            "Duplicate Type": "Exact Match",
                            "Customer": row.get(customer_column, "") if customer_column else "",
                            "Phone Number": row.get(phone_column, "") if phone_column else "",
                            "Assigned to contractor": row.get(contractor_column, "") if contractor_column else "",
                            "State": row.get("State", ""),
                            "System": row.get("System", ""),
                            "Balance": row.get("Balance", ""),
                            "Left to pay": row.get("Left to pay", ""),
                            "Days system off": row.get("Days system off", ""),
                            "Location area 1": row.get("Location area 1", ""),
                            "Location area 2": row.get("Location area 2", ""),
                            "Location address": row.get("Location address", ""),
                        }
                    )

        # Similar matches (by first name and similarity ratio)
        unique_names = df["_norm_name"].dropna().unique().tolist()
        similar_pairs = []
        for i in range(len(unique_names)):
            for j in range(i + 1, len(unique_names)):
                name_a = unique_names[i]
                name_b = unique_names[j]
                if not name_a or not name_b:
                    continue
                if name_a.split(" ")[0] != name_b.split(" ")[0]:
                    continue
                ratio = SequenceMatcher(None, name_a, name_b).ratio()
                if ratio >= 0.72:
                    similar_pairs.append((name_a, name_b))

        for name_a, name_b in similar_pairs:
            rows = df[df["_norm_name"].isin([name_a, name_b])].copy()
            for _, row in rows.iterrows():
                duplicate_rows.append(
                    {
                        "Duplicate Type": "Similar Name",
                        "Customer": row.get(customer_column, "") if customer_column else "",
                        "Phone Number": row.get(phone_column, "") if phone_column else "",
                        "Assigned to contractor": row.get(contractor_column, "") if contractor_column else "",
                        "State": row.get("State", ""),
                        "System": row.get("System", ""),
                        "Balance": row.get("Balance", ""),
                        "Left to pay": row.get("Left to pay", ""),
                        "Days system off": row.get("Days system off", ""),
                        "Location area 1": row.get("Location area 1", ""),
                        "Location area 2": row.get("Location area 2", ""),
                        "Location address": row.get("Location address", ""),
                    }
                )

    if not duplicate_rows:
        return pd.DataFrame(columns=display_columns)

    duplicate_df = pd.DataFrame(duplicate_rows)
    duplicate_df = duplicate_df.drop_duplicates().reset_index(drop=True)
    return duplicate_df.reindex(columns=display_columns).fillna("")
