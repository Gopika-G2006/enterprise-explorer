import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "enterprises.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cur = conn.cursor()
    cur.executescript("""
        CREATE TABLE IF NOT EXISTS enterprises (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            enterprise_name TEXT NOT NULL,
            state TEXT,
            district TEXT,
            pincode TEXT,
            registration_date TEXT,
            address TEXT,
            description TEXT,
            sector TEXT,
            categories TEXT
        );

        CREATE TABLE IF NOT EXISTS activities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            enterprise_id INTEGER NOT NULL REFERENCES enterprises(id),
            nic_code TEXT,
            nic_description TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_ent_name ON enterprises(enterprise_name);
        CREATE INDEX IF NOT EXISTS idx_ent_district ON enterprises(district);
        CREATE INDEX IF NOT EXISTS idx_ent_pincode ON enterprises(pincode);
        CREATE INDEX IF NOT EXISTS idx_ent_categories ON enterprises(categories);
        CREATE INDEX IF NOT EXISTS idx_act_nic ON activities(nic_code);
        CREATE INDEX IF NOT EXISTS idx_act_enterprise ON activities(enterprise_id);
    """)
    conn.commit()
    conn.close()
