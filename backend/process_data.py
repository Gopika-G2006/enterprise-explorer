"""
ETL Script: Read MSME Excel → Parse JSON activities → Map categories → Insert into SQLite
Run once: py -3 process_data.py
"""
import pandas as pd
import sqlite3
import json
import os
import sys

CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "msme.csv")
DB_PATH = os.path.join(os.path.dirname(__file__), "enterprises.db")

# ─── Category Mapping ─────────────────────────────────────────────────────────
CATEGORY_KEYWORDS = {
    "Technology":    ["software", "it ", "digital", "computer", "telecom", "internet", "programming", "electronic"],
    "Manufacturing": ["manufactur", "production", "textile", "weaving", "mill", "fabricat", "assembl", "printing", "processing"],
    "Retail":        ["retail sale", "retail ", "shop", "wholesale", "trade", "dealer", "selling"],
    "Food":          ["meat", "food", "seafood", "dairy", "bakery", "beverage", "restaurant", "catering", "flour", "oil", "cereal", "fish", "poultry"],
    "Transport":     ["vehicle", "transport", "bus", "truck", "courier", "driving", "freight", "cargo", "auto"],
    "Construction":  ["construct", "building", "civil", "plumbing", "electrician", "carpenter", "paint"],
    "Agriculture":   ["agri", "farm", "crop", "horticulture", "plant", "flower", "seed", "fertilizer"],
    "Services":      ["consulting", "cleaning", "agency", "repair", "salon", "laundry", "beauty", "tailoring", "service", "maintenance"],
    "Healthcare":    ["medical", "health", "pharmacy", "clinic", "hospital", "dental", "optical", "nursing"],
    "Education":     ["school", "tutori", "training", "education", "coaching", "academy"],
}


def assign_categories(description: str) -> list[str]:
    if not description:
        return ["Other"]
    desc_lower = description.lower()
    cats = [cat for cat, kws in CATEGORY_KEYWORDS.items() if any(kw in desc_lower for kw in kws)]
    return cats if cats else ["Other"]


def run():
    global CSV_PATH
    if not os.path.exists(CSV_PATH):
        # Try alternate path
        alt = os.path.join(os.path.dirname(__file__), "..", "msme.csv")
        if os.path.exists(alt):
            CSV_PATH = alt
        else:
            print(f"ERROR: CSV file not found at {CSV_PATH}")
            sys.exit(1)

    print(f"Reading CSV from {os.path.abspath(CSV_PATH)} ...")
    df = pd.read_csv(CSV_PATH, dtype=str)
    df = df.fillna("")
    print(f"  Loaded {len(df)} rows")

    # Normalize column names
    df.columns = [c.strip() for c in df.columns]

    # Init DB
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.executescript("""
        CREATE TABLE enterprises (
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
        CREATE TABLE activities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            enterprise_id INTEGER NOT NULL REFERENCES enterprises(id),
            nic_code TEXT,
            nic_description TEXT
        );
        CREATE INDEX idx_ent_name     ON enterprises(enterprise_name COLLATE NOCASE);
        CREATE INDEX idx_ent_district ON enterprises(district);
        CREATE INDEX idx_ent_pincode  ON enterprises(pincode);
        CREATE INDEX idx_act_nic      ON activities(nic_code);
        CREATE INDEX idx_act_eid      ON activities(enterprise_id);
    """)

    enterprise_rows = []
    activity_rows = []

    for idx, row in df.iterrows():
        name        = str(row.get("EnterpriseName", "")).strip()
        state       = str(row.get("State", "")).strip()
        district    = str(row.get("District", "")).strip()
        pincode     = str(row.get("Pincode", "")).strip()
        reg_date    = str(row.get("RegistrationDate", "")).strip()
        address     = str(row.get("CommunicationAddress", "")).strip()
        description = str(row.get("Description", "")).strip()
        sector      = str(row.get("Sector", "")).strip()
        activities_raw = str(row.get("Activities", "[]")).strip()

        # Parse activities JSON
        try:
            activities = json.loads(activities_raw) if activities_raw else []
        except Exception:
            activities = []

        # Build full description from all activities if main description is empty
        all_descriptions = [a.get("Description", "") for a in activities if a.get("Description")]
        if not description and all_descriptions:
            description = all_descriptions[0]

        # Category mapping (use all activity descriptions)
        combined_desc = description + " " + " ".join(all_descriptions)
        categories = assign_categories(combined_desc)

        enterprise_rows.append((
            name, state, district, pincode, reg_date, address,
            description, sector, ",".join(categories)
        ))

        # We need the enterprise_id — insert in batch then bulk-insert activities
        for act in activities:
            activity_rows.append((
                idx + 1,  # placeholder — we'll fix after bulk insert
                str(act.get("NIC5DigitId", "")).strip(),
                str(act.get("Description", "")).strip(),
            ))

    print("Inserting enterprises ...")
    cur.executemany("""
        INSERT INTO enterprises (enterprise_name, state, district, pincode, registration_date,
                                  address, description, sector, categories)
        VALUES (?,?,?,?,?,?,?,?,?)
    """, enterprise_rows)
    conn.commit()

    # Now fetch the ids (they're sequential starting from 1)
    cur.execute("SELECT id FROM enterprises ORDER BY id")
    ent_ids = [r[0] for r in cur.fetchall()]

    # Map activity rows: activities are ordered by the original DataFrame iteration
    # We need to rebuild mapping per enterprise
    print("Inserting activities ...")
    final_activities = []
    act_idx = 0
    for eidx, (df_idx, row) in enumerate(df.iterrows()):
        activities_raw = str(row.get("Activities", "[]")).strip()
        try:
            acts = json.loads(activities_raw) if activities_raw else []
        except Exception:
            acts = []
        eid = ent_ids[eidx]
        for act in acts:
            final_activities.append((
                eid,
                str(act.get("NIC5DigitId", "")).strip(),
                str(act.get("Description", "")).strip(),
            ))

    cur.executemany("""
        INSERT INTO activities (enterprise_id, nic_code, nic_description)
        VALUES (?,?,?)
    """, final_activities)
    conn.commit()
    conn.close()

    print(f"[DONE] {len(enterprise_rows)} enterprises and {len(final_activities)} activities inserted into {DB_PATH}")


if __name__ == "__main__":
    run()
