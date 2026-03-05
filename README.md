# Enterprise Intelligence Explorer

A full-stack dashboard for exploring **21,645 Kerala MSME enterprises** — with intelligent search, multi-dimensional filters, analytics charts, and enterprise detail views.

---

## Quick Start (2 steps)

### Step 1 — Start the Backend

**Option A:** Double-click `start_backend.bat`

**Option B:** Open a terminal:
```powershell
cd enterprise-explorer\backend
py -3 -m uvicorn main:app --reload --port 8000
```

The API will be available at **http://127.0.0.1:8000**
→ Swagger docs at **http://127.0.0.1:8000/docs**

---

### Step 2 — Start the Frontend

Open a **second terminal** (keep backend running):

**Option A:** Double-click `start_frontend.bat`

**Option B:**
```powershell
cd enterprise-explorer\frontend
py -3 -m http.server 3000
```

Then open **http://localhost:3000** in your browser.

---

## Project Structure

```
enterprise-explorer/
├── backend/
│   ├── main.py            # FastAPI app (all API endpoints)
│   ├── database.py        # SQLite connect + init
│   ├── models.py          # Pydantic response models
│   ├── process_data.py    # ETL: Excel → SQLite (run once)
│   ├── enterprises.db     # SQLite database (auto-generated)
│   └── requirements.txt
└── frontend/
    ├── index.html         # App shell (nav, dashboard, analytics, modal)
    ├── style.css          # Dark glassmorphism design system
    └── app.js             # All frontend logic (API, charts, filters)
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/enterprises` | Paginated list. Params: `page`, `limit`, `search`, `category`, `district`, `pincode`, `nic_code` |
| GET | `/api/enterprises/{id}` | Full enterprise details + activities |
| GET | `/api/enterprises/{id}/similar` | Top 5 similar enterprises |
| GET | `/api/stats` | Aggregate statistics |
| GET | `/api/filters` | All available filter options |
| GET | `/api/export` | Download CSV (same filters as list) |

---

## Features

- **🔍 Keyword search** across enterprise name, description, address
- **🎛️ Multi-filter sidebar** — Category, District, Pincode, NIC code
- **📄 Paginated table** — 25 per page, navigable
- **📊 Analytics dashboard** — Pie chart (categories), Bar charts (pincodes, sectors)
- **🏢 Enterprise detail modal** — Full info, all activities, similar enterprises
- **⬇️ CSV export** — Download any filtered result set
- **📱 Responsive** — Works on tablet & mobile

---

## Re-running the ETL

If you update the Excel file, run:
```powershell
cd enterprise-explorer\backend
py -3 process_data.py
```

---

## Category Mapping Logic

Activities are mapped to categories by keyword matching on their NIC description:

| Category | Keywords matched |
|---|---|
| Technology | software, it, digital, computer, telecom |
| Manufacturing | manufactur, textile, weaving, mill, printing |
| Retail | retail sale, shop, wholesale, trade, dealer |
| Food | meat, food, seafood, dairy, bakery, flour, fish |
| Transport | vehicle, transport, bus, truck, courier |
| Construction | construct, building, civil, plumbing, electrician |
| Agriculture | agri, farm, crop, horticulture, seed |
| Services | consulting, cleaning, salon, laundry, repair |
| Healthcare | medical, health, pharmacy, clinic, hospital |
| Education | school, tutori, training, coaching, academy |
