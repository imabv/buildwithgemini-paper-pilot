"""Firestore backend tools for PaperPilot research resources."""
from typing import List, Optional, Dict, Any
from google.cloud import firestore

PROJECT_ID = "qwiklabs-gcp-03-644239e208e8"
COLLECTION_NAME = "research_resources"

_db = None


def get_firestore_client() -> firestore.Client:
    """Return a singleton Firestore client with the hardcoded project ID."""
    global _db
    if _db is None:
        _db = firestore.Client(project=PROJECT_ID)
    return _db


def list_resources(topic: Optional[str] = None) -> List[Dict[str, Any]]:
    """List research resources, optionally filtered by topic.

    Args:
        topic: Optional topic/project name to filter resources by (e.g. 'Retrieval Augmented Generation').

    Returns:
        A list of research resource documents with their summaries, arguments, and conclusions.
    """
    db = get_firestore_client()
    col_ref = db.collection(COLLECTION_NAME)

    if topic:
        query = col_ref.where("topic", "==", topic)
        docs = query.stream()
    else:
        docs = col_ref.stream()

    results = []
    for doc in docs:
        data = doc.to_dict()
        data["id"] = doc.id
        results.append(data)
    return results


def get_resource_details(resource_id: str) -> Dict[str, Any]:
    """Retrieve detailed information and extracted findings for a specific research resource.

    Args:
        resource_id: The unique identifier of the resource/paper (e.g., 'paper-rag-reasoning-2025').

    Returns:
        The resource document details, or an error message if not found.
    """
    db = get_firestore_client()
    doc_ref = db.collection(COLLECTION_NAME).document(resource_id)
    doc = doc_ref.get()

    if not doc.exists:
        return {"error": f"Resource with ID '{resource_id}' not found."}

    data = doc.to_dict()
    data["id"] = doc.id
    return data


def save_resource(
    resource_id: str,
    title: str,
    topic: str,
    conclusions: str,
    arguments: List[str],
    assumptions: Optional[List[str]] = None,
    summary: Optional[str] = "",
    authors: Optional[List[str]] = None,
    year: Optional[int] = None,
    findings: Optional[str] = "",
    contradictions: Optional[List[str]] = None,
    strengthens: Optional[List[str]] = None,
    tags: Optional[List[str]] = None,
    source: str = "local"
) -> Dict[str, Any]:
    """Save or update a research paper or resource in the library.

    Args:
        resource_id: Unique slug or ID for the document (e.g. 'paper-hybrid-search-2026').
        title: Title of the paper or document.
        topic: Project or research topic it belongs to.
        conclusions: Key conclusions extracted from the paper.
        arguments: Core arguments and supporting reasoning in the resource.
        assumptions: Underlying theoretical or empirical assumptions.
        summary: Concise summary of the paper.
        authors: List of author names.
        year: Year of publication.
        findings: Specific empirical findings or methodologies.
        contradictions: List of paper IDs or concepts this paper directly contradicts or disputes.
        strengthens: List of paper IDs or concepts this paper supports or reinforces.
        tags: Relevant subject or domain topic tags (e.g. 'AI', 'Quantum', 'Finance').
        source: Source type, e.g. 'local' or 'web'.

    Returns:
        Status confirming the resource has been saved.
    """
    db = get_firestore_client()
    doc_ref = db.collection(COLLECTION_NAME).document(resource_id)

    data = {
        "id": resource_id,
        "title": title,
        "topic": topic,
        "conclusions": conclusions,
        "arguments": arguments,
        "assumptions": assumptions or [],
        "summary": summary or "",
        "authors": authors or [],
        "year": year or 2026,
        "findings": findings or "",
        "contradictions": contradictions or [],
        "strengthens": strengthens or [],
        "tags": tags or [],
        "source": source
    }

    doc_ref.set(data, merge=True)
    return {"status": "success", "message": f"Resource '{title}' ({resource_id}) successfully saved.", "resource": data}
