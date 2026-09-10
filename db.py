import sqlite3
import os
from datetime import datetime, timezone

# Anchor the database path directly to the folder where db.py is located
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "bank.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('client','manager')),
    full_name TEXT NOT NULL,
    age INTEGER,
    gender TEXT,             -- 'female' / 'male'  (also used for fraud model as F/M)
    phone TEXT,
    email TEXT,
    state TEXT,               -- 2-letter US state, used by fraud model
    job TEXT,                 -- free text occupation, used by fraud model
    account_number TEXT UNIQUE,
    balance REAL DEFAULT 0,
    income REAL,
    employment_years INTEGER,
    home_ownership TEXT,
    credit_score INTEGER,
    credit_history_years INTEGER,
    has_prior_default TEXT DEFAULT 'No',
    geography TEXT DEFAULT 'France',        -- France/Germany/Spain, used by the segmentation model
    tenure_years INTEGER,                    -- years as a bank customer, used by the segmentation model
    num_of_products INTEGER,                 -- 1-4, used by the segmentation model
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS loans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    amount REAL NOT NULL,
    intent TEXT NOT NULL,
    interest_rate REAL NOT NULL,
    percent_income REAL NOT NULL,
    applicant_gender TEXT,
    applicant_education TEXT,
    applicant_home_ownership TEXT,
    applicant_prior_default TEXT,
    status TEXT DEFAULT 'pending',   -- pending / approved / rejected
    model_probability REAL,
    model_recommend INTEGER,          -- 1 = model says approve, 0 = model says reject
    model_reasons TEXT,
    decided_by INTEGER,
    created_at TEXT,
    decided_at TEXT,
    FOREIGN KEY(user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sender_id INTEGER NOT NULL,
    receiver_account TEXT NOT NULL,
    receiver_name TEXT,
    amount REAL NOT NULL,
    merchant TEXT,
    category TEXT,
    status TEXT DEFAULT 'cleared',  -- cleared / pending_review / blocked / manager_approved / manager_rejected
    fraud_probability REAL,
    fraud_reasons TEXT,
    decided_by INTEGER,
    created_at TEXT,
    decided_at TEXT,
    FOREIGN KEY(sender_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS currency_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pair TEXT NOT NULL,
    day_index INTEGER NOT NULL,
    close_price REAL NOT NULL
);
"""


def get_db():
    # 30-second timeout prevents Windows / OneDrive "database is locked" errors
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def init_db():
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = get_db()
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()


def now():
    return datetime.now(timezone.utc).replace(tzinfo=None).isoformat(timespec="seconds")