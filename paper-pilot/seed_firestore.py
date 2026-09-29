"""Seed script for PaperPilot Firestore backend."""
from google.cloud import firestore

PROJECT_ID = "qwiklabs-gcp-03-644239e208e8"

SAMPLE_RESOURCES = [
    {
        "id": "paper-rag-reasoning-2025",
        "title": "Iterative Retrieval Augmented Reasoning in LLMs",
        "topic": "Retrieval Augmented Generation",
        "authors": ["A. Vaswani", "K. Chen", "L. Gomez"],
        "year": 2025,
        "resource_type": "paper",
        "source": "local",
        "arguments": [
            "Single-step RAG fails on multi-hop questions because intermediate evidence is missing.",
            "Iterative query reformulation improves precision over dense retrievers."
        ],
        "conclusions": "Iterative retrieval increases factual accuracy on complex reasoning tasks by 23% over baseline RAG.",
        "findings": "Dense retrievers often retrieve semantically similar but logically irrelevant chunks without query refinement.",
        "contradictions": [],
        "strengthens": ["paper-graph-rag-2024"],
        "tags": ["rag", "reasoning", "retrieval"]
    },
    {
        "id": "paper-graph-rag-2024",
        "title": "Graph-based Knowledge Grounding for Complex QA",
        "topic": "Retrieval Augmented Generation",
        "authors": ["M. Zhang", "S. Patel"],
        "year": 2024,
        "resource_type": "paper",
        "source": "local",
        "arguments": [
            "Vector distance alone ignores entity relationships.",
            "Graph structures preserve multi-hop causal chains."
        ],
        "conclusions": "Graph-structured grounding outperforms pure vector search on relationship extraction.",
        "findings": "Graph indexing requires 2x indexing latency but reduces hallucinated links.",
        "contradictions": ["paper-vector-primacy-2025"],
        "strengthens": [],
        "tags": ["rag", "knowledge-graph", "grounding"]
    },
    {
        "id": "paper-vector-primacy-2025",
        "title": "Why Simple Vector Search is All You Need for Enterprise RAG",
        "topic": "Retrieval Augmented Generation",
        "authors": ["R. Miller", "D. Zhao"],
        "year": 2025,
        "resource_type": "paper",
        "source": "local",
        "arguments": [
            "Graph construction overhead does not justify marginal accuracy gains over hybrid dense-sparse search.",
            "Well-tuned embedding models can implicitly capture multi-hop relations."
        ],
        "conclusions": "Hybrid vector retrieval matches graph RAG performance at 1/5th latency and engineering complexity.",
        "findings": "Hybrid search beats graph-only retrievers across 8 out of 10 standard enterprise QA benchmarks.",
        "contradictions": ["paper-graph-rag-2024"],
        "strengthens": [],
        "tags": ["rag", "vector-search", "hybrid"]
    }
]

def seed_db():
    print(f"Connecting to Firestore for project: {PROJECT_ID}")
    db = firestore.Client(project=PROJECT_ID)
    collection = db.collection("research_resources")

    for item in SAMPLE_RESOURCES:
        doc_id = item["id"]
        doc_ref = collection.document(doc_id)
        doc_ref.set(item)
        print(f"Seeded document: {doc_id} -> '{item['title']}'")

    print("\nSeeding complete!")

if __name__ == "__main__":
    seed_db()
