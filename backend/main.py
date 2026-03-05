"""
Enterprise Intelligence Explorer - FastAPI Backend
Run: uvicorn main:app --reload --port 8000
"""
import io
import math
import csv
import os
import sqlite3
from typing import Optional

from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles

from database import get_connection, init_db
from models import (
    ActivityOut,
    EnterpriseDetail,
    EnterpriseListItem,
    PaginatedEnterprises,
    StatsResponse,
    FiltersResponse,
    ChatRequest,
    ChatResponse,
)
try:
    import chromadb
    from sentence_transformers import SentenceTransformer
    from langchain_groq import ChatGroq
    from langchain_openai import ChatOpenAI
    from langchain_core.prompts import PromptTemplate
    from dotenv import load_dotenv
    
    load_dotenv()
    CHROMA_PATH = os.path.join(os.path.dirname(__file__), "chroma_db")
    chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
    vector_collection = chroma_client.get_or_create_collection(name="enterprises")
    embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
except Exception as e:
    print(f"Warning: RAG components failed to initialize: {e}")
    vector_collection = None
    embedding_model = None

def get_llm():
    if os.getenv("GROQ_API_KEY"):
        return ChatGroq(temperature=0.2, model_name="llama-3.1-8b-instant")
    elif os.getenv("OPENAI_API_KEY"):
        return ChatOpenAI(temperature=0.2)
    return None

rag_prompt = PromptTemplate.from_template('''
You are a helpful MSME (Micro, Small, and Medium Enterprises) assistant for Kerala, India.
Use the following context about registered enterprises to answer the user's question. 
If the answer is not in the context, just say that you don't know or don't have enough data.
Keep your answers helpful, concise, and friendly.

Context:
{context}

Question: {question}

Answer:
''')

# ──────────────────────────────────────────────────────────────────────────────
app = FastAPI(title="Enterprise Intelligence Explorer API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = os.path.join(os.path.dirname(__file__), "enterprises.db")


@app.on_event("startup")
def startup():
    if not os.path.exists(DB_PATH):
        init_db()


# ──────────────────────────────────────────────────────────────────────────────
# Helper: build WHERE clause from filters
# ──────────────────────────────────────────────────────────────────────────────
def build_where(
    search: Optional[str],
    category: Optional[str],
    district: Optional[str],
    pincode: Optional[str],
    nic_code: Optional[str],
    place: Optional[str] = None,
) -> tuple[str, list]:
    clauses = []
    params: list = []

    if search:
        # Smart Search: Split into words and match each
        words = [w.strip() for w in search.lower().split() if len(w.strip()) > 2]
        if not words:
            words = [search.lower()]
        
        search_clauses = []
        for word in words:
            search_clauses.append("(e.enterprise_name LIKE ? OR e.description LIKE ? OR e.address LIKE ?)")
            like = f"%{word}%"
            params.extend([like, like, like])
        
        if search_clauses:
            clauses.append("(" + " AND ".join(search_clauses) + ")")

    if category:
        clauses.append("e.categories LIKE ?")
        params.append(f"%{category}%")

    if district:
        clauses.append("e.district = ?")
        params.append(district.upper())

    if pincode:
        clauses.append("e.pincode = ?")
        params.append(pincode)

    if nic_code:
        clauses.append("""e.id IN (
            SELECT DISTINCT enterprise_id FROM activities WHERE nic_code = ?
        )""")
        params.append(nic_code)

    if place:
        clauses.append("(e.address LIKE ? OR e.district LIKE ? OR e.pincode LIKE ?)")
        like = f"%{place}%"
        params.extend([like, f"%{place.upper()}%", f"%{place}%"])

    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    return where, params


# ──────────────────────────────────────────────────────────────────────────────
# GET /api/enterprises
# ──────────────────────────────────────────────────────────────────────────────
@app.get("/api/enterprises", response_model=PaginatedEnterprises)
def list_enterprises(
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=1, le=200),
    search: Optional[str] = None,
    category: Optional[str] = None,
    district: Optional[str] = None,
    pincode: Optional[str] = None,
    nic_code: Optional[str] = None,
    place: Optional[str] = None,
):
    where, params = build_where(search, category, district, pincode, nic_code, place)
    offset = (page - 1) * limit

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(f"SELECT COUNT(*) FROM enterprises e {where}", params)
    total = cur.fetchone()[0]

    cur.execute(f"""
        SELECT e.id, e.enterprise_name, e.state, e.district, e.pincode,
               e.description, e.sector, e.categories
        FROM enterprises e
        {where}
        ORDER BY e.enterprise_name
        LIMIT ? OFFSET ?
    """, params + [limit, offset])

    rows = cur.fetchall()
    conn.close()

    data = [
        EnterpriseListItem(
            id=r["id"],
            enterprise_name=r["enterprise_name"],
            state=r["state"],
            district=r["district"],
            pincode=r["pincode"],
            description=r["description"],
            sector=r["sector"],
            categories=r["categories"],
        )
        for r in rows
    ]

    return PaginatedEnterprises(
        total=total,
        page=page,
        limit=limit,
        pages=math.ceil(total / limit) if total else 1,
        data=data,
    )


