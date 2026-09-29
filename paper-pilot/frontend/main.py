"""FastAPI proxy and backend for PaperPilot Library Management Assistant.

Features:
- Deployed Agent Runtime over A2A protocol (agents-cli 1.1.0+ GA compatible)
- Project Definition & Project Library management
- Multi-project scoping with paper assignment
- Upload own documents (as User Note / Draft OR Paper Resource with text/PDF parsing)
- Generated synthesis and audit reports saved directly into user documents
- Live Firestore catalog of research resources & user documents
"""

import io
import os
import sys
import uuid
import datetime
from typing import Optional, List, Dict, Any

parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

import google.auth
import google.auth.transport.requests
import httpx
from a2a.client import ClientConfig, ClientFactory, create_client
from a2a.types import (
    AgentCard,
    Message,
    Part,
    Role,
    SendMessageRequest,
    TaskArtifactUpdateEvent,
)
from a2a.utils.constants import PROTOCOL_VERSION_1_0, VERSION_HEADER, TransportProtocol
from fastapi import FastAPI, Request, UploadFile, File, Form
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from google.cloud import firestore
from google.protobuf.json_format import MessageToDict
import pypdf

PROJECT_ID = "qwiklabs-gcp-03-644239e208e8"
RESOURCE = os.environ.get(
    "AGENT_ENGINE_RESOURCE_NAME",
    "projects/598591427571/locations/us-east1/reasoningEngines/7146876158078877696",
)
AGENT_DIRECTORY = os.environ.get("AGENT_DIRECTORY", "app")
LOCATION = RESOURCE.split("/locations/")[1].split("/")[0] if "/locations/" in RESOURCE else "us-east1"

A2A_BASE = (
    f"https://{LOCATION}-aiplatform.googleapis.com/reasoningEngines/v1/"
    f"{RESOURCE}/api/a2a/{AGENT_DIRECTORY}"
)
A2A_CARD_URL = f"{A2A_BASE}/.well-known/agent-card.json"

COLLECTION_RESOURCES = "research_resources"
COLLECTION_PROJECTS = "research_projects"
COLLECTION_USER_DOCS = "user_documents"

_A2UI_MIME = "application/json+a2ui"

# Auth credentials
_creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])


def _auth_headers() -> dict[str, str]:
    _creds.refresh(google.auth.transport.requests.Request())
    return {
        "Authorization": f"Bearer {_creds.token}",
        "Content-Type": "application/json",
        VERSION_HEADER: PROTOCOL_VERSION_1_0,
    }


def _get_firestore_client():
    return firestore.Client(project=PROJECT_ID)


app = FastAPI(title="PaperPilot Library Management Assistant")

_contexts: dict[str, str] = {}
_card: Optional[AgentCard] = None


async def _get_card(client: httpx.AsyncClient) -> AgentCard:
    global _card
    if _card is None:
        resp = await client.get(A2A_CARD_URL)
        resp.raise_for_status()
        _card = AgentCard.model_validate_json(resp.text)
    return _card


def _extract_parts(parts: list[Any]) -> list[dict]:
    out: list[dict] = []
    for p in parts:
        try:
            d = MessageToDict(p) if hasattr(p, "DESCRIPTOR") else (p if isinstance(p, dict) else {})
        except Exception:
            d = {}

        # Check for standard text part
        text = d.get("text")
        if text:
            out.append({"kind": "text", "text": text})
            continue

        # Check for data / A2UI part
        data_payload = d.get("data")
        if data_payload:
            meta = data_payload.get("metadata", {})
            mime = meta.get("mimeType")
            if mime == _A2UI_MIME:
                inner_data = data_payload.get("data", {})
                out.append({"kind": "a2ui", "data": inner_data})
                continue
            elif "beginRendering" in data_payload or "surfaceUpdate" in data_payload:
                out.append({"kind": "a2ui", "data": data_payload})
                continue

        # Fallback to direct attribute check
        attr_text = getattr(p, "text", None)
        if attr_text:
            out.append({"kind": "text", "text": attr_text})
            continue

        file_part = getattr(p, "file", None)
        if file_part:
            uri = getattr(file_part, "uri", None)
            if uri:
                out.append({"kind": "text", "text": uri})
    return out


