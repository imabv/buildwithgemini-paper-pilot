# PaperPilot: Agent Capabilities & Testing Scenarios

This document specifies the primary capabilities of the **PaperPilot** research literature and synthesis agent, defines testing scenarios for each capability, and records the verification results.

---

## Capabilities Overview

1. **Academic Literature Search (`search_academic_literature`)**: Search arXiv for preprints and peer-reviewed literature by topic, keywords, or research questions, returning structured metadata (title, authors, summary, published date, PDF link).
2. **Local Paper & Note Ingestion (`add_local_paper`, `add_project_note`)**: Ingest researcher PDFs and text files with automatic metadata and summary extraction, or log ad-hoc researcher notes and hypotheses into the project dossier.
3. **Paper Summarization & Statement Extraction (`summarize_paper`)**: Extract structured scientific statements (arguments, assumptions, conclusions), concise summaries, and standardized domain topic tags (e.g., AI, Quantum, Finance, Optimization).
4. **Consistency & Verification Analyzer (`analyze_cross_paper_consistency`)**: Compare a target paper or claim against the literature corpus to identify corroborations (strengthens) and contradictions (disagreements), updating relational links in Firestore.
5. **Draft Report Auditor (`audit_draft_report`)**: Audit researcher draft manuscripts or lab reports against literature to classify grounded claims, flag ungrounded/unverified claims, note literature contradictions, and highlight the researcher's novel contributions.
6. **Note & Synthesis Consolidator (`consolidate_project_synthesis`)**: Synthesize all collected papers, notes, arguments, and conclusions for a given research topic into an executive summary report with a comparative analysis table.
7. **Scientific Visual Artifact Generation (`generate_visual_artifact`)**: Generate publication-grade conceptual diagrams, graphical abstracts, or topic covers, uploading them to Google Cloud Storage with markdown embed links.

---

## Detailed Testing Scenarios & Verification

### Capability 1: Academic Literature Search
*Tool*: `search_academic_literature`

#### Scenario 1.1: Querying cutting-edge topics (e.g. Autoregressive RAG)
- **Input**: `query="Retrieval Augmented Generation autoregressive"`, `max_results=2`
- **Expected Behavior**: Connects to the arXiv API, parses Atom XML feed, and returns a list of dictionaries with `title`, `authors`, `summary`, `published`, and `pdf_url`.
- **Verification Result**: **PASS**. Retrieved 2 papers including *"AR-RAG: Autoregressive Retrieval Augmentation for Image Generation"* with full metadata and valid arXiv PDF URLs.

#### Scenario 1.2: General AI query with constrained result count
- **Input**: `query="graph neural networks drug discovery"`, `max_results=3`
- **Expected Behavior**: Exactly 3 papers returned with non-empty titles and summaries.
- **Verification Result**: **PASS**. Output matches schema without rate-limiting or network issues.

---

### Capability 2: Local Paper & Note Ingestion
*Tools*: `add_local_paper`, `add_project_note`

#### Scenario 2.1: Ingestion of informal researcher hypothesis / observation
- **Input**: `topic="Vector Retrieval"`, `title="HNSW Cache Observation"`, `content="HNSW graph traversal hits 99.4% L3 cache residency on modern AVX-512 nodes."`
- **Expected Behavior**: Stores document in Firestore with `source="user_note"`, assigns a UUID note ID, and returns confirmation.
- **Verification Result**: **PASS**. Ingested note with ID (e.g., `note-25259f2b`), successfully retrieved from Firestore.

#### Scenario 2.2: Local PDF / text paper ingestion with auto-summarization
- **Input**: `title="Empirical Evaluation of Vector Index Architectures"`, `authors=["Dr. A. Vance"]`, `text_content="We benchmark IVF vs HNSW indexes across 10M embeddings..."`
- **Expected Behavior**: Executes `summarize_paper` on the provided text, extracts arguments/conclusions, sets topic tags, and persists to Firestore under `research_resources`.
- **Verification Result**: **PASS**. Document persisted with structured arguments and conclusions.

---

### Capability 3: Paper Summarization & Statement Extraction
*Tool*: `summarize_paper`

#### Scenario 3.1: Dense scientific abstract statement decomposition
- **Input**: Text describing a quantum annealing speedup on traveling salesperson benchmarks with specific assumptions regarding transverse-field Ising Hamiltonians.
- **Expected Behavior**:
  - `arguments`: Contains claims regarding coherent quantum tunneling bypassing energy barriers.
  - `assumptions`: Contains transverse-field Ising Hamiltonian connectivity.
  - `conclusions`: Identifies 4x speedup on 50-city benchmarks.
  - `topic_tags`: Assigns relevant tags such as `['Quantum Computing', 'Optimization', 'Logistics']`.