# ──────────────────────────────────────────────────────────────────────────────
# GET /api/enterprises/{id}
# ──────────────────────────────────────────────────────────────────────────────
@app.get("/api/enterprises/{enterprise_id}", response_model=EnterpriseDetail)
def get_enterprise(enterprise_id: int):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM enterprises WHERE id = ?", (enterprise_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Enterprise not found")

    cur.execute(
        "SELECT id, nic_code, nic_description FROM activities WHERE enterprise_id = ?",
        (enterprise_id,),
    )
    acts = [
        ActivityOut(id=a["id"], nic_code=a["nic_code"], nic_description=a["nic_description"])
        for a in cur.fetchall()
    ]
    conn.close()

    return EnterpriseDetail(
        id=row["id"],
        enterprise_name=row["enterprise_name"],
        state=row["state"],
        district=row["district"],
        pincode=row["pincode"],
        registration_date=row["registration_date"],
        address=row["address"],
        description=row["description"],
        sector=row["sector"],
        categories=row["categories"],
        activities=acts,
    )


# ──────────────────────────────────────────────────────────────────────────────
# GET /api/enterprises/{id}/similar
# ──────────────────────────────────────────────────────────────────────────────
@app.get("/api/enterprises/{enterprise_id}/similar", response_model=list[EnterpriseListItem])
def get_similar(enterprise_id: int, limit: int = 5):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT description, categories FROM enterprises WHERE id = ?", (enterprise_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Enterprise not found")

    desc = row["description"] or ""
    cats = row["categories"] or ""

    # Extract keywords from description (words >4 chars)
    keywords = [w for w in desc.lower().split() if len(w) > 4]
    cat_list = [c.strip() for c in cats.split(",") if c.strip()]

    similar = []

    if keywords or cat_list:
        # Search by category match first
        cat_clause = " OR ".join(["e.categories LIKE ?" for c in cat_list])
        kw_clause  = " OR ".join(["e.description LIKE ?" for k in keywords[:5]])

        parts = []
        params: list = []
        if cat_clause:
            parts.append(f"({cat_clause})")
            params.extend([f"%{c}%" for c in cat_list])
        if kw_clause:
            parts.append(f"({kw_clause})")
            params.extend([f"%{k}%" for k in keywords[:5]])

        where = "WHERE e.id != ? AND (" + " OR ".join(parts) + ")"
        params = [enterprise_id] + params

        cur.execute(f"""
            SELECT e.id, e.enterprise_name, e.state, e.district, e.pincode,
                   e.description, e.sector, e.categories
            FROM enterprises e
            {where}
            LIMIT ?
        """, params + [limit])

        rows = cur.fetchall()
        similar = [
            EnterpriseListItem(
                id=r["id"],
                enterprise_name=r["enterprise_name"],
                state=r["state"],
                district=r["district"],
                pincode=r["pincode"],
                description=r["description"],
                sector=r["sector"],
                categories=r["categories"],
            )
            for r in rows
        ]

    conn.close()
    return similar


# ──────────────────────────────────────────────────────────────────────────────
# GET /api/stats
# ──────────────────────────────────────────────────────────────────────────────
@app.get("/api/stats", response_model=StatsResponse)
def get_stats():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM enterprises")
    total = cur.fetchone()[0]

    cur.execute("SELECT COUNT(DISTINCT district) FROM enterprises")
    total_districts = cur.fetchone()[0]

    cur.execute("SELECT COUNT(DISTINCT pincode) FROM enterprises")
    total_pincodes = cur.fetchone()[0]

    cur.execute("SELECT COUNT(DISTINCT nic_code) FROM activities")
    total_nic = cur.fetchone()[0]

    # By district
    cur.execute("""
        SELECT district, COUNT(*) as cnt
        FROM enterprises
        GROUP BY district
        ORDER BY cnt DESC
        LIMIT 20
    """)
    by_district = {r["district"]: r["cnt"] for r in cur.fetchall()}

    # By pincode (top 20)
    cur.execute("""
        SELECT pincode, COUNT(*) as cnt
        FROM enterprises
        GROUP BY pincode
        ORDER BY cnt DESC
        LIMIT 20
    """)
    by_pincode = {r["pincode"]: r["cnt"] for r in cur.fetchall()}

    # By sector
    cur.execute("""
        SELECT sector, COUNT(*) as cnt
        FROM enterprises
        GROUP BY sector
        ORDER BY cnt DESC
    """)
    by_sector = {r["sector"]: r["cnt"] for r in cur.fetchall()}

    # By category (categories is comma-separated, need to split)
    cur.execute("SELECT categories FROM enterprises")
    cat_counts: dict = {}
    for row in cur.fetchall():
        cats = (row["categories"] or "Other").split(",")
        for c in cats:
            c = c.strip()
            if c:
                cat_counts[c] = cat_counts.get(c, 0) + 1

    conn.close()

    return StatsResponse(
        total_enterprises=total,
        total_districts=total_districts,
        total_pincodes=total_pincodes,
        total_nic_codes=total_nic,
        by_category=dict(sorted(cat_counts.items(), key=lambda x: -x[1])),
        by_district=by_district,
        by_pincode=by_pincode,
        by_sector=by_sector,
    )


