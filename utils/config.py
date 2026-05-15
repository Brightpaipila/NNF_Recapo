PLAN_RULES = {
    "12": {
        "name": "12 MONTHS PLAN",
        "duration_months": 12,
        "total_amount": 155000,
        "installation_fee": 14000,
        "financed_amount": 149000,
        "monthly_payment": 12000,
        "weekly_payment": 3000,
        "payment_frequency": "weekly"
    },
    "18": {
        "name": "18 MONTHS PLAN",
        "duration_months": 18,
        "total_amount": 155000,
        "installation_fee": 14000,
        "financed_amount": 149000,
        "monthly_payment": 8300,
        "weekly_payment": 2100,
        "payment_frequency": "weekly"
    }
}

# Flag meanings
FLAG_MEANINGS = {
    "!!!": {"days_range": (180, 999999), "description": "Many days - Critical Default"},
    "!!": {"days_range": (90, 180), "description": "Moderate days - High Risk"},
    "!": {"days_range": (30, 90), "description": "Some days - Medium Risk"},
    "": {"days_range": (0, 30), "description": "Current - On Track"}
}

# Risk categories
RISK_CATEGORIES = {
    "Critical": (365, 999999),
    "High Risk": (180, 364),
    "Medium Risk": (90, 179),
    "Watchlist": (30, 89),
    "On Track": (0, 29)
}