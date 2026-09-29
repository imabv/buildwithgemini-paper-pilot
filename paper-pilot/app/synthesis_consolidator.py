"""Synthesis and notes consolidator tool for generating structured comparative reports."""
import json
from typing import Any, Dict, Optional
from google import genai
from google.genai import types

from app.firestore_tools import list_resources

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


def consolidate_project_synthesis(
    topic: str
) -> Dict[str, Any]:
    """Consolidate all notes, paper summaries, arguments, and conclusions for a given project topic into a structured comparative report.

    Args:
        topic: The project or research topic to consolidate (e.g., 'Retrieval Augmented Generation').

    Returns:
        A dictionary with the formatted markdown comparative report, summary tables, and key takeaways.
    """
    resources = list_resources(topic=topic)
    if not resources:
        return {"error": f"No resources or notes found for topic '{topic}'."}

    papers = [r for r in resources if r.get("source") != "user_note"]
    notes = [r for r in resources if r.get("source") == "user_note"]

    payload = {
        "topic": topic,
        "papers": [
            {
                "id": p.get("id"),
                "title": p.get("title"),
                "authors": p.get("authors", []),
                "summary": p.get("summary", ""),
                "arguments": p.get("arguments", []),
                "conclusions": p.get("conclusions", ""),
                "contradictions": p.get("contradictions", []),
                "strengthens": p.get("strengthens", [])
            }
            for p in papers
        ],
        "notes": [
            {
                "id": n.get("id"),
                "title": n.get("title"),
                "content": n.get("summary") or n.get("findings", "")
            }
            for n in notes
        ]
    }

    prompt = f"""You are an executive research director. Synthesize the following papers and user notes for the research topic '{topic}'.

COLLECTED RESOURCES & NOTES:
{json.dumps(payload, indent=2)}

Create an exhaustive, beautifully formatted markdown research report. Include:
# Research Synthesis: {topic}
## 1. Executive Summary & Core Consensus
## 2. Comparative Analysis Table (Columns: Paper/Resource, Core Thesis/Approach, Key Conclusions, Limitations/Trade-offs)
## 3. Contradictions & Open Debates
## 4. Integration with Researcher Notes
## 5. Recommended Next Directions

Return the response directly as clean Markdown text.
"""

    client = get_genai_client()
    try:
        response = client.models.generate_content(
            model=MODEL_ID,
            contents=prompt,
        )
        report_text = response.text.strip()
        return {
            "topic": topic,
            "paper_count": len(papers),
            "note_count": len(notes),
            "report_markdown": report_text,
            "status": "success"
        }
    except Exception as e:
        return {"error": f"Failed to consolidate project synthesis: {str(e)}"}