# ──────────────────────────────────────────────────────────────────────────────
# GET /api/filters
# ──────────────────────────────────────────────────────────────────────────────
@app.get("/api/filters", response_model=FiltersResponse)
def get_filters():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT DISTINCT district FROM enterprises WHERE district != '' ORDER BY district")
    districts = [r["district"] for r in cur.fetchall()]

    cur.execute("SELECT DISTINCT pincode FROM enterprises WHERE pincode != '' ORDER BY pincode")
    pincodes = [r["pincode"] for r in cur.fetchall()]

    cur.execute("SELECT DISTINCT nic_code FROM activities WHERE nic_code != '' ORDER BY nic_code")
    nic_codes = [r["nic_code"] for r in cur.fetchall()]

    # Extract unique categories
    cur.execute("SELECT DISTINCT categories FROM enterprises WHERE categories != ''")
    cat_set: set = set()
    for row in cur.fetchall():
        for c in row["categories"].split(","):
            c = c.strip()
            if c:
                cat_set.add(c)

    conn.close()

    return FiltersResponse(
        districts=districts,
        pincodes=pincodes,
        categories=sorted(cat_set),
        nic_codes=nic_codes,
    )


# ──────────────────────────────────────────────────────────────────────────────
# GET /api/export  (CSV download)
# ──────────────────────────────────────────────────────────────────────────────
@app.get("/api/export")
def export_csv(
    search: Optional[str] = None,
    category: Optional[str] = None,
    district: Optional[str] = None,
    pincode: Optional[str] = None,
    nic_code: Optional[str] = None,
    place: Optional[str] = None,
):
    where, params = build_where(search, category, district, pincode, nic_code, place)
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(f"""
        SELECT e.id, e.enterprise_name, e.state, e.district, e.pincode,
               e.registration_date, e.description, e.sector, e.categories
        FROM enterprises e
        {where}
        ORDER BY e.enterprise_name
        LIMIT 5000
    """, params)

    rows = cur.fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Name", "State", "District", "Pincode",
                     "Registration Date", "Description", "Sector", "Categories"])
    for r in rows:
        writer.writerow([r["id"], r["enterprise_name"], r["state"], r["district"],
                         r["pincode"], r["registration_date"], r["description"],
                         r["sector"], r["categories"]])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=enterprises.csv"},
    )


# ──────────────────────────────────────────────────────────────────────────────
# POST /api/chat
# ──────────────────────────────────────────────────────────────────────────────
@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    msg = req.message.lower().strip()
    
    llm = get_llm()
    if not llm:
        return ChatResponse(
            response="I am currently in Rule-Based mode because no LLM API Key (GROQ_API_KEY or OPENAI_API_KEY) was found in the environment. Please add an API key to enable full RAG intelligence! Try asking me 'how many enterprises' or 'help'.",
            intent="error_no_llm",
            data_count=None
        )
        
    if not vector_collection or not embedding_model:
        return ChatResponse(
            response="My knowledge base is completely offline or hasn't been built yet. Please run `index_data.py` to index the MSME data into ChromaDB.",
            intent="error_no_db",
            data_count=None
        )

    # Convert query to embedding
    query_emb = embedding_model.encode(req.message).tolist()
    
    # Retrieve top 5 relevant documents
    results = vector_collection.query(
        query_embeddings=[query_emb],
        n_results=5
    )
    
    docs = results.get("documents", [[]])[0]
    context = "\n".join(docs) if docs else "No matching enterprises found."
    
    # Construct prompt and get response
    prompt_val = rag_prompt.format(context=context, question=req.message)
    try:
        res = llm.invoke(prompt_val)
        answer = res.content
        intent = "rag_response"
    except Exception as e:
        answer = f"I encountered an AI error: {e}"
        intent = "error_llm_call"

    return ChatResponse(response=answer, intent=intent, data_count=None)


# No longer serving static files here
# ──────────────────────────────────────────────────────────────────────────────
# In Vercel, static files are served via vercel.json routes
# Do not mount static files inside FastAPI here.
