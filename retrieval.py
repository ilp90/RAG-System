"""
Milestone 4 — embedding + vector store + retrieval for "The Unofficial Guide".

Pipeline stages 3 & 4 (per planning.md):
  chunks.json --embed (all-MiniLM-L6-v2)--> ChromaDB --query (top-k cosine)--> ranked chunks

Run:
  .venv/bin/python retrieval.py          # (re)build the index, then test the 5 eval queries
  .venv/bin/python retrieval.py test      # test only (use the already-built index)
"""

import json
import sys
import textwrap

import chromadb
from sentence_transformers import SentenceTransformer

CHUNKS_PATH = "chunks.json"
DB_PATH = "chroma_db"
COLLECTION = "unofficial_guide"
MODEL_NAME = "all-MiniLM-L6-v2"
TOP_K = 4  # planning.md Retrieval Approach

# The 5 evaluation queries from planning.md (used to validate retrieval).
EVAL_QUERIES = [
    "What salad-bar formula does Dr. Rachel Paul recommend for a healthy cafeteria salad?",
    "What is the difference between Flex Meals and Dining Dollars on an ISU meal plan?",
    "How does an ISU student with a food allergy get accommodated, and what does the Special Diet Kitchen cover?",
    "Which Ames grocery store is cheapest for students, and what is a specialty option?",
    "What dining spots or foods do ISU students name as their campus favorites?",
]

_model = None


def get_model():
    """Load all-MiniLM-L6-v2 once (local, no API key)."""
    global _model
    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)
    return _model


def get_collection():
    """Return the persistent ChromaDB collection (cosine distance)."""
    client = chromadb.PersistentClient(path=DB_PATH)
    return client.get_or_create_collection(
        COLLECTION, metadata={"hnsw:space": "cosine"}
    )


def build_index():
    """Embed every chunk in chunks.json and (re)load it into ChromaDB with metadata."""
    with open(CHUNKS_PATH, encoding="utf-8") as f:
        chunks = json.load(f)

    print(f"Embedding {len(chunks)} chunks with {MODEL_NAME} ...")
    embeddings = get_model().encode(
        [c["text"] for c in chunks],
        normalize_embeddings=True,
        show_progress_bar=True,
    )

    client = chromadb.PersistentClient(path=DB_PATH)
    # fresh rebuild so reruns don't accumulate stale/duplicate vectors
    try:
        client.delete_collection(COLLECTION)
    except Exception:
        pass
    col = client.create_collection(COLLECTION, metadata={"hnsw:space": "cosine"})

    col.add(
        ids=[f"chunk-{i}" for i in range(len(chunks))],
        embeddings=embeddings.tolist(),
        documents=[c["text"] for c in chunks],
        metadatas=[
            {
                "source_name": c["source_name"],
                "source": c["source"],
                "chunk_index": c["chunk_index"],
            }
            for c in chunks
        ],
    )
    print(f"Indexed {col.count()} chunks into '{COLLECTION}' ({DB_PATH}/)\n")
    return col


def retrieve(query, k=TOP_K):
    """Return the top-k most relevant chunks for a query, with source + cosine distance."""
    col = get_collection()
    q_emb = get_model().encode([query], normalize_embeddings=True).tolist()
    res = col.query(query_embeddings=q_emb, n_results=k)
    return [
        {
            "text": doc,
            "source_name": meta["source_name"],
            "chunk_index": meta["chunk_index"],
            "distance": dist,
        }
        for doc, meta, dist in zip(
            res["documents"][0], res["metadatas"][0], res["distances"][0]
        )
    ]


def test_retrieval():
    """Run the eval queries and print ranked chunks + distance scores for inspection."""
    if get_collection().count() == 0:
        print("Index is empty — run `python retrieval.py` to build it first.")
        sys.exit(1)

    for qi, query in enumerate(EVAL_QUERIES, 1):
        print("=" * 90)
        print(f"Q{qi}: {query}")
        print("=" * 90)
        for rank, hit in enumerate(retrieve(query), 1):
            flag = "" if hit["distance"] < 0.5 else "  ⚠️ weak (>0.5)"
            print(f"\n[{rank}] distance={hit['distance']:.3f}{flag}  "
                  f"| {hit['source_name']}  (chunk {hit['chunk_index']})")
            print(textwrap.fill(hit["text"][:340].strip(), width=88,
                                initial_indent="    ", subsequent_indent="    "))
        print()


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "build"
    if mode == "test":
        test_retrieval()
    else:
        build_index()
        test_retrieval()


if __name__ == "__main__":
    main()
