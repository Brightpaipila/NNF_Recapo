# app/dashboard.py
"""
RECAPO Intelligence Dashboard
Real-time collection recovery analytics and forecasting
"""

import sys
from pathlib import Path
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

root = Path(__file__).parent.parent
sys.path.insert(0, str(root))

from expected_engine import (
    generate_expected_metrics, 
    calculate_daily_expected_collection,
    get_collection_summary
)
from collection_engine import calculate_collection_metrics, get_all_contractors_collection
from risk_engine import apply_risk_logic, get_risk_distribution, get_portfolio_health_score
from recovery_engine import recovery_metrics, get_critical_cases
from agent_analytics import contractor_performance, get_top_performers
from due_engine import daily_due_customers, get_urgent_followups, get_payment_schedule_summary
from forecasting import forecast_recovery, scenario_analysis

# ================= PAGE CONFIG =================
st.set_page_config(
    page_title="RECAPO Intelligence",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("📊 RECAPO Recovery Intelligence System")
st.markdown("Real-time collection analytics & payment forecast engine")

# ================= LOAD DATA =================
def load_data():
    """Load latest CSV or Excel export from raw data folder"""
    try:
        files = list((root / "data/raw").glob("*.xlsx")) + list((root / "data/raw").glob("*.csv"))
        if not files:
            raise FileNotFoundError("No CSV or XLSX files found in data/raw")
        latest_file = max(files, key=lambda f: f.stat().st_mtime)
        if latest_file.suffix.lower() == ".csv":
            df = pd.read_csv(latest_file)
        else:
            df = pd.read_excel(latest_file)
        return df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()

df = load_data()

if len(df) == 0:
    st.error("No data available. Please ensure data/raw/*.xlsx exists.")
    st.stop()

# ================= DATA CLEANING & ENRICHMENT =================
# Standardize column names
df.columns = df.columns.str.strip()

# Clean numeric columns
numeric_cols = ["Balance", "Left to pay", "Days system off", "Payoff amount", "Percentage paid"]
for col in numeric_cols:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

# Standardize state values
if "State" in df.columns:
    df["State"] = df["State"].str.lower().str.strip()

# ================= ENGINE PIPELINE =================
# Generate expected metrics (core KPI)
df = generate_expected_metrics(df)

# Apply risk logic
df = apply_risk_logic(df)

# Calculate all metrics
daily_collection = calculate_daily_expected_collection(df)
recovery = recovery_metrics(df)
collection_metrics = calculate_collection_metrics(df)
collection_summary = get_collection_summary(df)
forecast = forecast_recovery(df, 30)

# ================= SIDEBAR - FILTERS & INFO =================
st.sidebar.header("🎯 Filters & Controls")

# Multi-select contractors
contractors_list = sorted(df["Assigned to contractor"].fillna("Unassigned").astype(str).unique().tolist())
selected_contractors = st.sidebar.multiselect(
    "Select Contractors",
    contractors_list,
    default=contractors_list
)

# Multi-select risk categories
risk_categories = sorted(df["Risk_Category"].fillna("Unknown").astype(str).unique().tolist())
selected_risks = st.sidebar.multiselect(
    "Select Risk Categories",
    risk_categories,
    default=risk_categories
)

# State filter
states = sorted(df["State"].fillna("Unknown").astype(str).unique().tolist())
selected_states = st.sidebar.multiselect(
    "Customer Status",
    states,
    default=states
)

# Due date and days filters
filter_by_due_date = st.sidebar.checkbox("Filter by Due Date", value=False)
due_date = st.sidebar.date_input(
    "Select Due Date",
    value=pd.Timestamp.now("UTC").date()
)

min_days = int(df["Days_Until_Due"].min()) if "Days_Until_Due" in df.columns else 0
max_days = int(df["Days_Until_Due"].max()) if "Days_Until_Due" in df.columns else 0
selected_days = st.sidebar.slider(
    "Days Until Due Range",
    min_value=min_days,
    max_value=max_days,
    value=(min_days, max_days)
)

# Apply filters
contractor_mask = df["Assigned to contractor"].fillna("Unassigned").isin(selected_contractors)
risk_mask = df["Risk_Category"].fillna("Unknown").isin(selected_risks)
state_mask = df["State"].fillna("Unknown").isin(selected_states)

days_mask = pd.Series(True, index=df.index)
if selected_days != (min_days, max_days):
    days_mask = df["Days_Until_Due"].between(selected_days[0], selected_days[1])

filtered_df = df[contractor_mask & risk_mask & state_mask & days_mask]

if filter_by_due_date:
    filtered_df = filtered_df[filtered_df["Charged until"].dt.date == due_date]

# Display filter info
st.sidebar.markdown("---")
st.sidebar.info(f"""
**Data Summary**
- Total records: {len(df)}
- Filtered: {len(filtered_df)}
- Active customers: {len(df[df['State'].isin(['good', 'active'])])}
- Last updated: {df['Last token time'].max() if 'Last token time' in df.columns else 'Unknown'}
""")

health_score = get_portfolio_health_score(filtered_df)

# ================= KEY PERFORMANCE INDICATORS =================
st.markdown("## 📈 Key Performance Indicators")

col1, col2, col3, col4, col5, col6 = st.columns(6)

with col1:
    st.metric(
        "👥 Total Customers",
        f"{len(filtered_df):,}",
        delta=f"{len(df):,} total"
    )

with col2:
    st.metric(
        "💰 Expected Monthly",
        f"MK {collection_summary['monthly_expected']:,.0f}",
        delta=f"{collection_metrics['efficiency_percent']:.1f}% efficiency"
    )

with col3:
    st.metric(
        "📊 Outstanding",
        f"MK {recovery['outstanding']:,.0f}",
        delta=f"{len(df[df['Risk_Category'].isin(['Critical', 'High Risk'])])} at risk"
    )

with col4:
    st.metric(
        "⏰ Due Today",
        f"{daily_collection['expected_customers']}",
        delta=f"MK {daily_collection['expected_collection']:,.0f}"
    )

with col5:
    st.metric(
        "🏥 Portfolio Health",
        f"{health_score:.0f}/100",
        delta=f"{collection_summary['default_rate']:.1f}% default"
    )

with col6:
    st.metric(
        "⚠️ Default Rate",
        f"{collection_summary['default_rate']:.1f}%",
        delta=f"{daily_collection['default_customers']} default customers"
    )

# ================= MAIN DASHBOARD SECTIONS =================
st.markdown("---")

# Row 1: Risk Distribution, Collection, and Trend
col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("Risk Distribution")
    risk_dist = filtered_df["Risk_Category"].value_counts()
    fig = px.pie(
        values=risk_dist.values,
        names=risk_dist.index,
        hole=0.45,
        color_discrete_map={
            "On Track": "#2ecc71",
            "Watchlist": "#f39c12",
            "Medium Risk": "#e67e22",
            "High Risk": "#e74c3c",
            "Critical": "#c0392b"
        }
    )
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("Collection Status")
    status_data = {
        "Expected": [collection_summary['monthly_expected']],
        "Arrears": [collection_summary['total_arrears']]
    }
    fig = go.Figure(data=[
        go.Bar(name="Expected", x=["Monthly"], y=[collection_summary['monthly_expected']]),
        go.Bar(name="Arrears", x=["Monthly"], y=[collection_summary['total_arrears']])
    ])
    st.plotly_chart(fig, use_container_width=True)

with col3:
    st.subheader("Due Date Trend")
    if "Charged until" in filtered_df.columns:
        due_counts = (
            filtered_df.groupby(filtered_df["Charged until"].dt.date)
            .size()
            .reset_index(name="Customer Count")
            .sort_values(by="Charged until")
        )
        if len(due_counts) > 0:
            fig = px.line(
                due_counts,
                x="Charged until",
                y="Customer Count",
                markers=True,
                labels={"Charged until": "Due Date", "Customer Count": "Customers"}
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No due-date trend available for the current selection.")
    else:
        st.info("Charged until date is required for due-date trend.")

# Row 2: Customers per Due Date
st.markdown("---")
st.subheader("📅 Customers by Due Date")

if "Charged until" in filtered_df.columns:
    due_counts = (
        filtered_df.groupby(filtered_df["Charged until"].dt.date)
        .size()
        .reset_index(name="Customer Count")
        .sort_values(by="Charged until")
    )
    if len(due_counts) > 0:
        fig = px.bar(
            due_counts,
            x="Charged until",
            y="Customer Count",
            labels={"Charged until": "Due Date", "Customer Count": "Customers"}
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No customers available for the selected due date range.")
else:
    st.info("Charged until date is required for due-date grouping.")

# Row 3: Contractor Performance
st.markdown("---")
st.subheader("🏢 Contractor Performance")

contractors_perf = get_all_contractors_collection(filtered_df)
if len(contractors_perf) > 0:
    st.dataframe(
        contractors_perf.style.format({
            "expected_total": "MK {:,.0f}",
            "collected_total": "MK {:,.0f}",
            "efficiency_percent": "{:.1f}%"
        }),
        use_container_width=True
    )
else:
    st.info("No contractor data available")

# Row 3: Urgent Follow-ups
st.markdown("---")
st.subheader("🔴 Urgent Follow-ups (Top 20)")

urgent = get_urgent_followups(filtered_df, top_n=20)
if len(urgent) > 0:
    st.dataframe(
        urgent.style.format({
            "Weekly_Payment": "MK {:,.0f}",
            "Expected_Arrears": "MK {:,.0f}"
        }),
        use_container_width=True
    )
else:
    st.success("✅ No urgent follow-ups needed!")

# Row 4: Forecast
st.markdown("---")
st.subheader("📊 30-Day Forecast & Scenarios")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Daily Projection", f"MK {forecast['daily_avg']:,.0f}")
with col2:
    st.metric("30-Day Forecast", f"MK {forecast['forecast_30_days']:,.0f}")
with col3:
    st.metric("Confidence", f"{forecast['confidence_percent']:.0f}%")
with col4:
    st.metric("Monthly Projection", f"MK {forecast['monthly_projection']:,.0f}")

# Scenario analysis
st.subheader("Scenario Analysis")
scenarios = {}
for scenario in ["conservative", "realistic", "optimistic"]:
    scenarios[scenario] = scenario_analysis(filtered_df, scenario)

scenario_data = []
for scenario, data in scenarios.items():
    scenario_data.append({
        "Scenario": scenario.title(),
        "Weekly": data.get("weekly_collection", 0),
        "Monthly": data.get("monthly_projection", 0)
    })

scenario_df = pd.DataFrame(scenario_data)
st.dataframe(
    scenario_df.style.format({
        "Weekly": "MK {:,.0f}",
        "Monthly": "MK {:,.0f}"
    }),
    use_container_width=True
)

# Row 5: Critical Cases
st.markdown("---")
st.subheader("⚠️ Critical Cases (180+ days)")

critical = get_critical_cases(filtered_df, 180)
if len(critical) > 0:
    st.warning(f"⚠️ {len(critical)} customers in critical state requiring immediate action")
    st.dataframe(
        critical.style.format({
            "Expected_Arrears": "MK {:,.0f}",
            "Left to pay": "MK {:,.0f}"
        }),
        use_container_width=True
    )
else:
    st.success("✅ No critical cases!")

# ================= EXPORT & DOWNLOAD =================
st.markdown("---")
st.subheader("📥 Export Options")

col1, col2, col3 = st.columns(3)

with col1:
    csv = filtered_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "📊 Download Filtered Data (CSV)",
        csv,
        "recapo_filtered.csv",
        "text/csv"
    )

with col2:
    urgent_csv = get_urgent_followups(filtered_df, 50).to_csv(index=False).encode("utf-8")
    st.download_button(
        "🔴 Download Urgent List (CSV)",
        urgent_csv,
        "recapo_urgent.csv",
        "text/csv"
    )

with col3:
    critical_csv = get_critical_cases(filtered_df, 180).to_csv(index=False).encode("utf-8")
    st.download_button(
        "⚠️ Download Critical Cases (CSV)",
        critical_csv,
        "recapo_critical.csv",
        "text/csv"
    )

# ================= FOOTER =================
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: gray; font-size: 12px;'>
RECAPO Intelligence System | Recovery & Collection Forecast Engine
</div>
""", unsafe_allow_html=True)
