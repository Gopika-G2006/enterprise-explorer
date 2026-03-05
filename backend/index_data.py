import sqlite3
import os
import chromadb
from sentence_transformers import SentenceTransformer

DB_PATH = os.path.join(os.path.dirname(__file__), "enterprises.db")
CHROMA_PATH = os.path.join(os.path.dirname(__file__), "chroma_db")

def init_vector_db():
    print("Initializing SentenceTransformer model (all-MiniLM-L6-v2)...")
    model = SentenceTransformer("all-MiniLM-L6-v2")

    print(f"Connecting to ChromaDB at {CHROMA_PATH}...")
    chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
    
    # Reset or create collection
    try:
        chroma_client.delete_collection(name="enterprises")
    except Exception:
        pass

    collection = chroma_client.create_collection(name="enterprises")

    print(f"Connecting to SQLite DB at {DB_PATH}...")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("SELECT * FROM enterprises")
    rows = cur.fetchall()
    
    documents = []
    metadatas = []
    ids = []

    print(f"Loaded {len(rows)} records from SQLite.")
    
    # To save time and memory for this demonstration, we might only index a subset or all of them.
    # We will index the first 10,000 to keep it lightweight.
    LIMIT = min(len(rows), 10000)
    print(f"Processing top {LIMIT} records for vector database...")

    for i in range(LIMIT):
        row = rows[i]
        ent_id = str(row["id"])
        name = row["enterprise_name"]
        desc = row["description"]
        dist = row["district"]
        cats = row["categories"]
        
        # Combine into a rich document for embedding
        doc_text = f"Name: {name}. Description: {desc}. Location: {dist}. Categories: {cats}."
        
        documents.append(doc_text)
        metadatas.append({
            "id": row["id"],
            "name": name,
            "district": dist,
            "categories": cats
        })
        ids.append(ent_id)

    print("Generating embeddings and adding to ChromaDB. This may take a minute...")
    # Generate embeddings ourselves or rely on chroma default
    # Let's use chroma default for faster setup, but use sentence-transformers if we want consistency
    # For now, we'll let chroma use its built in all-minilm-l6-v2 under the hood for simplicity if we don't pass embeddings, 
    # but since we imported sentence_transformers, let's just generate them.
    
    BATCH_SIZE = 1000
    for i in range(0, LIMIT, BATCH_SIZE):
        batch_docs = documents[i:i + BATCH_SIZE]
        batch_meta = metadatas[i:i + BATCH_SIZE]
        batch_ids = ids[i:i + BATCH_SIZE]
        
        print(f"  -> Batch {i//BATCH_SIZE + 1} ({i} to {i+len(batch_docs)})...")
        # Generate embeddings
        batch_embeddings = model.encode(batch_docs, show_progress_bar=False).tolist()
        
        # Add to collection
        collection.add(
            embeddings=batch_embeddings,
            documents=batch_docs,
            metadatas=batch_meta,
            ids=batch_ids
        )
    
    print(f"Successfully embedded and stored {LIMIT} enterprise records in ChromaDB at {CHROMA_PATH}.")

if __name__ == "__main__":
    init_vector_db()