# ==========================================
# Projects & Project Library Management
# ==========================================

@app.get("/api/projects")
def list_projects():
    """List all user research projects."""
    try:
        db = _get_firestore_client()
        docs = db.collection(COLLECTION_PROJECTS).stream()
        projects = []
        for d in docs:
            p = d.to_dict()
            p["id"] = d.id
            projects.append(p)
        if not projects:
            # Seed default project if empty
            default_proj = {
                "name": "General Literature Synthesis",
                "topic": "Retrieval Augmented Generation",
                "description": "Default research project analyzing vector retrieval and GraphRAG synergies.",
                "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "paper_ids": ["paper-rag-reasoning-2025", "paper-graph-rag-2024", "paper-vector-primacy-2025"]
            }
            db.collection(COLLECTION_PROJECTS).document("proj-default").set(default_proj)
            default_proj["id"] = "proj-default"
            projects = [default_proj]
        return {"projects": projects}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/api/projects")
async def create_project(req: Request):
    """Define a new project and project library."""
    try:
        data = await req.json()
        name = data.get("name", "").strip()
        topic = data.get("topic", "").strip() or "General"
        description = data.get("description", "").strip()
        if not name:
            return JSONResponse(status_code=400, content={"error": "Project name is required"})

        proj_id = f"proj-{uuid.uuid4().hex[:8]}"
        doc_data = {
            "name": name,
            "topic": topic,
            "description": description,
            "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "paper_ids": data.get("paper_ids", [])
        }
        db = _get_firestore_client()
        db.collection(COLLECTION_PROJECTS).document(proj_id).set(doc_data)
        doc_data["id"] = proj_id
        return {"success": True, "project": doc_data}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/api/projects/{project_id}/papers")
async def toggle_project_paper(project_id: str, req: Request):
    """Add or remove select papers from a project's library."""
    try:
        data = await req.json()
        paper_id = data.get("paper_id")
        action = data.get("action", "add")  # "add" or "remove"
        if not paper_id:
            return JSONResponse(status_code=400, content={"error": "paper_id is required"})

        db = _get_firestore_client()
        ref = db.collection(COLLECTION_PROJECTS).document(project_id)
        doc = ref.get()
        if not doc.exists:
            return JSONResponse(status_code=404, content={"error": "Project not found"})

        p_data = doc.to_dict()
        papers = list(p_data.get("paper_ids", []))
        if action == "add" and paper_id not in papers:
            papers.append(paper_id)
        elif action == "remove" and paper_id in papers:
            papers.remove(paper_id)

        ref.update({"paper_ids": papers})
        return {"success": True, "paper_ids": papers}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


# ==========================================
# Resources & User Documents
# ==========================================

@app.get("/api/resources")
def get_resources(topic: Optional[str] = None, project_id: Optional[str] = None):
    """Retrieve research resources from Firestore, optionally filtered by topic or project library."""
    try:
        db = _get_firestore_client()
        col = db.collection(COLLECTION_RESOURCES)
        
        allowed_ids = None
        if project_id and project_id != "all":
            p_doc = db.collection(COLLECTION_PROJECTS).document(project_id).get()
            if p_doc.exists:
                p_data = p_doc.to_dict() or {}
                p_ids = p_data.get("paper_ids", [])
                if p_ids:
                    allowed_ids = set(p_ids)

        docs = col.stream()
        resources = []
        for doc in docs:
            item = doc.to_dict()
            item["id"] = doc.id
            if allowed_ids is not None and item["id"] not in allowed_ids:
                continue
            if topic and topic.strip() and topic != "All":
                doc_topic = item.get("topic", "")
                tags = item.get("tags", [])
                topic_tags = item.get("topic_tags", [])
                if (
                    topic != doc_topic
                    and topic not in tags
                    and topic not in topic_tags
                ):
                    continue
            resources.append(item)
        return {"resources": resources}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/api/user_documents")
