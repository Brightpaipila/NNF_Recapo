CREATE TABLE IF NOT EXISTS customers (
    db_id INTEGER PRIMARY KEY,
    customer_id TEXT UNIQUE,
    customer_name TEXT,
    state TEXT,
    sales_product TEXT,
    sales_price TEXT,
    system_id TEXT,
    balance REAL,
    payoff_amount REAL,
    effective_payoff_amount REAL,
    left_to_pay REAL,
    percentage_paid REAL,
    penalties REAL,
    manual_penalties REAL,
    automatic_penalties REAL,
    days_system_off INTEGER,
    flags TEXT,
    last_token_time TEXT,
    charged_until TEXT,
    assigned_contractor TEXT,
    payment_number INTEGER,
    location_area1 TEXT,
    location_area2 TEXT,
    location_area3 TEXT,
    location_area4 TEXT,
    location_address TEXT,
    phone TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS payment_schedules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id TEXT UNIQUE,
    plan_type TEXT,
    total_amount REAL,
    installation_fee REAL,
    weekly_payment REAL,
    monthly_payment REAL,
    payment_frequency TEXT,
    start_date TEXT,
    end_date TEXT,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);

CREATE TABLE IF NOT EXISTS payment_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id TEXT,
    payment_date TEXT,
    payment_amount REAL,
    weeks_paid INTEGER,
    balance_after REAL,
    collected_by TEXT,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);

CREATE TABLE IF NOT EXISTS daily_collections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    collection_date TEXT UNIQUE,
    expected_collection REAL,
    actual_collection REAL,
    expected_customers INTEGER,
    actual_customers INTEGER,
    default_customers INTEGER,
    default_rate REAL
);

CREATE TABLE IF NOT EXISTS agent_performance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contractor TEXT,
    reporting_date TEXT,
    customers_assigned INTEGER,
    customers_active INTEGER,
    customers_paid_off INTEGER,
    expected_collection REAL,
    actual_collection REAL,
    collection_efficiency REAL,
    default_rate REAL,
    top_performer BOOLEAN DEFAULT 0
);

CREATE TABLE IF NOT EXISTS expected_collections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id TEXT,
    collection_date TEXT,
    expected_amount REAL,
    is_overdue BOOLEAN,
    weeks_overdue INTEGER,
    days_until_due INTEGER,
    status TEXT,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);