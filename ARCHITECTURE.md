# System Architecture & Data Flow

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        DATA SOURCES                                 │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Excel Export (Latest)      RECAPO API          Manual Upload       │
│       ↓                         ↓                    ↓              │
│  data/raw/*.xlsx        automation/        User Browser            │
│                          downloader.py                             │
└────────────────────────────────┬──────────────────────────────────┘
                                 ↓
                    ┌────────────────────────┐
                    │   DATA LOADING &       │
                    │   CLEANING             │
                    │                        │
                    │ • Strip whitespace     │
                    │ • Convert types        │
                    │ • Normalize dates      │
                    │ • Clean currencies     │
                    └────────────┬───────────┘
                                 ↓
         ┌───────────────────────────────────────────┐
         │  CORE ENGINE PIPELINE                     │
         ├───────────────────────────────────────────┤
         │                                           │
         │  1. EXPECTED ENGINE                       │
         │     ✓ Plan detection (12/18 months)       │
         │     ✓ Weekly payment lookup               │
         │     ✓ Weeks overdue calculation           │
         │     ✓ Expected arrears (CORE KPI)         │
         │     ✓ Collection gap %                    │
         │     ✓ Days until due                      │
         │                    ↓                      │
         │  2. RISK ENGINE                           │
         │     ✓ Risk categorization                 │
         │     ✓ Risk scoring (0-100)                │
         │     ✓ Portfolio health                    │
         │     ✓ Flag assignment (!!!, !!, !)        │
         │                    ↓                      │
         │  3. PARALLEL PROCESSING ═╦═              │
         │     ║                                     │
         │     ╠→ COLLECTION ENGINE                 │
         │     ║  • Actual vs Expected               │
         │     ║  • Efficiency %                     │
         │     ║  • By risk category                 │
         │     ║                                     │
         │     ╠→ RECOVERY ENGINE                   │
         │     ║  • Outstanding tracking             │
         │     ║  • Recovery rate                    │
         │     ║  • Critical cases                   │
         │     ║                                     │
         │     ╠→ AGENT ANALYTICS                   │
         │     ║  • Contractor performance           │
         │     ║  • Default rates                    │
         │     ║  • Top performers                   │
         │     ║                                     │
         │     ╠→ DUE ENGINE                        │
         │     ║  • Customers due today              │
         │     ║  • Urgent follow-ups                │
         │     ║  • Payment schedule                 │
         │     ║                                     │
         │     └→ FORECASTING ENGINE                │
         │        • Daily projection                │
         │        • 30-day forecast                 │
         │        • Scenario analysis               │
         │                                           │
         └───────────────────────┬────────────────┘
                                 ↓
              ┌──────────────────────────────┐
              │   ENRICHED DATAFRAME         │
              ├──────────────────────────────┤
              │ Original columns +           │
              │ • Plan_Type                  │
              │ • Weekly_Payment             │
              │ • Weeks_Overdue              │
              │ • Expected_Arrears ⭐         │
              │ • Risk_Category              │
              │ • Risk_Score                 │
              │ • Is_Due_Today               │
              │ • Collection_Gap             │
              │ • Days_Until_Due             │
              │ + 20+ derived fields         │
              └──────────────────┬──────────┘
                                 ↓
              ┌──────────────────────────────┐
              │   DASHBOARD (Streamlit)      │
              ├──────────────────────────────┤
              │                              │
              │ INPUT: Filters              │
              │ ├─ Contractors (multi)      │
              │ ├─ Risk Categories (multi)  │
              │ └─ Customer Status (multi)  │
              │         ↓                   │
              │ LOGIC: Real-time Filter     │
              │         ↓                   │
              │ DISPLAY: 10 Sections        │
              │ ├─ KPI Cards (5)            │
              │ ├─ Risk Distribution        │
              │ ├─ Collection Status        │
              │ ├─ Payment Schedule         │
              │ ├─ Contractor Performance   │
              │ ├─ Urgent Follow-ups        │
              │ ├─ 30-Day Forecast          │
              │ ├─ Critical Cases           │
              │ ├─ Export Options           │
              │ └─ Professional Footer      │
              │         ↓                   │
              │ OUTPUT: CSV Export          │
              │ ├─ Filtered data            │
              │ ├─ Urgent list              │
              │ └─ Critical cases           │
              │                              │
              └──────────────────────────────┘

```

---

## 🔄 Data Flow by Operation

### Operation 1: Calculate Expected Arrears (Core KPI)

```
Customer Record
    ↓
┌─────────────────────────────────────────────────┐
│ 1. Extract Plan Type from Sales Price          │
│    "18 MONTHS PLAN (155000)" → "18"            │
│                                                  │
│ 2. Lookup Weekly Payment                       │
│    Plan 18 → 2,100 MWK/week                    │
│                                                  │
│ 3. Calculate Weeks Overdue                     │
│    Weeks = (Today - Charged Until) / 7         │
│    Example: (2026-05-11 - 2025-07-30) / 7     │
│           = 286 days / 7                       │
│           = 41 weeks                           │
│                                                  │
│ 4. Calculate Expected Arrears ⭐               │
│    Arrears = 41 weeks × 2,100 MWK             │
│           = 86,100 MWK                         │
│                                                  │
│ 5. Calculate Collection Gap                    │
│    Gap % = (86,100 / 155,000) × 100           │
│        = 55.5%                                 │
│                                                  │
│ 6. Determine Risk Category                     │
│    Days system off = 281                       │
│    Range: 180-364 → HIGH RISK ⚠️               │
│                                                  │
│ 7. Assign Flag                                 │
│    281 days ≥ 180 → Flag = "!!!" (Critical)   │
└─────────────────────────────────────────────────┘
    ↓
Enriched Record with:
✓ Plan_Type = "18"
✓ Weekly_Payment = 2,100
✓ Weeks_Overdue = 41
✓ Expected_Arrears = 86,100 ⭐
✓ Collection_Gap = 55.5%
✓ Risk_Category = "High Risk"
✓ Risk_Flag = "!!!"
```

---

### Operation 2: Calculate Daily Expected Collection

```
All Enriched Customers
    ↓
┌──────────────────────────────────────────────────┐
│ FILTER: State = "good" or "active"              │
│         AND Charged Until ≤ Today                │
│                                                   │
│ Result: 30 customers are DUE TODAY              │
│                                                   │
│ DUE CUSTOMERS:                                   │
│ • Tafelanji (18-month): 2,100 MWK              │
│ • Pileti (18-month): 2,100 MWK                 │
│ • Ides (18-month): 2,100 MWK                   │
│ • Wakisoni (18-month): 2,100 MWK               │
│ • ... 26 more customers ...                    │
│                                                   │
│ TOTAL EXPECTED = 30 × 2,100 = 63,000 MWK      │
│                                                   │
│ DEFAULT CALCULATION:                            │
│ High Risk + Critical in due customers = 18     │
│ Default Rate = (18 / 30) × 100 = 60%           │
└──────────────────────────────────────────────────┘
    ↓
Daily Collection Metrics
✓ Expected Collection = 63,000 MWK
✓ Expected Customers = 30
✓ Default Rate = 60%
✓ Default Customers = 18
✓ Total Arrears = SUM of all arrears
```

---

### Operation 3: Forecast 30-Day Collection

```
Daily Expected (63,000 MWK)
    ↓
├─ Convert to Daily: 63,000 / 7 = 9,000 MWK/day
    ↓
├─ Adjust for Risk
│  Active customers: 150
│  On Track: 90
│  Collection rate: 90/150 = 60%
│  Adjusted daily: 9,000 × 0.6 = 5,400 MWK/day
    ↓
├─ Calculate Confidence
│  Critical + High Risk: 60
│  Confidence = 100 - (60/150 × 50) = 80%
    ↓
├─ Project 30 Days
│  30-Day = 5,400 × 30 × 0.8 = 129,600 MWK
    ↓
└─ Scenario Analysis
   ├─ CONSERVATIVE (60% on-track, 5% at-risk)
   │  Weekly = 50,000 × 0.6 + 20,000 × 0.05 = 31,000
   │  Monthly = 31,000 × 4 = 124,000
   │
   ├─ REALISTIC (80% on-track, 20% at-risk) ← DEFAULT
   │  Weekly = 50,000 × 0.8 + 20,000 × 0.2 = 44,000
   │  Monthly = 44,000 × 4 = 176,000
   │
   └─ OPTIMISTIC (100% on-track, 30% at-risk)
      Weekly = 50,000 × 1.0 + 20,000 × 0.3 = 56,000
      Monthly = 56,000 × 4 = 224,000

Results:
✓ Daily Projection: 9,000 MWK
✓ Conservative 30-day: 124,000 MWK
✓ Realistic 30-day: 176,000 MWK (RECOMMENDED)
✓ Optimistic 30-day: 224,000 MWK
```

---

### Operation 4: Contractor Performance Aggregation

```
All Customers
    ↓
GROUP BY: Assigned to contractor
    ↓
FOR EACH CONTRACTOR:
┌────────────────────────────────────────┐
│ MW15 Esawo Horse                       │
│                                        │
│ 1. Count Customers                    │
│    Total assigned: 45                 │
│    Active (good): 38                  │
│    Paid off: 7                        │
│                                        │
│ 2. Sum Expected Weekly                │
│    18-month (25): 25 × 2,100 = 52,500 │
│    12-month (13): 13 × 3,000 = 39,000 │
│    Total: 91,500 MWK                  │
│                                        │
│ 3. Count At-Risk                      │
│    High Risk + Critical: 12            │
│    Default Rate: 12/38 = 31.6%        │
│                                        │
│ 4. Calculate On-Track %                │
│    On Track: 18                       │
│    Percentage: 18/38 = 47.4%          │
│                                        │
│ 5. Calculate Total Arrears            │
│    SUM(Expected_Arrears): 450,000 MWK │
│                                        │
│ 6. Realistic Projection               │
│    Expected × 0.7 = 64,050 MWK/week   │
│    Monthly ≈ 256,200 MWK              │
└────────────────────────────────────────┘
    ↓
Contractor Metrics Table:
✓ Contractor | 45 assigned | 38 active | 91,500 expected | 31.6% default
✓ (Repeated for all contractors)
✓ Sorted by expected collection (highest first)
```

---

## 🎯 Dashboard Filter Flow

```
USER SELECTS FILTERS (Left Sidebar):
    ↓
┌─────────────────────────────────────────┐
│ Selected Contractors:                   │
│ ☑ MW15 Esawo Horse                      │
│ ☑ MW43 Nelson Kaposa                    │
│ ☐ MW5 Mrs Awadi                         │
│ ... (2 selected out of 20)              │
│                                         │
│ Selected Risk Categories:               │
│ ☑ On Track                              │
│ ☑ Watchlist                             │
│ ☑ Medium Risk                           │
│ ☑ High Risk                             │
│ ☐ Critical                              │
│ ... (4 selected out of 5)               │
│                                         │
│ Selected Status:                        │
│ ☑ good                                  │
│ ☑ active                                │
│ ☐ paid_off                              │
│ ... (2 selected out of 5)               │
└─────────────────────────────────────────┘
    ↓
FILTER LOGIC:
    df where:
    (Assigned_to_contractor IN selected)
    AND (Risk_Category IN selected)
    AND (State IN selected)
    ↓
FILTERED DATASET
    ↓
DASHBOARD RECALCULATES:
    ✓ KPI Cards (using filtered data)
    ✓ Risk Distribution (pie chart)
    ✓ Collection Status
    ✓ Payment Schedule
    ✓ Contractor Performance
    ✓ Urgent Follow-ups
    ✓ 30-Day Forecast
    ✓ Critical Cases
    ↓
REAL-TIME UPDATES
(All visualizations update instantly)
```

---

## 💾 Database Integration Points

```
EXCEL FILE (data/raw/*.xlsx)
    ↓
┌──────────────────────────────────┐
│ AUTOMATED PIPELINE (Future)      │
├──────────────────────────────────┤
│                                  │
│ 1. Load from Excel               │
│    ↓                             │
│ 2. Transform & Enrich            │
│    ↓                             │
│ 3. Insert/Update Customers       │
│    → customers table             │
│    ↓                             │
│ 4. Insert Payment Schedules      │
│    → payment_schedules table     │
│    ↓                             │
│ 5. Calculate Expected            │
│    → expected_collections table  │
│    ↓                             │
│ 6. Aggregate Daily Metrics       │
│    → daily_collections table     │
│    ↓                             │
│ 7. Contractor Performance        │
│    → agent_performance table     │
│    ↓                             │
│ 8. Payment History (if available)│
│    → payment_history table       │
│                                  │
└──────────────────────────────────┘
    ↓
DATABASE (6 optimized tables)
    ↓
QUERY DASHBOARD
    ↓
REAL-TIME ANALYTICS
```

---

## 🔄 Calculation Dependencies

```
INDEPENDENT CALCULATIONS:
    ├─ Plan Detection
    ├─ Weekly Payment Lookup
    └─ Days System Off Analysis

DEPENDENT ON ABOVE:
    ├─ Weeks Overdue (needs charged_until date)
    │   └─ Expected Arrears ⭐ (needs weekly_payment + weeks_overdue)
    │       └─ Collection Gap (needs expected_arrears + total_amount)
    │
    ├─ Risk Category (needs days_system_off)
    │   └─ Risk Score (needs risk_category)
    │       └─ Portfolio Health (aggregate of risk_scores)
    │
    └─ Is Due Today (needs charged_until + today's date)
        └─ Daily Expected (SUM of due customers' weekly payments)
            ├─ Default Rate (count at-risk / total due)
            ├─ 30-Day Forecast (daily × 30 × adjustments)
            └─ Contractor Aggregation (SUM by contractor)

ALL ABOVE COMBINE FOR:
    └─ Dashboard Metrics & Visualizations
```

---

## 📊 Key Metrics Hierarchy

```
LEVEL 1 - CUSTOMER METRICS:
├─ Weekly Payment (from plan)
├─ Weeks Overdue (calculation)
├─ Expected Arrears (core KPI) ⭐
├─ Collection Gap % (derived)
├─ Risk Category (classification)
├─ Days Until Due (countdown)
└─ Is Due Today (boolean)

LEVEL 2 - DAILY METRICS:
├─ Daily Expected (sum of due)
├─ Customers Due (count)
├─ Default Rate % (% at-risk)
├─ Total Arrears (sum)
└─ Collection Efficiency (actual/expected)

LEVEL 3 - CONTRACTOR METRICS:
├─ Customers Assigned (count)
├─ Customers Active (count)
├─ Expected Weekly (sum)
├─ Total Arrears (sum)
├─ Default Rate % (% at-risk)
└─ On Track % (% healthy)

LEVEL 4 - PORTFOLIO METRICS:
├─ Total Customers (count)
├─ Portfolio Health Score (0-100)
├─ Overall Expected Weekly (sum)
├─ Overall Arrears (sum)
├─ 30-Day Forecast (projection)
├─ Confidence % (reliability)
└─ Risk Distribution (breakdown)

LEVEL 5 - BUSINESS METRICS:
├─ Monthly Projection (realistic)
├─ Collection Efficiency % (actual)
├─ Recovery Rate % (progress)
└─ Default Risk % (exposure)
```

---

## 🚀 Execution Flow

```
START: app/dashboard.py
    ↓
1. Load Excel (cached 1 hour)
    ↓
2. Data Cleaning
    • Strip columns
    • Convert types
    • Normalize dates
    ↓
3. Engine Pipeline
    expected_engine.py ──┐
    risk_engine.py ──────┤─→ Enriched DF
    [7 parallel engines] │
    ↓
4. Load Filters (Sidebar)
    • Contractor selection
    • Risk category selection
    • Status selection
    ↓
5. Apply Filters
    df_filtered = df[(conditions)]
    ↓
6. Render Dashboard (10 sections)
    ├─ KPI Cards
    ├─ Risk Pie Chart
    ├─ Collection Bar
    ├─ Schedule Bar
    ├─ Contractor Table
    ├─ Urgent Dataframe
    ├─ Forecast Metrics
    ├─ Critical Dataframe
    ├─ Export Buttons
    └─ Footer
    ↓
7. User Interaction
    ├─ Change filters → Jump to step 4
    ├─ Download CSV → Generate & export
    └─ Refresh → Jump to step 1
    ↓
CONTINUOUS LOOP: Responsive to changes
```

---

**This architecture enables real-time, multi-dimensional analysis of collection patterns and risk exposure across the entire customer portfolio.**
