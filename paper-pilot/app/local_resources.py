"""Local document and notes ingestion tools for PaperPilot."""
import os
import uuid
from typing import Any, Dict, List, Optional
import pypdf

from app.firestore_tools import save_resource
from app.summarizer import summarize_paper


def _extract_text_from_file(file_path: str) -> str:
    """Extract plain text from local txt, md, or pdf files."""
    if not os.path.isabs(file_path):
        file_path = os.path.abspath(file_path)

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found at: {file_path}")

    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".pdf":
        reader = pypdf.PdfReader(file_path)
        text_chunks = []
        for i, page in enumerate(reader.pages):
            extracted = page.extract_text()
            if extracted:
                text_chunks.append(extracted)
            if i >= 15:  # Cap at first 15 pages for summarization efficiency
                break
        return "\n\n".join(text_chunks)
    else:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()


def add_local_paper(
    topic: str,
    pdf_path: Optional[str] = None,
    text_content: Optional[str] = None,
    title: Optional[str] = None,
    author: Optional[str] = None,
    authors: Optional[List[str]] = None,
    paper_uuid: Optional[str] = None,
    auto_summarize: bool = True
) -> Dict[str, Any]:
    """Add a local research paper into the library from a PDF/text file or text content.

    Args:
        topic: The research project or topic this paper belongs to (e.g. 'Quantum Computing').
        pdf_path: Local file path to the PDF (or text/markdown) document.
        text_content: Direct text content or abstract if file is not provided.
        title: Title of the paper (if known; otherwise extracted).
        author: Primary author name (optional).
        authors: List of author names (optional).
        paper_uuid: Custom unique ID/UUID (optional; automatically generated if omitted).
        auto_summarize: Whether to extract arguments, assumptions, conclusions, and tags via Gemini.

    Returns:
        A dictionary with the saved paper details and extraction results.
    """
    raw_content = ""
    if pdf_path:
        try:
            raw_content = _extract_text_from_file(pdf_path)
        except Exception as e:
            return {"error": f"Failed to read file from '{pdf_path}': {str(e)}"}
    elif text_content:
        raw_content = text_content
    else:
        return {"error": "Either 'pdf_path' or 'text_content' must be provided."}

    # Normalize authors
    author_list = authors or []
    if author and author not in author_list:
        author_list.append(author)

    resource_id = paper_uuid or f"paper-{uuid.uuid4().hex[:8]}"

    extracted_title = title
    extracted_summary = ""
    extracted_arguments: List[str] = []
    extracted_assumptions: List[str] = []
    extracted_conclusions = ""
    extracted_tags: List[str] = []

    if auto_summarize and raw_content.strip():
        summary_result = summarize_paper(raw_content[:8000], title=title)
        if "error" not in summary_result:
            extracted_title = title or summary_result.get("title") or "Untitled Paper"
            extracted_summary = summary_result.get("summary", "")
            extracted_arguments = summary_result.get("arguments", [])
            extracted_assumptions = summary_result.get("assumptions", [])
            concl = summary_result.get("conclusions", [])
            extracted_conclusions = concl if isinstance(concl, str) else "; ".join(concl)
            extracted_tags = summary_result.get("topic_tags", [])

    final_title = extracted_title or title or (os.path.basename(pdf_path) if pdf_path else "Untitled Paper")

    res = save_resource(
        resource_id=resource_id,
        title=final_title,
        topic=topic,
        conclusions=extracted_conclusions,
        arguments=extracted_arguments,
        assumptions=extracted_assumptions,
        summary=extracted_summary,
        authors=author_list,
        findings=raw_content[:2000] if not extracted_summary else "",
        tags=extracted_tags,
        source="local_file" if pdf_path else "local_text"
    )

    return {
        "status": "success",
        "resource_id": resource_id,
        "title": final_title,
        "topic": topic,
        "authors": author_list,
        "summary": extracted_summary,
        "arguments": extracted_arguments,
        "assumptions": extracted_assumptions,
        "conclusions": extracted_conclusions,
        "tags": extracted_tags,
        "source": "local_file" if pdf_path else "local_text"
    }


def add_project_note(
    topic: str,
    note_content: str,
    title: Optional[str] = None,
    note_uuid: Optional[str] = None,
    author: Optional[str] = "User"
) -> Dict[str, Any]:
    """Add a researcher note or thought memo for a project or topic.

    Args:
        topic: The project or research topic the note belongs to.
        note_content: The content of the user note or brainstorm.
        title: Optional title for the note.
        note_uuid: Custom unique ID/UUID (optional).
        author: The note creator (defaults to 'User').

    Returns:
        Status and saved note details.
    """
    resource_id = note_uuid or f"note-{uuid.uuid4().hex[:8]}"
    note_title = title or f"Note: {note_content[:40]}..."

    save_resource(
        resource_id=resource_id,
        title=note_title,
        topic=topic,
        conclusions="",
        arguments=[],
        assumptions=[],
        summary=note_content,
        authors=[author],
        findings=note_content,
        tags=["notes", "user-draft"],
        source="user_note"
    )

    return {
        "status": "success",
        "note_id": resource_id,
        "title": note_title,
        "topic": topic,
        "author": author,
        "content": note_content
    }