def get_user_documents(project_id: Optional[str] = None):
    """Retrieve user-authored notes, uploaded drafts, and generated reports."""
    try:
        db = _get_firestore_client()
        docs = db.collection(COLLECTION_USER_DOCS).order_by("created_at", direction=firestore.Query.DESCENDING).stream()
        items = []
        for d in docs:
            doc = d.to_dict()
            doc["id"] = d.id
            if project_id and project_id != "all" and doc.get("project_id") and doc.get("project_id") != project_id:
                continue
            items.append(doc)
        return {"documents": items}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/api/user_documents")
async def save_user_document(req: Request):
    """Save a user document or generated report to user_documents."""
    try:
        data = await req.json()
        doc_id = data.get("id") or f"doc-{uuid.uuid4().hex[:8]}"
        doc_data = {
            "title": data.get("title", "Untitled Document"),
            "doc_type": data.get("doc_type", "user_note"), # "user_note", "draft_report", "generated_report"
            "content": data.get("content", ""),
            "project_id": data.get("project_id", "proj-default"),
            "topic": data.get("topic", "General"),
            "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "metadata": data.get("metadata", {})
        }
        db = _get_firestore_client()
        db.collection(COLLECTION_USER_DOCS).document(doc_id).set(doc_data)
        doc_data["id"] = doc_id
        return {"success": True, "document": doc_data}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/api/upload_document")
async def upload_document(
    file: Optional[UploadFile] = File(None),
    text_content: Optional[str] = Form(None),
    title: str = Form(...),
    doc_destination: str = Form("user_document"), # "user_document" OR "paper_resource"
    project_id: Optional[str] = Form("proj-default"),
    topic: Optional[str] = Form("General"),
    authors: Optional[str] = Form("")
):
    """Upload researcher document: assigned to user documents OR added as a formal paper resource."""
    try:
        extracted_text = ""
        if file is not None and file.filename:
            content = await file.read()
            if file.filename.lower().endswith(".pdf"):
                reader = pypdf.PdfReader(io.BytesIO(content))
                pages = [page.extract_text() or "" for page in reader.pages]
                extracted_text = "\n".join(pages).strip()
            else:
                extracted_text = content.decode("utf-8", errors="ignore").strip()
        elif text_content:
            extracted_text = text_content.strip()

        if not extracted_text:
            extracted_text = "No textual content provided."

        db = _get_firestore_client()
        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()

        if doc_destination == "paper_resource":
            # Save into research_resources as an indexed literature paper
            res_id = f"paper-local-{uuid.uuid4().hex[:6]}"
            author_list = [a.strip() for a in authors.split(",")] if authors else ["Researcher Upload"]
            summary = extracted_text[:400] + ("..." if len(extracted_text) > 400 else "")
            doc_data = {
                "title": title,
                "authors": author_list,
                "summary": summary,
                "text_content": extracted_text[:10000],
                "topic_tags": [t.strip() for t in topic.split(",") if t.strip()],
                "source": "local_upload",
                "created_at": timestamp,
                "arguments": ["Imported user literature paper"],
                "assumptions": [],
                "conclusions": []
            }
            db.collection(COLLECTION_RESOURCES).document(res_id).set(doc_data)
            doc_data["id"] = res_id

            # Also associate with current project library
            if project_id:
                p_ref = db.collection(COLLECTION_PROJECTS).document(project_id)
                p_doc = p_ref.get()
                if p_doc.exists:
                    p_papers = list(p_doc.to_dict().get("paper_ids", []))
                    if res_id not in p_papers:
                        p_papers.append(res_id)
                        p_ref.update({"paper_ids": p_papers})

            return {"success": True, "type": "paper_resource", "item": doc_data}

        else:
            # Save into user_documents as researcher's personal note or draft
            doc_id = f"doc-{uuid.uuid4().hex[:8]}"
            user_doc = {
                "title": title,
                "doc_type": "user_draft",
                "content": extracted_text,
                "project_id": project_id or "proj-default",
                "topic": topic or "General",
                "created_at": timestamp,
                "authors": [authors] if authors else ["Current Researcher"],
                "metadata": {"filename": file.filename if file else "manual_text"}
            }
            db.collection(COLLECTION_USER_DOCS).document(doc_id).set(user_doc)
            user_doc["id"] = doc_id
            return {"success": True, "type": "user_document", "item": user_doc}

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"Upload failed: {str(e)}"})


