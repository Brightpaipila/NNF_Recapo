# RECAPO Intelligence System - Implementation Guide

## 📋 Table of Contents
1. [System Overview](#system-overview)
2. [Business Logic](#business-logic)
3. [Database Schema](#database-schema)
4. [Calculation Engines](#calculation-engines)
5. [Key Metrics & KPIs](#key-metrics--kpis)
6. [Running the System](#running-the-system)

---

## System Overview

**RECAPO** is a **Recovery & Collection Forecast Engine** designed to:
- Track daily payment collections from customers
- Predict expected collections based on payment schedules
- Identify customers at risk of default
- Forecast recovery amounts for planning
- Monitor contractor/agent performance

### Architecture
```
Data Flow:
Excel File (Latest Export) 
    ↓
Data Loading & Cleaning
    ↓
Expected Metrics Engine (Core KPI)
    ↓
Risk Classification Engine
    ↓
Collection, Recovery, Agent Analytics, Due Customers, Forecasting Engines
    ↓
Streamlit Dashboard Visualization
```

---

## Business Logic

### Payment Plans

The system supports two payment plan types:

#### 18-Month Plan
- **Total Amount**: 155,000 MWK
- **Installation Fee**: 6,000 MWK
- **Financed Amount**: 149,000 MWK
- **Weekly Payment**: 2,100 MWK
- **Monthly Payment**: 8,300 MWK
- **Duration**: 18 months

#### 12-Month Plan
- **Total Amount**: 155,000 MWK
- **Installation Fee**: 6,000 MWK
- **Financed Amount**: 149,000 MWK
- **Weekly Payment**: 3,000 MWK
- **Monthly Payment**: 12,000 MWK
- **Duration**: 12 months

### Customer States
- **lead**: Registration incomplete, not yet active
- **good/active**: Currently paying (target for collections)
- **paid_off/inactive**: Completed payment obligations

### Risk Categories

Based on **Days System Off** (how many days since last payment):

| Category | Days Range | Status | Action |
|----------|-----------|--------|--------|
| On Track | 0-29 | ✅ Healthy | Monitor |
| Watchlist | 30-89 | ⚠️ Moderate Risk | Follow-up |
| Medium Risk | 90-179 | ⚠️ Concerning | Attention |
| High Risk | 180-364 | 🔴 Serious | Urgent |
| Critical | 365+ | 🔴 Likely Default | Immediate |

### Flag Notation
- `!!!`: Many days (180+) - Critical default risk
- `!!`: Moderate days (90-180) - High risk
- `!`: Some days (30-90) - Medium risk
- Empty: Current/on track (0-30)

---

## Database Schema

### 1. `customers` Table
Main customer master data with payment status.

```sql
db_id INTEGER PRIMARY KEY
customer_id TEXT UNIQUE
customer_name TEXT
state TEXT
sales_product TEXT
sales_price TEXT
system_id TEXT
balance REAL
payoff_amount REAL
effective_payoff_amount REAL
left_to_pay REAL
percentage_paid REAL
days_system_off INTEGER
flags TEXT
last_token_time TEXT (Payment timestamp)
charged_until TEXT (Payment expiry date)
assigned_contractor TEXT
```

### 2. `payment_schedules` Table
Tracks payment plan details per customer.

```sql
customer_id TEXT PRIMARY KEY
plan_type TEXT (12 or 18)
total_amount REAL
weekly_payment REAL
monthly_payment REAL
start_date TEXT
end_date TEXT
```

### 3. `daily_collections` Table
Aggregate daily collection metrics.

```sql
collection_date TEXT UNIQUE
expected_collection REAL
actual_collection REAL
expected_customers INTEGER
actual_customers INTEGER
default_customers INTEGER
default_rate REAL
```

### 4. `expected_collections` Table
Expected collection details for each customer.

```sql
customer_id TEXT
collection_date TEXT
expected_amount REAL
is_overdue BOOLEAN
weeks_overdue INTEGER
status TEXT
```

### 5. `agent_performance` Table
Contractor/agent performance metrics.

```sql
contractor TEXT
reporting_date TEXT
customers_assigned INTEGER
customers_active INTEGER
customers_paid_off INTEGER
expected_collection REAL
actual_collection REAL
collection_efficiency REAL
default_rate REAL
```

---

## Calculation Engines

### 1. **Expected Engine** (`expected_engine.py`)
**Core Purpose**: Generate expected collection metrics for each customer.

**Key Functions**:
- `generate_expected_metrics(df)`: Main function enriching data with expected metrics
- `calculate_daily_expected_collection(df, target_date)`: Total expected for a day
- `get_collection_summary(df)`: High-level summary statistics

**Calculations**:

#### Weeks Overdue
```
weeks_overdue = (today - charged_until) / 7
```

#### Expected Arrears
```
expected_arrears = weeks_overdue × weekly_payment
```

#### Daily Expected Collection
For all customers where `charged_until <= target_date`:
```
daily_expected = SUM(weekly_payment)
```

#### Collection Gap
```
collection_gap = (expected_arrears / total_plan_amount) × 100%
```

---

### 2. **Risk Engine** (`risk_engine.py`)
**Purpose**: Categorize customer risk based on payment history.

**Key Functions**:
- `apply_risk_logic(df)`: Assign risk categories
- `get_risk_distribution(df)`: Risk category breakdown
- `get_portfolio_health_score(df)`: Overall portfolio health (0-100)

**Risk Score Calculation**:
- On Track: 10 points
- Watchlist: 30 points
- Medium Risk: 60 points
- High Risk: 80 points
- Critical: 95 points

---

### 3. **Collection Engine** (`collection_engine.py`)
**Purpose**: Calculate actual collection performance vs expected.

**Key Metrics**:
- Expected Total: Sum of all weekly payments
- Collected Total: Actual payments received
- Efficiency %: `(Collected / Expected) × 100`
- By Risk Category: Performance breakdown

---

### 4. **Recovery Engine** (`recovery_engine.py`)
**Purpose**: Track outstanding amounts and recovery progress.

**Key Metrics**:
- Outstanding: Total left to pay (active customers)
- Paid Off: Amount already collected
- Recovery Rate: `(Paid / Total Financed) × 100%`
- Total Arrears: Sum of all overdue amounts

---

### 5. **Agent Analytics** (`agent_analytics.py`)
**Purpose**: Monitor contractor performance.

**Key Metrics per Contractor**:
- Customers Assigned
- Customers Active
- Customers Paid Off
- Expected Weekly Collection
- Total Arrears
- High Risk Count
- On Track % (% of active customers in "On Track" status)
- Default Rate %

---

### 6. **Due Engine** (`due_engine.py`)
**Purpose**: Identify customers due for payment.

**Functions**:
- `daily_due_customers(df)`: Customers due today
- `get_urgent_followups(df)`: Top at-risk customers
- `get_payment_schedule_summary(df)`: Payment schedule breakdown
- `get_by_risk_category(df)`: Customers by risk level

---

### 7. **Forecasting Engine** (`forecasting.py`)
**Purpose**: Project future collections.

**Forecast Types**:

#### Daily Average Projection
```
daily_avg = (total_weekly / 7) × collection_rate
```

#### 30-Day Forecast
```
forecast_30_days = daily_avg × 30
```

#### Scenario Analysis
- **Optimistic**: 100% on-track pay, 30% at-risk pay
- **Realistic**: 80% on-track pay, 20% at-risk pay
- **Conservative**: 60% on-track pay, 5% at-risk pay

---

## Key Metrics & KPIs

| Metric | Formula | Interpretation |
|--------|---------|-----------------|
| Expected Weekly | SUM(weekly_payment) | Total expected from all active customers weekly |
| Daily Expected | Expected Weekly / 7 | Expected collection per day |
| Outstanding | SUM(left_to_pay) | Total amount still owed |
| Total Arrears | SUM(expected_arrears) | Sum of all missed payments |
| Collection Efficiency | (Collected / Expected) × 100% | % of expected amount actually collected |
| Default Rate | (Critical + High Risk) / Active × 100% | % of customers at serious risk |
| Portfolio Health | Avg(risk_scores) | Lower is better (0-100) |

---

## Running the System

### 1. **Setup Environment**
```bash
# Create virtual environment
python -m venv .venv

# Activate it
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. **Data Preparation**
- Place Excel export in `data/raw/` folder
- Ensure column names match expected format
- Run data cleaning in expected_engine.py

### 3. **Run Dashboard**
```bash
cd d:\Work\RECAPO\Code Base\NNF_Recapo
streamlit run app/dashboard.py
```

### 4. **Automate Data Download** (Optional)
```bash
# Start scheduler in separate terminal
python automation/scheduler.py
```
Downloads latest RECAPO export daily at 06:00 AM.

---

## Data Flow Example

**Scenario**: Customer "Tafelanji Galiyamu" with 18-month plan

**Raw Data**:
- Last token time: 2025-06-30
- Charged until: 2025-07-30
- Days system off: 281

**Processing**:

1. **Plan Detection**
   - Detect: 18-month plan
   - Weekly payment: 2,100 MWK

2. **Expected Calculation** (as of 2026-05-11)
   - Weeks overdue: (2026-05-11 - 2025-07-30) / 7 = 41 weeks
   - Expected arrears: 41 × 2,100 = 86,100 MWK

3. **Risk Classification**
   - Days system off: 281
   - Risk category: **High Risk** (180-364 range)
   - Risk flag: `!!!`

4. **Collection Impact**
   - Status: At Risk (not on schedule)
   - Collection gap: 86,100 / 155,000 = 55.5%

5. **Dashboard Display**
   - Appears in urgent follow-ups
   - Assigned to contractor: MW15 Esawo Horse
   - Requires immediate intervention

---

## Customization & Extension

### Adding New KPIs
1. Add calculation in appropriate engine (e.g., risk_engine.py)
2. Update dashboard.py to display metric
3. Document in this guide

### Integrating with External Database
1. Update `database/schema.sql` with new tables
2. Create data pipeline in `automation/`
3. Add database connection in utils/config.py

### Custom Reports
Use exported CSV files or create new functions in respective engines to generate reports.

---

## Support & Troubleshooting

### Common Issues

**Issue**: "No data available" error
- **Solution**: Ensure latest Excel file in `data/raw/`

**Issue**: Column name mismatch
- **Solution**: Check data cleaning section in dashboard.py
- Column names should match: `Customer`, `State`, `Days system off`, etc.

**Issue**: Forecast accuracy
- **Solution**: Ensure `Last token time` and `Charged until` columns are present
- Forecast improves with historical payment data

---

## Version History

- **v1.0** (2026-05-11): Initial implementation
  - Expected collection engine
  - Risk categorization
  - Basic forecasting
  - Dashboard visualization

---

**Last Updated**: 2026-05-11
**System Status**: ✅ Production Ready
