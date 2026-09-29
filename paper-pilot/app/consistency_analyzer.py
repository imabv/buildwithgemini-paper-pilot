"""Consistency and verification analyzer tool for cross-paper relation detection."""
import json
from typing import Any, Dict, List, Optional
from google import genai
from google.genai import types

from app.firestore_tools import get_firestore_client, list_resources, COLLECTION_NAME

PROJECT_ID = "qwiklabs-gcp-03-644239e208e8"
LOCATION = "us-east1"
MODEL_ID = "gemini-2.5-flash"

_genai_client = None


def get_genai_client() -> genai.Client:
    """Singleton GenAI client using Vertex AI."""
    global _genai_client
    if _genai_client is None:
        _genai_client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)
    return _genai_client


def analyze_cross_paper_consistency(
    target_paper_id: str,
    topic: Optional[str] = None,
    auto_update_links: bool = True
) -> Dict[str, Any]:
    """Analyze consistency, contradictions, and corroborations between a target paper and other papers in the library.

    Args:
        target_paper_id: The ID of the paper to evaluate against existing literature.
        topic: Optional topic filter to narrow down the comparison papers (defaults to target paper's topic).
        auto_update_links: Whether to automatically update the 'contradictions' and 'strengthens' fields in Firestore.

    Returns:
        A dictionary containing:
          - target_paper: Title and ID of the analyzed paper
          - contradictions: List of discovered contradictions with rationale and paper IDs
          - corroborations: List of discovered corroborations (papers that strengthen each other) with rationale
          - comparison_summary: Brief overall synthesis of scientific consensus and divergence
    """
    db = get_firestore_client()
    target_doc = db.collection(COLLECTION_NAME).document(target_paper_id).get()

    if not target_doc.exists:
        return {"error": f"Target paper with ID '{target_paper_id}' not found in the library."}

    target_data = target_doc.to_dict()
    target_topic = topic or target_data.get("topic")

    all_papers = list_resources(topic=target_topic) if target_topic else list_resources()
    comparison_papers = [p for p in all_papers if p.get("id") != target_paper_id]

    if not comparison_papers:
        return {
            "target_paper": {"id": target_paper_id, "title": target_data.get("title")},
            "contradictions": [],
            "corroborations": [],
            "comparison_summary": "No other papers found in the specified topic to compare against."
        }

    # Format literature for LLM prompt
    target_repr = {
        "id": target_paper_id,
        "title": target_data.get("title"),
        "arguments": target_data.get("arguments", []),
        "conclusions": target_data.get("conclusions", ""),
        "findings": target_data.get("findings", ""),
        "assumptions": target_data.get("assumptions", [])
    }

    reference_reprs = [
        {
            "id": p.get("id"),
            "title": p.get("title"),
            "arguments": p.get("arguments", []),
            "conclusions": p.get("conclusions", ""),
            "findings": p.get("findings", ""),
            "assumptions": p.get("assumptions", [])
        }
        for p in comparison_papers
    ]

    prompt = f"""You are an expert scientific auditor. Your task is to analyze scientific consistency between a TARGET paper and a set of REFERENCE papers.

TARGET PAPER:
{json.dumps(target_repr, indent=2)}

REFERENCE PAPERS:
{json.dumps(reference_reprs, indent=2)}

Analyze relationships between the target paper and each reference paper:
1. Identify CONTRADICTIONS: Where the target paper and a reference paper assert conflicting findings, opposing conclusions, or mutually incompatible assumptions.
2. Identify CORROBORATIONS (STRENGTHENING): Where the target paper and a reference paper reinforce, support, empirically validate, or strengthen each other's conclusions or arguments.
3. Provide a high-level consensus/divergence summary.

Return a JSON object conforming strictly to this schema:
{{
  "contradictions": [
    {{
      "conflicting_paper_id": "string",
      "conflicting_paper_title": "string",
      "nature_of_conflict": "string",
      "target_claim": "string",
      "reference_claim": "string"
    }}
  ],
  "corroborations": [
    {{
      "strengthening_paper_id": "string",
      "strengthening_paper_title": "string",
      "nature_of_reinforcement": "string",
      "supporting_evidence": "string"
    }}
  ],
  "comparison_summary": "string"
}}

Return ONLY raw valid JSON without markdown fences.
"""

    client = get_genai_client()
    try:
        response = client.models.generate_content(
            model=MODEL_ID,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        analysis = json.loads(response.text)
    except Exception as e:
        return {"error": f"Failed during consistency analysis: {str(e)}"}

    # Update Firestore bidirectional links if requested
    if auto_update_links:
        contradicting_ids = [c["conflicting_paper_id"] for c in analysis.get("contradictions", []) if "conflicting_paper_id" in c]
        strengthening_ids = [s["strengthening_paper_id"] for s in analysis.get("corroborations", []) if "strengthening_paper_id" in s]

        existing_contradictions = set(target_data.get("contradictions", []))
        existing_strengthens = set(target_data.get("strengthens", []))

        updated_contradictions = list(existing_contradictions.union(contradicting_ids))
        updated_strengthens = list(existing_strengthens.union(strengthening_ids))

        db.collection(COLLECTION_NAME).document(target_paper_id).update({
            "contradictions": updated_contradictions,
            "strengthens": updated_strengthens
        })

    analysis["target_paper"] = {
        "id": target_paper_id,
        "title": target_data.get("title")
    }
    return analysis
