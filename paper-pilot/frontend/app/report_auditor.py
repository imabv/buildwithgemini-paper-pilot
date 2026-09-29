"""Draft report auditor tool for ungrounded claims and novel contribution extraction."""
import json
from typing import Any, Dict, List, Optional
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


def audit_draft_report(
    draft_text: str,
    topic: Optional[str] = None
) -> Dict[str, Any]:
    """Audit a user's draft report or research paper against the existing library of resources.

    Checks for ungrounded claims, validates consistency against literature, and extracts the author's novel contributions.

    Args:
        draft_text: The draft report or paper text submitted by the user.
        topic: Optional topic filter to look up reference literature.

    Returns:
        A dictionary containing:
          - grounded_claims: Claims supported by the literature with citation references.
          - ungrounded_claims: Claims made in the draft that lack evidence or citation in the literature.
          - contradictions: Claims that conflict with findings in the literature.
          - user_contributions: Novel claims, methodologies, or findings introduced by the author.
          - audit_summary: High-level verification verdict.
    """
    if not draft_text or not draft_text.strip():
        return {"error": "Draft text is empty."}

    resources = list_resources(topic=topic) if topic else list_resources()
    lit_context = [
        {
            "id": r.get("id"),
            "title": r.get("title"),
            "arguments": r.get("arguments", []),
            "conclusions": r.get("conclusions", ""),
            "findings": r.get("findings", "")
        }
        for r in resources
    ]

    prompt = f"""You are a rigorous peer-review auditor. Review the following DRAFT REPORT against the provided REFERENCE LITERATURE.

REFERENCE LITERATURE:
{json.dumps(lit_context, indent=2)}

DRAFT REPORT:
\"\"\"
{draft_text}
\"\"\"

Analyze the report and extract:
1. "grounded_claims": Claims that are directly supported by papers in the reference literature, indicating the supporting paper id and title.
2. "ungrounded_claims": Assertions or factual claims made in the report that have NO supporting evidence or citation in the reference literature.
3. "contradictions": Claims in the draft that contradict findings or conclusions in the reference literature.
4. "user_contributions": The author's original proposals, novel methodologies, or new findings (as distinct from background facts).
5. "audit_summary": A concise evaluation of the draft's grounding, rigor, and readiness.

Return a JSON object conforming strictly to this structure:
{{
  "grounded_claims": [
    {{"claim": "string", "supported_by": "paper-id", "paper_title": "string"}}
  ],
  "ungrounded_claims": [
    {{"claim": "string", "risk_level": "low|medium|high", "recommendation": "string"}}
  ],
  "contradictions": [
    {{"claim": "string", "conflicts_with": "paper-id", "explanation": "string"}}
  ],
  "user_contributions": [
    {{"contribution": "string", "significance": "string"}}
  ],
  "audit_summary": "string"
}}

Return ONLY raw JSON without markdown fences.
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
        return json.loads(response.text)
    except Exception as e:
        return {"error": f"Failed to audit draft report: {str(e)}"}
