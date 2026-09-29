# My agent: PaperPilot
One-liner: A conversational research and library management agent that helps researchers organize project dossiers, summarize literature, verify cross-paper consistency, and validate draft reports against a local and fetched catalog of research papers.

Tool coverage:
- Memory: Remembers active projects/topics, user research interests, reading lists, draft notes, and discovered consensus/contradiction patterns across sessions.
- Tools:
  - Local document scanner & reader (reading papers and notes in the project directory).
  - Web/academic search (on user demand, finding related papers or topic-specific resources).
  - Summarizer & extractor (extracting arguments, methodology, conclusions, and novel contributions).
  - Consistency & verification analyzer (cross-referencing papers to detect contradictions or corroborations, and checking user reports for ungrounded claims).
  - Note & synthesis consolidator (merging user notes with paper findings, generating structured comparative reports).
- Catalog/UI: Collection of projects, papers, notes, and contradiction/corroboration matrices rendered as A2UI cards, comparison tables, and highlighted conclusion/contribution blocks.
- Image gen: Conceptual overview diagrams, graphical abstract representations, or visual topic covers.
- Sandbox: n/a (recomputation of paper metrics is not required).

Recommended for every project: memory, storage, tools, image generation, A2UI
Agent-specific / stretch (pick what fits): Vertex AI RAG Engine for local corpus indexing, Google Search tool for on-demand literature retrieval, A2UI cards for paper comparison tables and highlighted claim audits.
