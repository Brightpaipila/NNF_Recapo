# Expected Collection Calculations - Detailed Reference

## 📊 Overview

The Expected Collection Engine is the **core KPI** of RECAPO Intelligence. It calculates:
1. How much each customer should pay weekly
2. How much they owe in arrears (missed payments)
3. Who is due for payment today
4. Total expected collection for any given day

---

## Core Formula: Expected Arrears

```
Expected Arrears = Weeks Overdue × Weekly Payment
```

### Step 1: Detect Plan Type

From the `Sales price` field which contains text like:
- "18 MONTHS PLAN (Paygo, 155000.00 MWK)"
- "12 MONTHS PLAN (Paygo, 155000.00 MWK)"

**Extract**: 18 or 12

### Step 2: Get Weekly Payment

From plan configuration:
- **18-Month**: 2,100 MWK/week
- **12-Month**: 3,000 MWK/week

### Step 3: Calculate Weeks Overdue

```
Weeks Overdue = (Today - Charged Until) / 7
```

Where:
- **Today**: Current date (2026-05-11)
- **Charged Until**: Date when current payment expires (from data)

### Step 4: Calculate Arrears

```
Expected Arrears = Weeks Overdue × Weekly Payment
```

---

## Worked Examples

### Example 1: Tafelanji Galiyamu (18-Month Plan)

**Raw Data**:
```
Sales price: 18 MONTHS PLAN (Paygo, 155000.00 MWK)
Last token time: 2025-06-30 08:31:44 UTC
Charged until: 2025-07-30 08:31:44 UTC
Days system off: 281
State: good
```

**Calculation** (as of 2026-05-11):

1. **Plan Detection**
   - Extract from Sales price: "18 MONTHS"
   - Plan type: 18
   - Weekly payment: **2,100 MWK**

2. **Weeks Overdue**
   ```
   Weeks = (2026-05-11 - 2025-07-30) / 7 days
   Weeks = 286 days / 7
   Weeks = 40.86 weeks ≈ 41 weeks
   ```

3. **Expected Arrears**
   ```
   Arrears = 41 weeks × 2,100 MWK/week
   Arrears = 86,100 MWK
   ```

4. **Collection Gap**
   ```
   Gap % = (86,100 / 155,000) × 100
   Gap % = 55.5%
   ```

5. **Risk Classification**
   ```
   Days system off: 281
   Range: 180-364 → High Risk
   Flag: !!! (many days without payment)
   ```

---

### Example 2: Ides Sidon (18-Month Plan)

**Raw Data**:
```
Sales price: 18 MONTHS PLAN (Paygo, 155000.00 MWK)
Last token time: 2025-11-06 08:21:59 UTC
Charged until: 2025-12-03 08:21:59 UTC
Days system off: 155
State: good
```

**Calculation**:

1. **Plan Detection**
   - Weekly payment: **2,100 MWK**

2. **Weeks Overdue**
   ```
   Weeks = (2026-05-11 - 2025-12-03) / 7
   Weeks = 160 days / 7
   Weeks = 22.86 weeks ≈ 23 weeks
   ```

3. **Expected Arrears**
   ```
   Arrears = 23 weeks × 2,100 MWK
   Arrears = 48,300 MWK
   ```

4. **Risk Classification**
   ```
   Days system off: 155
   Range: 90-179 → Medium Risk
   Flag: !!
   ```

---

### Example 3: Chikondi Phiri (18-Month Plan - On Track)

**Raw Data**:
```
Sales price: 18 MONTHS PLAN (Paygo, 155000.00 MWK)
Last token time: 2026-04-21 16:18:19 UTC
Charged until: 2026-05-22 16:18:19 UTC
Days system off: 0
State: good
```

**Calculation**:

1. **Plan Detection**
   - Weekly payment: **2,100 MWK**

2. **Weeks Overdue**
   ```
   Weeks = (2026-05-11 - 2026-05-22) / 7
   Weeks = -11 days / 7
   Weeks = -1.57 weeks → 0 weeks (not yet overdue!)
   ```

3. **Expected Arrears**
   ```
   Arrears = 0 weeks × 2,100 MWK
   Arrears = 0 MWK (On schedule)
   ```

4. **Risk Classification**
   ```
   Days system off: 0
   Range: 0-29 → On Track
   Flag: (none)
   ```

5. **Status**
   - ✅ **On Track** - Not yet due
   - Payment due: 2026-05-22 (11 days from today)
   - No arrears

---

## Daily Expected Collection Calculation

### Formula

For a target date (usually today):

```
Daily Expected = SUM(Weekly Payment) 
                  for all customers where:
                  - Charged Until ≤ Target Date
                  - State = "good" or "active"
```

### Example: Expected Collection for 2026-05-11

**Active Customers Due**:
1. Tafelanji: 2,100 MWK
2. Pileti: 2,100 MWK  
3. Ides: 2,100 MWK
4. Wakisoni: 2,100 MWK
5. ... (27 more customers overdue)

**Total Expected for Today**:
```
Expected = 30 customers × 2,100 MWK (avg)
Expected ≈ 63,000 MWK
```