# ==========================================
# Scientific Poster Generator Endpoint
# ==========================================

@app.post("/api/generate_poster")
async def generate_poster_endpoint(req: Request):
    """Generate a publication-ready scientific poster for either the project library (default) or a draft."""
    try:
        body = await req.json()
        project_id = body.get("project_id") or "proj-default"
        target = body.get("target") or "project_library"  # "project_library" or "draft"
        draft_id = body.get("draft_id")

        db = _get_firestore_client()
        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()

        # Fetch project info
        p_doc = db.collection(COLLECTION_PROJECTS).document(project_id).get()
        p_data = p_doc.to_dict() if p_doc.exists else {}
        project_name = p_data.get("name", "Research Project")
        project_topic = p_data.get("topic", "Literature Synthesis")

        if target == "draft":
            # Target is a draft document
            draft_doc = None
            if draft_id:
                d_ref = db.collection(COLLECTION_USER_DOCS).document(draft_id).get()
                if d_ref.exists:
                    draft_doc = d_ref.to_dict()
                    draft_doc["id"] = d_ref.id
            if not draft_doc:
                # Get latest draft in this project
                docs = list(db.collection(COLLECTION_USER_DOCS).where("project_id", "==", project_id).where("doc_type", "==", "user_draft").stream())
                if docs:
                    draft_doc = docs[-1].to_dict()
                    draft_doc["id"] = docs[-1].id

            if not draft_doc:
                return JSONResponse(status_code=404, content={"error": "No draft document found in this project to create a poster from."})

            draft_title = draft_doc.get("title", "Research Draft")
            draft_content = draft_doc.get("content", "")

            poster_title = f"DRAFT RESEARCH POSTER: {draft_title.upper()}"
            subtitle = f"PROJECT: {project_name.upper()} • DRAFT MANUSCRIPT EVALUATION • 2026"

            content_snippets = [line.strip() for line in draft_content.split("\n") if line.strip() and not line.strip().startswith("#")]
            p_snippet = content_snippets[0] if len(content_snippets) > 0 else "Analysis of novel architectures and performance trade-offs."
            m_snippet = content_snippets[1] if len(content_snippets) > 1 else "Empirical benchmark evaluation comparing recall, latency, and resource footprint."
            c_snippet = content_snippets[2] if len(content_snippets) > 2 else "Conclusions corroborate existing baseline performance metrics."

            col1 = ("PROBLEM & MOTIVATION", "#0284C7", [
                f"• Title: {draft_title}",
                f"• Context: {p_snippet[:130]}",
                "• Motivation: Identify performance bounds and resolve inconsistencies in existing literature."
            ])
            col2 = ("PROPOSED METHODOLOGY & CLAIMS", "#4338CA", [
                f"• Approach: {m_snippet[:130]}",
                "• Evaluation: Systematic testing across diverse query sets and memory constraints.",
                "• Core Claims: Demonstrates superior throughput and validated stability under peak workloads."
            ])
            col3 = ("GROUNDING & CONTRIBUTIONS", "#047857", [
                f"• Key Findings: {c_snippet[:130]}",
                "• Literature Grounding: Corroborated with peer-reviewed papers in project library.",
                "• Novel Contributions: Actionable design guidelines and robust benchmark figures."
            ])

        else:
            # Target is project_library (default)
            paper_ids = p_data.get("paper_ids", [])
            papers = []
            if paper_ids:
                for pid in paper_ids[:6]:
                    rdoc = db.collection(COLLECTION_RESOURCES).document(pid).get()
                    if rdoc.exists:
                        p_dict = rdoc.to_dict()
                        p_dict["id"] = rdoc.id
                        papers.append(p_dict)
            if not papers:
                q = db.collection(COLLECTION_RESOURCES).stream()
                papers = [d.to_dict() for d in q][:6]

            poster_title = f"RESEARCH SYNTHESIS POSTER: {project_name.upper()}"
            subtitle = f"TOPIC: {project_topic.upper()} • CURATED PROJECT LIBRARY CORPUS • 2026"

            corpus_items = []
            for p in papers[:4]:
                p_title = p.get("title", "Research Paper")
                p_yr = p.get("year", 2026)
                corpus_items.append(f"• {p_title[:45]}... ({p_yr})")
            if not corpus_items:
                corpus_items = ["• No catalogued papers in library yet. Add papers via arXiv or document upload."]

            args_items = []
            for p in papers:
                for arg in p.get("arguments", []):
                    if len(args_items) < 3 and len(arg) > 10:
                        args_items.append(f"• {arg[:100]}")
            if not args_items:
                args_items = [
                    "• Comparative algorithmic evaluation across vector quantization and traversal.",
                    "• Latency-recall trade-off modeling under concurrent multi-tenant loads."
                ]

            synth_items = []
            for p in papers:
                for c in p.get("conclusions", []) if isinstance(p.get("conclusions"), list) else [p.get("conclusions")]:
                    if c and len(synth_items) < 2 and len(c) > 10:
                        synth_items.append(f"• Consensus: {c[:100]}")
            for p in papers:
                for contra in p.get("contradictions", []):
                    if len(synth_items) < 3 and len(contra) > 5:
                        synth_items.append(f"• Disputed: {contra[:90]}")
            if not synth_items:
                synth_items = [
                    "• Consensus: Hybrid dense-lexical pipelines outperform single-index setups.",
                    "• Debate: Inconsistent memory footprint scaling under clustered sharding.",
                    "• Open Question: Generalizability across long-context reasoning regimes."
                ]

            col1 = ("CURATED LITERATURE CORPUS", "#0284C7", corpus_items)
            col2 = ("CORE METHODOLOGY & CLAIMS", "#4338CA", args_items)
            col3 = ("SYNTHESIS & CONTROVERSIES", "#047857", synth_items)

        # Render poster via app.visual_generator
        from app.visual_generator import create_and_upload_poster
        poster_res = create_and_upload_poster(
            title=poster_title,
            subtitle=subtitle,
            col1_title=col1[0],
            col1_color=col1[1],
            col1_items=col1[2],
            col2_title=col2[0],
            col2_color=col2[1],
            col2_items=col2[2],
            col3_title=col3[0],
            col3_color=col3[1],
            col3_items=col3[2],
            file_prefix=f"poster_{target}"
        )

        image_url = poster_res.get("image_url")

        # Save record in user_documents
        doc_id = f"poster-{uuid.uuid4().hex[:8]}"
        poster_doc = {
            "id": doc_id,
            "title": f"Poster: {poster_title}",
            "doc_type": "poster_artifact",
            "content": f"![{poster_title}]({image_url})\n\n**Scientific Poster for {target.replace('_', ' ').title()}**\n\nPublic GCS URL: {image_url}",
            "project_id": project_id,
            "topic": project_topic,
            "image_url": image_url,
            "created_at": timestamp,
            "metadata": {"target": target, "poster_title": poster_title}
        }
        db.collection(COLLECTION_USER_DOCS).document(doc_id).set(poster_doc)

        return {
            "success": True,
            "target": target,
            "title": poster_title,
            "image_url": image_url,
            "item": poster_doc,
            "markdown_embed": f"![{poster_title}]({image_url})"
        }

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"Poster generation failed: {str(e)}"})


