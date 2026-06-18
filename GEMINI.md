# GEMINI.md

---
## ⚠️ MANDATORY WORKFLOW RULE (NON-NEGOTIABLE)

**After EVERY completed action** → immediately update `docx/Session_Progress_Tracker.md`:
- Move the completed task to the `✅ Done` section with a brief note.

**Before / when planning ANY new task** → immediately update `docx/Session_Progress_Tracker.md`:
- Add the new task to the `🚀 Next Steps / Pending Tasks` section.

> This rule applies to ALL actions, no matter how small. No exceptions.
> File: [Session_Progress_Tracker.md](file:///Users/lap14489/Documents/claw-a-thon-demo-agent-longht/docx/Session_Progress_Tracker.md)

---

- Goal (incl. success criteria):
  - Build the **Acme Knowledge Platform (Data Platform Copilot)** for the GreenNode Claw-a-thon 2026 hackathon.
  - Submission deadline: **June 17, 2026 at 12:00 PM (GMT+7)**.
  - Deliverables: GitHub repo (public), 2-3 min demo video, 100-200 word use case description.
  - Success metrics: Data discovery < 1 min (vs. 30 min manually), automated impact analysis, centralized knowledge graph.

- Constraints/Assumptions:
  - Communication language: Vietnamese (tiếng Việt).
  - Technical writings/code/docs: English (tiếng Anh).
  - Role perspective: Senior Data Quality Engineer & Senior Data Engineer.
  - OS: macOS (Mac).
  - AI Tooling: Gemini & Antigravity (Agy) IDE/extension.
  - Workflow Rule: Always update `docx/Session_Progress_Tracker.md` immediately after completing any action. Whenever a plan introduces new tasks or upcoming steps, they must also be logged into `docx/Session_Progress_Tracker.md`.
  - Model: `minimax/minimax-m2.5` via GreenNode MaaS (`https://maas-llm-aiplatform-hcm.api.vngcloud.vn/v1`).
  - Platform: GreenNode AgentBase Runtime (Docker-based).
  - Git Branch: `feat/integrate-agentbase-skills`.

- Key decisions:
  - **Architecture**: Metadata-First + Knowledge Graph philosophy.
  - **MVP scope**: Data Platform domain only (Hive, Spark, Airflow, Confluence).
  - **Data sources**: Confluence, Jira, GitLab, Data Catalog (Hive/Presto).
  - **Backend stack**: Ingestion → AI Extraction (MiniMax-M2.5) → Graph DB (Neo4j/Nebula) + Vector DB (Qdrant) → Agentic RAG.
  - **SDK**: `greennode-agentbase` SDK, entry point at `src/main.py`, port 8080.
  - Security: `.greennode.json` (IAM), `.env` (MaaS API key), `.gitignore` & `.dockerignore` hardened.

- State:
  - Done:
    - Phase 0: Workspace init, docs.
    - Phase 1: Security hardening, MaaS API configured.
    - Phase 2: Strategic plan (`Acme_Knowledge_Platform_Plan.md`) + Progress tracker (`Session_Progress_Tracker.md`).
    - **P0**: `copilot.py` implemented with real `AsyncOpenAI` LLM call + tool-calling loop (verified MiniMax-M2.5 responds with tools).
    - **P1-A**: Upgraded `schema.py` (tier, tags, owner dict) and `engine.py` (recursive BFS lineage tracking).
    - **P1-B**: Building Ingestion Pipeline. DataHub extracted 856 datasets.
    - Implemented **Just-In-Time (JIT) Verification** (`get_entity_details`) with Fallback `_warning` mechanism for DataHub.
    - **P1-C**: Multi-Agent GitLab Extraction. Cloned 6 Git repositories. Spawned 6 AI subagents (`CodeAnalyzer`) in parallel to read code and generate rich `architecture.json` and `file_descriptions.json`. Merged outputs.
    - Implemented **Just-In-Time (JIT) Verification** (`read_confluence_page`) for Confluence.
    - Extracted Confluence Markdown into **OpenMetadata Schema JSON** using RAGFlow Document Chunking strategy (`extract_confluence_knowledge.py`).
    - **P1-D**: Re-architected Confluence Cache. Converted flat Markdown to **Deep Semantic JSON Tree** organized by `parent_id` (`confluence_tree_extractor.py`).
    - **P1-E**: Built Jira JIT Verification module (`jira_extractor.py`) pulling Epics and Tickets based on tight JQL criteria. Mapped schemas properly and seeded mock data.
    - **P1-F**: Aligned all Core Schemas (`align_schemas.py`) so DataHub, GitLab, Confluence, and Jira data structure matches the exact Graph OpenMetadata spec.
  - Now:
    - Freezing code state for machine reset. P1 (Ingestion Pipeline) is 100% complete and validated.
  - Next:
    - Tomorrow: Start **Phase 2 (Knowledge Graph Enrichment)**.
    - Implement Typed Edges in `engine.py` (LOADED_BY, DEPENDS_ON).
    - Upgrade `discovery.py` to recursively parse the newly structured JSON trees and integrate hybrid metadata filtering.

- Open questions (UNCONFIRMED if needed):
  - DataHub auth mechanism (SSO vs Basic? Best to use session cookie).
  - GitLab and Confluence URLs and tokens.

- Working set (files/ids/commands):
  - [GEMINI.md](file:///Users/lap14489/Documents/claw-a-thon-demo-agent-longht/GEMINI.md)
  - [Session_Progress_Tracker.md](file:///Users/lap14489/Documents/claw-a-thon-demo-agent-longht/docx/Session_Progress_Tracker.md)
  - [Acme_Knowledge_Platform_Plan.md](file:///Users/lap14489/Documents/claw-a-thon-demo-agent-longht/docx/Acme_Knowledge_Platform_Plan.md)
  - [Claw-a-thon_User_Guide.md](file:///Users/lap14489/Documents/claw-a-thon-demo-agent-longht/docx/Claw-a-thon_User_Guide.md)
  - [AgentBase_User_Guide.md](file:///Users/lap14489/Documents/claw-a-thon-demo-agent-longht/docx/AgentBase_User_Guide.md)
  - [src/main.py](file:///Users/lap14489/Documents/claw-a-thon-demo-agent-longht/src/main.py)
  - [src/core/schema.py](file:///Users/lap14489/Documents/claw-a-thon-demo-agent-longht/src/core/schema.py)
  - [src/core/engine.py](file:///Users/lap14489/Documents/claw-a-thon-demo-agent-longht/src/core/engine.py)
  - [src/tools/discovery.py](file:///Users/lap14489/Documents/claw-a-thon-demo-agent-longht/src/tools/discovery.py)
  - [src/tools/impact.py](file:///Users/lap14489/Documents/claw-a-thon-demo-agent-longht/src/tools/impact.py)
  - [src/agents/copilot.py](file:///Users/lap14489/Documents/claw-a-thon-demo-agent-longht/src/agents/copilot.py)
  - [src/data_platform/datasets.json](file:///Users/lap14489/Documents/claw-a-thon-demo-agent-longht/src/data_platform/datasets.json)
  - [src/data_platform/pipelines.json](file:///Users/lap14489/Documents/claw-a-thon-demo-agent-longht/src/data_platform/pipelines.json)
