"""Automated end-to-end verification script for PaperPilot agent capabilities."""
import sys
import pprint

print("=== Starting PaperPilot Capabilities Verification ===\n")

# 1. Literature Search
from app.academic_search import search_academic_literature
print("--> Testing Capability 1: Academic Literature Search")
papers = search_academic_literature("Retrieval Augmented Generation", max_results=2)
assert len(papers) > 0, "Failed to retrieve papers from arXiv"
assert "title" in papers[0], "Paper missing title"
print(f"✓ Retrieved {len(papers)} papers from arXiv. Sample: '{papers[0]['title']}'\n")

# 2. Local Document & Notes Ingestion
from app.local_resources import add_local_paper, add_project_note
print("--> Testing Capability 2: Local Resources & Notes Ingestion")
note_res = add_project_note(
    topic="Vector Retrieval",
    note_content="Assess latency trade-offs between HNSW and ScaNN for production scale.",
    title="HNSW vs ScaNN exploration"
)
assert note_res["status"] == "success"
print(f"✓ Ingested user project note: ID '{note_res['note_id']}'")

paper_res = add_local_paper(
    topic="Vector Retrieval",
    text_content="We present an empirical benchmark of vector indices. HNSW demonstrates higher recall (98%) compared to IVF-PQ (91%) under high query loads, though requiring 3x memory footprint.",
    title="Empirical Evaluation of Vector Index Architectures",
    author="D. Lee",
    paper_uuid="paper-vec-bench-2026",
    auto_summarize=True
)
assert paper_res["status"] == "success"
print(f"✓ Ingested local paper: '{paper_res['title']}'\n")

# 3. Paper Summarization & Statement Extraction
from app.summarizer import summarize_paper
print("--> Testing Capability 3: Paper Summarization & Tagging")
sample_text = (
    "Quantum Annealing for Combinatorial Logistics. "
    "We assume transverse-field Ising Hamiltonians with all-to-all connectivity. "
    "We argue that coherent quantum tunneling bypasses tall energy barriers in traveling salesperson instances. "
    "We conclude that D-Wave processors achieve 4x speedup over simulated annealing on 50-city benchmarks."
)
summary_res = summarize_paper(sample_text, title="Quantum Annealing for Logistics")
assert "arguments" in summary_res and "conclusions" in summary_res and "topic_tags" in summary_res
print(f"✓ Extracted {len(summary_res['arguments'])} arguments, conclusions: '{summary_res['conclusions']}'")
print(f"  Topic tags assigned: {summary_res['topic_tags']}\n")

# 4. Consistency & Verification Analyzer
from app.consistency_analyzer import analyze_cross_paper_consistency
print("--> Testing Capability 4: Consistency & Verification Analyzer (Contradictions & Corroborations)")
consistency_res = analyze_cross_paper_consistency("paper-graph-rag-2024")
assert "contradictions" in consistency_res
assert "corroborations" in consistency_res
print(f"✓ Discovered {len(consistency_res['contradictions'])} contradiction(s) and {len(consistency_res['corroborations'])} corroboration(s)")
print()

# 5. Draft Report Auditor & Ungrounded Claim Detection
from app.report_auditor import audit_draft_report
print("--> Testing Capability 5: Draft Report Auditor")
draft = (
    "In our research, we find that graph-based retrieval enhances relationship extraction. "
    "However, we also claim that quantum computers can currently replace all vector databases with zero cost. "
    "Our novel contribution is a hybrid routing algorithm that switches between graph and dense search dynamically."
)
audit_res = audit_draft_report(draft, topic="Retrieval Augmented Generation")
assert "grounded_claims" in audit_res or "ungrounded_claims" in audit_res
print(f"✓ Audited draft: Found {len(audit_res.get('grounded_claims', []))} grounded, "
      f"{len(audit_res.get('ungrounded_claims', []))} ungrounded claims, and "
      f"{len(audit_res.get('user_contributions', []))} user contribution(s).\n")

# 6. Note & Synthesis Consolidator
from app.synthesis_consolidator import consolidate_project_synthesis
print("--> Testing Capability 6: Note & Synthesis Consolidator")
synthesis_res = consolidate_project_synthesis("Retrieval Augmented Generation")
report_md = synthesis_res.get("report_markdown", "")
assert len(report_md) > 50, f"Synthesis report too short: {report_md}"
print(f"✓ Generated comparative synthesis report ({len(report_md)} chars) with key conclusions.\n")

# 7. Image Generation & Visual Artifacts
from app.visual_generator import generate_visual_artifact
print("--> Testing Capability 7: Visual Artifact Generation")
visual_res = generate_visual_artifact(
    prompt="Abstract vector search vs graph knowledge network with glowing interconnected nodes",
    title="Graph vs Vector Topology",
    artifact_type="graphical_abstract"
)
assert visual_res["status"] == "success" and "https://storage.googleapis.com" in visual_res["image_url"]
print(f"✓ Generated visual and uploaded to public bucket: {visual_res['image_url']}\n")

print("=== ALL 7 CAPABILITIES VERIFIED SUCCESSFULLY! ===")
