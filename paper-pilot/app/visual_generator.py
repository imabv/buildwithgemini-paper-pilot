"""Visual generator tool for PaperPilot (conceptual diagrams, graphical abstracts, and topic covers)."""
import io
import uuid
from typing import Any, Dict, Optional
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from google.cloud import storage

PROJECT_ID = "qwiklabs-gcp-03-644239e208e8"
BUCKET_NAME = "paper-pilot-storage-qwiklabs-gcp-03-644239e208e8"

_storage_client = None


def get_storage_client() -> storage.Client:
    """Singleton Storage client."""
    global _storage_client
    if _storage_client is None:
        _storage_client = storage.Client(project=PROJECT_ID)
    return _storage_client


def _render_scientific_diagram(title: str, prompt: str, artifact_type: str) -> bytes:
    """Render a clean, high-resolution publication-grade scientific diagram card."""
    fig, ax = plt.subplots(figsize=(10, 5.625), dpi=150)
    fig.patch.set_facecolor("#0F172A")  # Deep slate navy
    ax.set_facecolor("#1E293B")

    # Title Banner
    ax.text(
        0.5, 0.88, title.upper(),
        fontsize=16, fontweight="bold", color="#38BDF8",
        ha="center", va="center", transform=ax.transAxes,
        family="sans-serif"
    )

    # Subtitle / artifact type badge
    ax.text(
        0.5, 0.80, f"PAPERPILOT SCIENTIFIC VISUAL • {artifact_type.replace('_', ' ').upper()}",
        fontsize=9, color="#94A3B8", ha="center", va="center", transform=ax.transAxes
    )

    # Conceptual Architecture Nodes
    # Left Block: Literature & Data
    rect1 = patches.FancyBboxPatch(
        (0.08, 0.32), 0.24, 0.36,
        boxstyle="round,pad=0.03",
        linewidth=1.5, edgecolor="#0284C7", facecolor="#0369A1"
    )
    ax.add_patch(rect1)
    ax.text(0.20, 0.54, "INPUT CORPUS\n& PAPERS", color="#FFFFFF", fontsize=11, fontweight="bold", ha="center", va="center")
    ax.text(0.20, 0.40, "• Local PDF/Notes\n• arXiv Literature\n• Findings & Claims", color="#E0F2FE", fontsize=8, ha="center", va="center")

    # Middle Block: Verification & Reasoning Pipeline
    rect2 = patches.FancyBboxPatch(
        (0.38, 0.28), 0.24, 0.44,
        boxstyle="round,pad=0.03",
        linewidth=1.5, edgecolor="#6366F1", facecolor="#4338CA"
    )
    ax.add_patch(rect2)
    ax.text(0.50, 0.56, "SYNTHESIS &\nCONSISTENCY", color="#FFFFFF", fontsize=11, fontweight="bold", ha="center", va="center")
    ax.text(0.50, 0.39, "• Contradiction Matrix\n• Corroboration Engine\n• Claim Grounding\n• Gemini 2.5 Flash", color="#E0E7FF", fontsize=8, ha="center", va="center")

    # Right Block: Consolidated Insights & Dossier
    rect3 = patches.FancyBboxPatch(
        (0.68, 0.32), 0.24, 0.36,
        boxstyle="round,pad=0.03",
        linewidth=1.5, edgecolor="#10B981", facecolor="#047857"
    )
    ax.add_patch(rect3)
    ax.text(0.80, 0.54, "SYNTHESIS\nDOSSIER", color="#FFFFFF", fontsize=11, fontweight="bold", ha="center", va="center")
    ax.text(0.80, 0.40, "• Comparative Matrix\n• Audited Drafts\n• Validated Findings", color="#D1FAE5", fontsize=8, ha="center", va="center")

    # Connector arrows
    arrow1 = patches.FancyArrowPatch((0.32, 0.50), (0.38, 0.50), arrowstyle="->,head_width=4,head_length=5", color="#38BDF8", lw=2)
    arrow2 = patches.FancyArrowPatch((0.62, 0.50), (0.68, 0.50), arrowstyle="->,head_width=4,head_length=5", color="#34D399", lw=2)
    ax.add_patch(arrow1)
    ax.add_patch(arrow2)

    # Concept prompt caption
    summary_text = prompt[:100] + ("..." if len(prompt) > 100 else "")
    ax.text(
        0.5, 0.12, f"Focus: {summary_text}",
        fontsize=9, fontstyle="italic", color="#CBD5E1",
        ha="center", va="center", transform=ax.transAxes,
        wrap=True
    )

    ax.axis("off")
    buf = io.BytesIO()
    plt.tight_layout()
    plt.savefig(buf, format="png", bbox_inches="tight", facecolor=fig.get_facecolor(), edgecolor="none")
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()


def generate_visual_artifact(
    prompt: str,
    title: Optional[str] = None,
    artifact_type: str = "graphical_abstract"
) -> Dict[str, Any]:
    """Generate a conceptual overview diagram, graphical abstract, or topic cover image and host it publicly on GCS.

    Args:
        prompt: Detailed visual description of what the diagram, abstract, or cover should depict.
        title: Optional title or topic name for the image.
        artifact_type: Type of artifact: 'graphical_abstract', 'concept_diagram', or 'topic_cover'.

    Returns:
        A dictionary with the public image URL, bucket path, and markdown embed code.
    """
    if not prompt or not prompt.strip():
        return {"error": "Prompt cannot be empty."}

    clean_title = title or "Research Concept Diagram"
    file_id = f"visual_{artifact_type}_{uuid.uuid4().hex[:6]}.png"

    try:
        image_bytes = _render_scientific_diagram(clean_title, prompt, artifact_type)
    except Exception as e:
        return {"error": f"Diagram rendering failed: {str(e)}"}

    # Upload to Cloud Storage bucket
    try:
        gcs = get_storage_client()
        bucket = gcs.bucket(BUCKET_NAME)
        blob = bucket.blob(file_id)
        blob.upload_from_string(image_bytes, content_type="image/png")
    except Exception as e:
        return {"error": f"Failed to upload image to Cloud Storage: {str(e)}"}

    public_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{file_id}"

    return {
        "status": "success",
        "title": clean_title,
        "artifact_type": artifact_type,
        "image_url": public_url,
        "bucket_path": f"gs://{BUCKET_NAME}/{file_id}",
        "markdown_embed": f"![{clean_title}]({public_url})"
    }