- **Verification Result**: **PASS**. Extracted arguments, assumptions, conclusions, and assigned 5 accurate topic tags.

---

### Capability 4: Consistency & Verification Analyzer
*Tool*: `analyze_cross_paper_consistency`

#### Scenario 4.1: Cross-paper contradiction and corroboration detection
- **Input**: `target_paper_id="paper-seed-003"` (GraphRAG paper) evaluated against topic `"Retrieval Augmented Generation"`.
- **Corpus Context**: Seed papers contain claims that pure dense vectors fail on multi-hop relationships (`paper-seed-001` vs `paper-seed-003`).
- **Expected Behavior**: Identifies contradiction between pure dense vector retrieval assumptions and knowledge graph multi-hop evidence; finds corroboration regarding retrieval latency trade-offs; updates Firestore links.
- **Verification Result**: **PASS**. Discovered 1 contradiction and 1 corroboration. Updated `paper-seed-003` in Firestore with corroborated and contradictory paper links.

---

### Capability 5: Draft Report Auditor
*Tool*: `audit_draft_report`

#### Scenario 5.1: Validating researcher manuscript with mixed claims
- **Input**: A draft claiming:
  1. Dense vector retrieval reduces hallucination rates (standard literature claim).
  2. Our novel hybrid pipeline achieves 35ms p99 latency using cache quantization (novel contribution).
  3. LLMs need zero context windows when using embeddings (unsupported / ungrounded claim).
- **Expected Behavior**:
  - Classifies claim 1 as `grounded_claims` with literature citation.
  - Classifies claim 2 as `user_contributions`.
  - Flags claim 3 as `ungrounded_claims` with critique.
- **Verification Result**: **PASS**. Successfully separated 1 grounded claim, 1 ungrounded claim, and 1 user contribution.

---

### Capability 6: Note & Synthesis Consolidator
*Tool*: `consolidate_project_synthesis`

#### Scenario 6.1: Full project dossier consolidation
- **Input**: `topic="Retrieval Augmented Generation"`
- **Expected Behavior**: Aggregates all papers and user notes matching the topic; generates a structured comparative report with:
  1. Executive Summary & Core Consensus
  2. Markdown Comparative Table (Paper/Resource, Core Thesis, Key Conclusions, Trade-offs)
  3. Contradictions & Open Debates
  4. Integration with Researcher Notes
  5. Recommended Next Directions
- **Verification Result**: **PASS**. Generated comprehensive 8,997-character synthesis report with formatted comparative tables and debate breakdown.

---

### Capability 7: Scientific Visual Artifact Generation
*Tool*: `generate_visual_artifact`

#### Scenario 7.1: Publication graphical abstract generation
- **Input**: `prompt="Abstract vector search vs graph knowledge network with glowing interconnected nodes"`, `title="Graph vs Vector Topology"`, `artifact_type="graphical_abstract"`
- **Expected Behavior**: Generates high-resolution scientific visual card, uploads PNG to `gs://paper-pilot-storage-qwiklabs-gcp-03-644239e208e8/`, and returns a publicly viewable URL and markdown embed code.
- **Verification Result**: **PASS**. Generated image and uploaded to GCS. Verified accessible public URL:
  `https://storage.googleapis.com/paper-pilot-storage-qwiklabs-gcp-03-644239e208e8/visual_graphical_abstract_232ce2.png`

---

## Verification Summary Matrix

| # | Capability | Primary Function | Test Scenario | Status |
|---|---|---|---|---|
| 1 | Academic Literature Search | `search_academic_literature` | arXiv query on Autoregressive RAG | **VERIFIED** |
| 2 | Local Resource Ingestion | `add_local_paper`, `add_project_note` | User note & local paper indexing | **VERIFIED** |
| 3 | Statement Extraction | `summarize_paper` | Assumptions, claims & tag extraction | **VERIFIED** |
| 4 | Consistency Analyzer | `analyze_cross_paper_consistency` | Corroboration & contradiction matrix | **VERIFIED** |
| 5 | Draft Report Auditor | `audit_draft_report` | Grounded, ungrounded & novel claims | **VERIFIED** |
| 6 | Synthesis Consolidator | `consolidate_project_synthesis` | Comparative table & executive synthesis | **VERIFIED** |
| 7 | Visual Generator | `generate_visual_artifact` | Publication visual card & GCS upload | **VERIFIED** |
