"""Paper summary and statement extraction tool using Gemini on Vertex AI."""
import json
from typing import Any, Dict, List, Optional
from google import genai
from google.genai import types

PROJECT_ID = "qwiklabs-gcp-03-644239e208e8"
LOCATION = "us-east1"
MODEL_ID = "gemini-2.5-flash"

_genai_client = None


def get_genai_client() -> genai.Client:
    """Singleton GenAI client using Vertex AI credentials."""
    global _genai_client
    if _genai_client is None:
        _genai_client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)
    return _genai_client


def summarize_paper(
    paper_content: str,
    title: Optional[str] = None
) -> Dict[str, Any]:
    """Extract key statements (arguments, assumptions, conclusions), generate a concise summary, and assign topic tags for a research paper.

    Args:
        paper_content: The text content, abstract, or excerpt of the paper/article.
        title: Optional title of the paper.

    Returns:
        A dictionary containing:
          - title: Inferred or provided title
          - summary: Concise overview of the paper's core thesis and findings
          - arguments: List of primary arguments presented by the authors
          - assumptions: List of underlying theoretical or empirical assumptions
          - conclusions: List of ultimate conclusions or outcomes drawn
          - topic_tags: List of standardized domain/topic tags (e.g., 'AI', 'Quantum', 'Finance', 'Data Analysis', etc.)
    """
    if not paper_content or not paper_content.strip():
        return {"error": "Paper content is empty."}

    client = get_genai_client()

    prompt = f"""You are an expert scientific analyst. Analyze the following research paper/article content carefully.

Paper Title: {title or 'Not specified'}

Paper Content:
\"\"\"
{paper_content}
\"\"\"

Extract the following in structured JSON:
1. "title": The title of the paper (use the provided title if present, otherwise extract from content).
2. "arguments": A list of key claims or logical arguments made by the authors.
3. "assumptions": A list of explicit or implicit assumptions made by the methodology or authors.
4. "conclusions": A list of primary conclusions or validated outcomes of the work.
5. "summary": A concise paragraph summarizing the paper's motivation, approach, and significant takeaways.
6. "topic_tags": A list of 2-5 high-level domain or topic tags (e.g. "AI", "Quantum", "Finance", "Data Analysis", "Natural Language Processing", "Machine Learning", "Optimization", etc.).

Return ONLY the raw JSON object conforming to this schema without markdown fences or additional commentary.
"""

    try:
        response = client.models.generate_content(
            model=MODEL_ID,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        result = json.loads(response.text)
        # Normalize keys defensively
        if "topic_tags" not in result:
            result["topic_tags"] = result.get("tags") or result.get("topics") or []
        if "arguments" not in result:
            result["arguments"] = result.get("claims") or []
        if "assumptions" not in result:
            result["assumptions"] = []
        if "conclusions" not in result:
            result["conclusions"] = result.get("outcomes") or []
        return result
    except Exception as e:
        return {"error": f"Failed to extract paper summary: {str(e)}"}