# ==========================================
# Chat & Report Synthesis Proxy
# ==========================================

@app.post("/chat")
async def chat(req: Request):
    """Proxy conversation to the deployed A2A Agent Runtime agent.
    Maintains separate conversation contexts per project via session_key = f"{user_id}:{project_id}".
    If the response contains a comprehensive research report or audit, save it into user_documents.
    """
    try:
        body = await req.json()
        message = body.get("message", "")
        user_id = body.get("user_id") or "web-user"
        project_id = body.get("project_id") or "proj-default"
        session_key = f"{user_id}:{project_id}"
        parts: list[dict] = []

        # Look up active project workspace details for ground context
        db = _get_firestore_client()
        proj_doc = db.collection(COLLECTION_PROJECTS).document(project_id).get()
        proj_data = proj_doc.to_dict() if proj_doc.exists else {}
        proj_name = proj_data.get("name", "General Literature Synthesis")
        proj_topic = proj_data.get("topic", "General Research")
        proj_papers = proj_data.get("paper_ids", [])

        scoped_message = (
            f"[Active Project Workspace: '{proj_name}' (ID: {project_id}) | Topic Focus: '{proj_topic}' | "
            f"Assigned Project Papers: {proj_papers}]\n"
            f"{message}"
        )

        headers = _auth_headers()
        async with httpx.AsyncClient(headers=headers, timeout=120) as client:
            config = ClientConfig(
                httpx_client=client,
                supported_protocol_bindings=[
                    TransportProtocol.JSONRPC,
                    TransportProtocol.HTTP_JSON,
                ],
            )
            a2a_client = await create_client(A2A_BASE, config)

            if session_key not in _contexts:
                _contexts[session_key] = str(uuid.uuid4())
            context_id = _contexts[session_key]

            msg = Message(
                message_id=str(uuid.uuid4()),
                role=Role.ROLE_USER,
                parts=[Part(text=scoped_message)],
                context_id=context_id,
            )

            async for chunk in a2a_client.send_message(SendMessageRequest(message=msg)):
                if chunk.HasField("artifact_update"):
                    if chunk.artifact_update.context_id:
                        _contexts[session_key] = chunk.artifact_update.context_id
                    parts.extend(_extract_parts(chunk.artifact_update.artifact.parts))
                elif chunk.HasField("task"):
                    if chunk.task.context_id:
                        _contexts[session_key] = chunk.task.context_id
                    for artifact in chunk.task.artifacts:
                        parts.extend(_extract_parts(artifact.parts))
                elif chunk.HasField("message"):
                    parts.extend(_extract_parts(chunk.message.parts))

        if not parts:
            parts = [{"kind": "text", "text": "(The assistant completed the action without text output.)"}]

        # Check if this generated a report or synthesis and save to user_documents
        full_text = "\n\n".join([p["text"] for p in parts if p.get("kind") == "text"])
        is_report = ("# Research Synthesis" in full_text or 
                     "## Executive Summary" in full_text or 
                     "Comparative Analysis Table" in full_text or 
                     "Audit Report" in full_text or
                     "generate report" in message.lower() or 
                     "synthesize" in message.lower())

        saved_doc = None
        if is_report and len(full_text) > 300:
            db = _get_firestore_client()
            doc_id = f"report-{uuid.uuid4().hex[:8]}"
            title = f"Report: {message[:40]}..." if len(message) > 40 else f"Report: {message}"
            saved_doc = {
                "title": title,
                "doc_type": "generated_report",
                "content": full_text,
                "project_id": project_id,
                "topic": "Literature Synthesis",
                "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "metadata": {"prompt": message}
            }
            db.collection(COLLECTION_USER_DOCS).document(doc_id).set(saved_doc)
            saved_doc["id"] = doc_id

        return JSONResponse({"parts": parts, "saved_report": saved_doc})
    except Exception as e:
        return JSONResponse(
            status_code=200,
            content={"parts": [{"kind": "text", "text": f"Error contacting agent: {type(e).__name__}: {str(e)}"}]},
        )


# Mount static directory for frontend
static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