**Default Rate**:
```
High Risk + Critical customers = 18
Default Rate = (18 / 30) × 100 = 60%
```

---

## Weekly Expected Calculation

### Formula

```
Weekly Expected = Daily Expected × 7
```

For the example above:
```
Weekly = 63,000 × 7 = 441,000 MWK
```

This represents the **target collection for the week** if all due customers pay on schedule.

---

## Monthly Expected Calculation

### Formula (Realistic)

Since payment patterns vary:

```
Monthly Realistic = (Weekly Expected × 4) × 0.7
```

The **0.7 factor** accounts for:
- Collections not happening exactly on schedule
- Some customers delaying payment
- Default risk

For the example:
```
Monthly Realistic = (441,000 × 4) × 0.7 = 1,234,800 MWK
```

---

## 30-Day Forecast

### Formula

```
30-Day Forecast = Daily Avg × 30 × Confidence %
```

Where:
- **Daily Avg**: Expected collection per day
- **Confidence %**: Based on portfolio health (0-100%)

### Confidence Calculation

```
Confidence % = 100 - (Critical + High Risk count / Active count × 50)
```

**Example**:
```
Active customers: 200
High Risk + Critical: 60

Confidence = 100 - (60 / 200 × 50)
Confidence = 100 - 15 = 85%

30-Day Forecast = 9,000 × 30 × 0.85 = 229,500 MWK
```

---

## Expected vs Actual Collection

### Efficiency Metric

```
Collection Efficiency = (Actual Collected / Expected Amount) × 100%
```

### By Risk Category

Each risk category has expected vs actual:

```
On Track:
  Expected: 50,000 MWK
  Actual: 48,000 MWK
  Efficiency: 96%

Medium Risk:
  Expected: 30,000 MWK
  Actual: 15,000 MWK
  Efficiency: 50%

High Risk:
  Expected: 25,000 MWK
  Actual: 2,000 MWK
  Efficiency: 8%
```

---

## Contractor-Level Expected Collection

### Formula

```
Contractor Expected = SUM(Weekly Payment)
                      for customers assigned to contractor
                      where State = "good" or "active"
```

### Example: Contractor "MW15 Esawo Horse"

**Customers Assigned**: 45
- Active: 38
- Paid off: 7

**Active Breakdown by Plan**:
- 18-Month (25 customers): 25 × 2,100 = 52,500 MWK
- 12-Month (13 customers): 13 × 3,000 = 39,000 MWK

**Total Expected Weekly**: 91,500 MWK
**High Risk/Critical**: 12 customers
**Default Rate**: (12 / 38) × 100 = 31.6%

---

## Collection Gap Percentage

### Formula

```
Collection Gap % = (Expected Arrears / Total Plan Amount) × 100%
```

**Interpretation**:
- **0-5%**: Acceptable (one missed payment)
- **5-20%**: Concerning (multiple missed)
- **20-50%**: Serious (significant arrears)
- **50%+**: Critical (likely default)

### Examples

**Customer A**: 
```
Arrears: 8,400 MWK (4 weeks missed)
Gap: (8,400 / 155,000) = 5.4% - Concerning
```

**Customer B**:
```
Arrears: 86,100 MWK (41 weeks missed)
Gap: (86,100 / 155,000) = 55.5% - Critical
```

---

## Portfolio Health Score

### Formula

```
Portfolio Health = Average Risk Score across all customers

Score Range: 0-100
- 0-20: Excellent
- 20-40: Good
- 40-60: Fair
- 60-80: Poor
- 80-100: Critical
```

**Lower score = healthier portfolio**

### Calculation

Risk points per category:
- On Track: 10
- Watchlist: 30
- Medium Risk: 60
- High Risk: 80
- Critical: 95

---

## Key Insights from Calculations

### 1. Arrears Compound

Each week of missed payment adds more arrears:
```
Week 1: 2,100
Week 2: 4,200
Week 4: 8,400
Week 8: 16,800
Week 16: 33,600
Week 41: 86,100
```

### 2. Risk Escalates Quickly

```
Day 30 → Watchlist (first flag!)
Day 90 → Medium Risk (!! flag)
Day 180 → High Risk (!!! flag, serious concern)
Day 365 → Critical (likely default)
```

### 3. Contractor Performance Matters

A contractor with 31.6% default rate will:
- Collect less than expected
- Need focused recovery efforts
- Impact overall portfolio health

### 4. Collections Are Non-Linear

Due to risk factors:
- On Track customers: ~95% collection rate
- Medium Risk: ~50% collection rate
- High Risk: ~10% collection rate
- Critical: ~2% collection rate

---

## Using These Calculations

### For Dashboard
- Daily expected drives KPI cards
- Contractor expected shows performance
- Arrears highlight urgent cases

### For Forecasting
- 30-day forecast uses daily expected × 30 × confidence
- Scenarios adjust these rates up/down

### For Recovery Focus
- Customers with highest arrears get priority
- Risk category determines intervention approach

### For Reporting
- Expected vs Actual shows efficiency
- Gap % shows severity
- Health score shows portfolio trend

---

**Reference Date**: 2026-05-11  
**System Version**: 1.0
