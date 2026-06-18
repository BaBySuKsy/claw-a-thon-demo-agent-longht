# Acme Knowledge Platform: Session Progress Tracker

> ⚠️ **MANDATORY RULE**: This file MUST be updated after EVERY completed action and EVERY new planned task. No exceptions.

This document tracks the end-to-end progress of the **Acme Knowledge Platform (Data Platform Copilot)** project for the Claw-a-thon 2026 hackathon.

---

## 1. Executive Summary

We are building an **Enterprise Knowledge Graph & AI Assistant** that standardizes metadata and tri-knowledge of Acme. The MVP focuses on the **Data Platform domain** to demonstrate high-value features like Data Discovery and Impact Analysis.

**Competition Category**: Primary → **Data Analysis** | Secondary → **Agentic Assistant**
**Current Branch**: `feat/integrate-agentbase-skills`
**Environment**: GreenNode AI Platform (MaaS) connected via `minimax/minimax-m2.5`.
**Submission Deadline**: June 17, 2026 at 12:00 PM (GMT+7)

---

## 2. Completed Milestones (✅ Done)

### Phase 0: Workspace & Documentation Initialization
- [x] Renamed project to `claw-a-thon-demo-agent-longht`.
- [x] Created and connected public GitHub repository.
- [x] Converted `[Official] Claw-a-thon User Guide.docx` to `docx/Claw-a-thon_User_Guide.md` (Technical English, macOS/Gemini/Agy focus).
- [x] Extracted official `AgentBase User Guide` from web to `docx/AgentBase_User_Guide.md`.

### Phase 1: Security & Cloud Configuration
- [x] Created feature branch `feat/integrate-agentbase-skills`.
- [x] Integrated `greennode-agentbase-skills` into the project root.
- [x] Configured **IAM Credentials** (`.greennode.json`) and verified Cloud connection.
- [x] Configured **MaaS API Key** and Environment variables in `.env`.
- [x] Selected and set **Default Model**: `minimax/minimax-m2.5`.
- [x] Implemented Security Hardening (`.gitignore`, `.dockerignore`).

### Phase 2: Strategic Planning
- [x] Designed the long-term vision and MVP scope: `docx/Acme_Knowledge_Platform_Plan.md`.
- [x] Defined the **Metadata-First** and **Knowledge Graph** architectural philosophy.

### Phase 3: MVP Scaffolding (Code Implementation)
- [x] Implemented **Core Schema** (`src/core/schema.py`): Defined Domain, Team, Dataset, Pipeline entities.
- [x] Implemented **Knowledge Engine** (`src/core/engine.py`): In-memory graph traversal and lineage logic (1-hop only, needs upgrade).
- [x] Populated **MVP Metadata** (`src/data_platform/`): Initial 2 datasets and 1 pipeline (seed only, needs expansion to 15+).
- [x] Developed **Specialized Tools**:
    - `src/tools/discovery.py`: Metadata & Ownership discovery.
    - `src/tools/impact.py`: Downstream Impact Analysis logic.
- [x] Designed **AI Intelligence**:
    - `src/agents/prompts/`: Modular system prompts (system.py, tool.py, extraction.py).
    - `src/agents/copilot.py`: Agent scaffold — **NOTE: LLM call not yet implemented (stub only)**.
- [x] Created **Application Entrypoint**: `src/main.py` using `greennode-agentbase` SDK.
- [x] **Local Testing & Validation**: Successfully ran `src/main.py` locally, server starts on port 8080.
- [x] **Cloud Preflight Check**: Verified IAM token generation and MaaS API connectivity. All systems GO.

### Session 2026-06-11: Strategy & Analysis
- [x] **Full documentation review**: Read all 4 `.md` files in `docx/` to re-establish project context.
- [x] **Competition category analysis**: Identified 3 official Claw-a-thon themes. Project fits **Data Analysis** (primary) + **Agentic Assistant** (secondary).
- [x] **Mandatory workflow rule saved**: Rule enforced in `GEMINI.md` and this tracker.
- [x] **Schema pattern review (industry standards)**: Reviewed OpenMetadata, Backstage, GraphRAG, RAGFlow, LlamaIndex, dbt patterns against current codebase. Identified critical gap: `copilot.py` does NOT actually call LLM. Full review in `schema_pattern_review.md`.
- [x] **P0 COMPLETED ✅**: Refactored `copilot.py` with real `AsyncOpenAI` LLM call + tool-calling loop (MAX 5 iterations). Added `openai>=1.30.0` to requirements. Upgraded `prompts/tool.py` with 3 OpenAI function-calling schemas. Updated `main.py` response envelope. **Verified**: Agent called `search_metadata` tool automatically, synthesized real Markdown answer via MiniMax-M2.5 in 2 iterations.
- [x] **Critical gaps identified**:
    - 🔴 `copilot.py` is a stub — no real LLM call implemented.
    - 🟡 `engine.py` lineage is 1-hop only — needs recursive BFS.
    - 🟡 `schema.py` is too basic — missing `tier`, `tags`, `status`, structured `owner`.
    - 🟡 `datasets.json` has only 2 records — insufficient for meaningful demo.
- [x] **Implementation roadmap finalized**: P0 → P1 → P2 → P3 → P4, logged in both tracker and plan files.
- [x] Analyzed `etl-lib` codebase (Spark/Scala ETL library), generated `architecture.json` and `file_descriptions.json` to understand the data platform utilities.

---

## 3. Implementation Roadmap (🚀 In Progress)

> **Rule**: Mark `[x]` immediately when a task is done, then update Section 4 (Current Status Summary).

### 🔴 P0 — CRITICAL: Agent Core (Do First — Without This, Nothing Works)

| Task | File | Detail | Status |
|------|------|--------|--------|
| Refactor `copilot.py` | `src/agents/copilot.py` | Replace stub with real `AsyncOpenAI` client call to `minimax/minimax-m2.5` via GreenNode MaaS. Implement tool-calling loop: parse LLM response → detect tool intent → invoke correct tool → return synthesized answer. | `[x]` |

**Acceptance criteria**: ✅ PASSED — Agent called `search_metadata` automatically, returned real Markdown answer synthesized by MiniMax-M2.5 in 2 LLM iterations.

---

### 🟡 P1 — Foundation: Schema, Data & Ingestion Pipeline
**Decision**: Instead of hardcoding fake data, build a real ingestion pipeline from 3 actual Acme sources: **DataHub** (table schemas + lineage), **GitLab** (DAG definitions), **Confluence** (table docs). This makes the demo significantly more convincing and the project architecturally sound.

#### P1-A: Code Fixes
| Task | File | Detail | Status |
|------|------|--------|--------|
| Upgrade `schema.py` | `src/core/schema.py` | Add `tier`, `tags`, `status`, `owner: Dict`. Adopt OpenMetadata pattern. | `[x]` |
| Fix `engine.py` lineage | `src/core/engine.py` | Recursive BFS traversal — current 1-hop is insufficient for Impact Analysis. | `[x]` |

#### P1-B: Ingestion Pipeline (`src/ingestion/`)
| Task | File | Detail | Status |
|------|------|--------|--------|
| **DataHub client** | `src/ingestion/datahub_client.py` | REST/GraphQL API. Fetched 856 HDFS datasets (filtered test/deprecated). Implemented JIT Verification (`fetch_dataset_by_urn`). | `[x]` |
| **GitLab client** | `src/ingestion/gitlab_client.py` | PAT token (user to provide). Extract DAG `.py` files → dag_id, schedule, inputs/outputs. | `[x]` |
| **Confluence client** | `src/ingestion/confluence_client.py` | Token (user to provide). Crawl DP space → extract table descriptions, owner, ETL notes. | `[ ]` |
| **Extractor + normalizer** | `src/ingestion/extractor.py` | Orchestrate clients → normalize → output `datasets.json` + `pipelines.json` in OpenMetadata format. | `[ ]` |

#### P1-C: JIT Verification (Real-time Fallback Logic)
| Task | File | Detail | Status |
|------|------|--------|--------|
| **DataHub JIT** | `src/tools/discovery.py` | Real-time fetch schema. Added `_warning` fallback if API fails. | `[x]` |
| **GitLab JIT** | `src/tools/discovery.py` | Real-time fetch DAG code. Add `_warning` fallback if API fails. | `[x]` |
| **GitLab Analysis** | `temp_analysis/` | Analyzed `fund-mapping-etl`, `airflow-onprem`, and `credit-curated-etl` repos, generated architecture and file descriptions. | `[x]` |
| **Confluence JIT**| `src/tools/discovery.py` | Real-time fetch latest Docs. Add `_warning` fallback if API fails. | `[x]` |
| **Jira JIT** | `src/ingestion/jira_extractor.py` | Real-time fetch Ticket status. Grouped by Epic (`>= 2025-01-01`) and Tickets (`>= 2026-01-01`) for PCDCM & PDPDW. Fallback to `other_epic.json`. | `[x]` |
| Update `discovery.py` loader | `src/tools/discovery.py` | Handle `owner: Dict`, `tier`, `tags` in new schema. | `[ ]` |

#### P1-C: Output Validation
| Task | File | Detail | Status |
|------|------|--------|--------|
| Validate extracted data | `src/data_platform/` | `datasets.json` 15+ records, `pipelines.json` 8+. Agent answers with real schema from DataHub. | `[ ]` |

**Acceptance criteria**: Agent answers "What is `user_dim`?" with real schema extracted from DataHub, not hardcoded data.

---

### 🟠 P2 — Knowledge Graph Enrichment + Search Foundation
**⚠️ Note**: Document Chunking và Hybrid Search được kéo lên P2 vì chúng block demo trực tiếp — nếu search không ra đúng entity thì demo fail.

| Task | File | Detail | Status |
|------|------|--------|--------|
| Add Typed Relations | `src/core/engine.py` | Add `add_relationship(source, target, type)` method. Edge types: `LOADED_BY`, `OWNED_BY`, `DEPENDS_ON`, `PRODUCES`, `CONSUMES`, `PART_OF`. Store in `self.relationships` list. Add `find_by_relation(entity_id, relation_type)` query method. | `[ ]` |
| Add Tier Awareness to Tools | `src/tools/impact.py` | Annotate each impacted entity with `tier`. Sort results: Tier1 first. Add `critical_tier1_count` + warning flag if any Tier1 entity is in impact set. | `[ ]` |
| Add Multi-Owner to Discovery | `src/tools/discovery.py` | `get_ownership()` must return full structured owner dict `{team, slack, tech_lead}` instead of raw string. | `[ ]` |
| Add `teams.json` + `domains.json` seed | `src/data_platform/` | Teams: Data Platform, Infrastructure, Analytics. Domains: data-platform, payments, fraud. Required for onboarding scenario. | `[ ]` |
| **[Semantic Recursive Tree]** Confluence text → structured entity JSON | `src/ingestion/confluence_tree_extractor.py` | Replaced flat Markdown with Deep JSON Tree. Extracted Sections, Tables, Links recursively for all Top-Level Root pages. **Required to feed highly structured data into graph.** | `[x]` |
| **[Hybrid Search — RAGFlow pattern]** Exact + fuzzy ranking in `search_metadata` | `src/tools/discovery.py` | Priority order: (1) exact name match → (2) partial name match → (3) fuzzy description match. Prevents demo failure when user types "bảng user" instead of exact "user_dim". | `[ ]` |

---

### 🔵 P3 — Intelligence Upgrade
**Goal**: Make the agent smarter in routing and retrieval.

| Task | File | Detail | Status |
|------|------|--------|--------|
| Upgrade `search_metadata` with pre-filtering | `src/tools/discovery.py` | Add pre-filtering by `domain`, `tier`, `entity_type` before search (LlamaIndex metadata filtering pattern). | `[ ]` |
| **[Two-Level Retrieval — simplified GraphRAG]** Add `_route_query()` intent classifier | `src/agents/copilot.py` | Classify intent then route: **SPECIFIC** query (contains entity name/table/team) → direct graph lookup via `search_metadata` + tools. **BROAD** query (no specific entity) → scan domain/team summary. **IMPACT** query → `analyze_impact`. **ONBOARDING** query → curated entity list for the team. | `[ ]` |
| Add exact-match prioritization to search | `src/tools/discovery.py` | Exact name match ranks above fuzzy description match (part of Hybrid Search — finalize here if not done in P2). | `[ ]` |
| Upgrade system prompt with Tier-awareness & onboarding flow | `src/agents/prompts/system.py` | Add Tier-awareness: "This change affects 3 Tier1 tables — critical!". Add onboarding flow template. | `[ ]` |

---

### 🟢 P4 — Deployment & Submission

| Task | File | Detail | Status |
|------|------|--------|--------|
| Harden `Dockerfile` | `Dockerfile` | Review and optimize: multi-stage build, correct WORKDIR, expose port 8080, non-root user. | `[ ]` |
| Dockerize & Local Test | — | `docker build -t acme-copilot .` then `docker run -p 8080:8080 acme-copilot`. Verify health check and chat endpoint. | `[ ]` |
| Run AgentBase Wizard | `agentbase-skills/` | Run `/agentbase-wizard` to finalize identity registration on GreenNode AgentBase Runtime. | `[ ]` |
| Deploy to AgentBase | — | Push Docker image to GreenNode Container Registry. Deploy via AgentBase Runtime. Set endpoint to public mode. | `[ ]` |
| End-to-End Demo Test | — | Validate all 3 demo scenarios on deployed agent: (1) Data Discovery, (2) Smart Onboarding, (3) Impact Analysis. | `[ ]` |
| Submission Prep | — | Write 100–200 word use case description. Record 2–3 min demo video. Verify GitHub repo is public. Submit at https://greennode.ai/events/greennode-claw-a-thon | `[ ]` |

---

### Session 2026-06-12: Full Codebase Review (Senior AI/Data Engineer)
- [x] **Full code review completed** — Reviewed all source files: `schema.py`, `engine.py`, `discovery.py`, `impact.py`, `copilot.py`, `main.py`, `datasets.json`, `pipelines.json`, `confluence_knowledge.json`.
- [x] **Critical bugs identified and documented** (see Section 4-BUG below).
- [x] **P0-BUG FIX** — Fix schema mismatch in `load_data_platform_engine()`: added `_normalize_dataset()`, `_normalize_pipeline()`, `_normalize_article()` to `discovery.py`. ✅
- [x] **P0-BUG FIX** — Fix `asyncio.run()` inside async context: `read_confluence_page()` is now `async def` + uses `await`. ✅
- [x] **P1-BUG FIX** — `KnowledgeEngine` is now a module-level singleton via `get_engine()`. ✅
- [x] **P1-BUG FIX** — `read_gitlab_file()` runs in `run_in_executor()` thread pool from `copilot.py` to avoid blocking event loop. ✅
- [x] **P1-DATA** — Enriched 14 key datasets: warehouse (identity_mart, bank_code_mapping, last_n_action_log, last_n_event_log, qrpay_user, qrpay_user_translog), Credit (loan_core_account/order/bill/statement/user), Partner (merchant_info/category/app_info). ✅
- [x] **P1-DATA** — `credit-curated-etl` pipeline: lineage.upstream = 5 Credit source tables, tier → Tier1. ✅
- [x] **P2-SEARCH** — `search_metadata()` capped at 15 results, sorted Tier1→Tier2→Tier3. ✅
- [x] **P2-SCHEMA** — `KnowledgeArticle` dataclass added to `schema.py`. ✅
- [x] **P2-GRAPH** — Cross-entity BFS in `engine.py`: Dataset↔Pipeline traversal via reverse-index. `add_relationship()`/`find_by_relation()` helpers added. ✅
- [x] **P2-SEARCH** — Confluence `knowledge_knowledge.json` loaded into engine + searchable via `search_metadata()`. ✅

### Session 2026-06-13: P3 Intelligence Upgrades
- [x] **P3.1** — Added `_route_query()` intent classifier to `copilot.py`. Regex patterns for IMPACT/ONBOARDING/SPECIFIC/BROAD in both Vietnamese and English. Priority order: IMPACT > ONBOARDING > SPECIFIC > BROAD. Routing hint injected as system message before LLM call. 4/4 test cases pass. ✅
- [x] **P3.2** — Upgraded `src/agents/prompts/system.py` with: Tier-awareness (Tier1=P0 critical, Tier2=P1), tool usage guidelines, Tier1 warning instructions, onboarding flow template, response standards. ✅
- [x] **P3.3** — Upgraded `src/tools/impact.py` to use `get_engine()` singleton (not `load_data_platform_engine()` per-call). Added `critical_tier1_count`, `warning` fields. Results sorted Tier1 first. Verified: `bank_code_mapping` → impact_count=3, critical_tier1_count=1, warning fires. ✅

### Session 2026-06-13 (PM): Quality Upgrades + Incident Triage + Redeploy v5
> ⚠️ Note: between the AM session and this one, the codebase had already grown well beyond what earlier tracker sections recorded — the live agent was running **12 tools** (not 3): search_metadata, get_ownership, get_entity_details, analyze_impact, get_related_context, read_gitlab_file, read_confluence_page, search_jira_tickets, get_recent_commits, get_data_freshness, get_schema, get_platform_alerts — plus BM25 Vietnamese search, multi-turn session memory, confidence scoring, cross-source index, and a proactive-alert background loop, and was **deployed live** on AgentBase (runtime `acme-dp-agent`). This session syncs the docs to reality and adds the upgrades below.

- [x] **Full state reconciliation** — Verified live endpoint (health 200) + 4 demo scenarios all passing before changes. Mapped actual codebase (8 tool files, 12 tools, live ingestion clients).
- [x] **P1.1 Onboarding grounding** — Added `src/data_platform/domains.json` (5 business domains) + `teams.json` (data-engineering) seed. Loaded into engine via `Domain`/`Team` dataclasses. New tool **`get_platform_overview(domain?)`** returns domains + Tier1 tables + key pipelines + must-read docs in ONE call. Onboarding now does 1 call instead of 4 `search_metadata`. ✅
- [x] **P1.2 Pipeline lineage enrichment** — Added 9 curated lending fact/dim datasets (grounded in `credit-curated-etl` testsuites) and set `credit-curated-etl.downstream`. Impact analysis on `loan_core_statement` now returns a **10-entity multi-hop chain** (source → Tier1 pipeline → 9 marts). ✅
- [x] **P1.3 Fuzzy search fallback** — `search_metadata()` adds `difflib` fuzzy matching (stdlib) when BM25 returns < 3 hits. Verified: typo `credit_core_statment` → resolves `loan_core_statement`. ✅
- [x] **P1.4 Confidence tuning** — `_compute_confidence()` credits `get_platform_overview` (+0.40), breadth, `get_platform_alerts`, `diagnose_entity`. Onboarding now ≥ 0.7. ✅
- [x] **P2 Incident Triage (WOW feature)** — New `src/tools/triage.py` → **`diagnose_entity(entity_id)`**: correlates freshness + recent pipeline commits + open Jira incidents + downstream Tier1 impact → findings + likely_root_cause + recommended_actions + severity. New `INCIDENT` intent (VI/EN). Reuses existing verified tools (no logic rewrite). ✅
- [x] **P3 Local verification** — Routing 6/6; onboarding/incident/impact/discovery/alerts/fuzzy all pass via real MiniMax-M2.5; no regression; py_compile OK. ✅
- [x] **P5 Redeploy v5** — Built `acme-dp-agent:v20260613e` (linux/amd64), pushed to CR, `runtime.sh update ... --from-cr`. Runtime version 5 ACTIVE, health 200. **Live verified**: onboarding→get_platform_overview (0.7), incident→diagnose_entity (1.0, live DataHub/GitLab/Jira), impact→10-entity multi-hop. ✅
- [ ] **P4 GitHub push (DEFERRED to submission)** — Local commits ready. **Sensitive-data guard**: gitignored `cache/`, `confluence_knowledge.json`, `confluence_index.json`, `file_descriptions.json` (contain internal IPs, DB users, employee emails, internal hostnames). Source internal hostnames to be env-only before push. NOT pushed yet — only needed for final submission.
- [ ] **P6 Submission deliverables** — README + use-case (100-200w) + demo video script. Pending.

### Session 2026-06-13 (Evening): Win-grade hardening + UI + Redeploy v6→v7
**Goal**: make the agent "flawless to win first place" — fix demo-breaking/trust bugs found in a full review, add wow features, build a professional UI. Reviewed via 3 review agents + `/code-review` skill.

**Reliability & trust fixes (deployed in v6 `v20260613f`):**
- [x] **Stopped JIT tier/owner overwrite** (`discovery._merge_fresh_into_existing`) — live DataHub no longer demotes curated Tier1 tables; removed request-time JSON write-back. ✅
- [x] **Bounded `diagnose_entity`** with `asyncio.wait_for(18s)` — was hanging >100s; returns partial on timeout. ✅
- [x] **Added `timeout=10` to all live HTTP** (datahub/gitlab/confluence clients, read_gitlab_file); cached GitLab project-id; `get_recent_commits` uses default branch (was `master`). ✅
- [x] **Redaction guard** (`src/tools/redact.py`) — scrubs internal IPs (private ranges only)/emails/DB-creds from tool output; applied in `copilot._dispatch_tool`; + system-prompt security rule. ✅
- [x] **Short-name→URN resolution** (`resolve_entity_id`, exact-match preferred) wired into analyze_impact/get_ownership/get_data_freshness; fixed stale example IDs. ✅
- [x] **Polish**: MAX_TOOL_ITERATIONS 6 + graceful final-synthesis fallback; VN/EN language consistency (triage returns structured signals, LLM renders in user's language); no tool-syntax leak. ✅

**New "wow" features (v6):**
- [x] **Mermaid lineage/impact visualization** — `src/tools/viz.py` + `engine.get_lineage_graph()`; `analyze_impact` returns a `mermaid` field; system prompt embeds it → blast radius renders as a tier-colored diagram. ✅
- [x] **Citation + Confidence footer** — deterministic footer (confidence bar + data sources from tools_called) appended in `copilot._build_response`. ✅
- [x] **Daily Health Briefing** — `monitor.get_health_briefing()` (tool #15) + BRIEFING intent; proactive digest of stale Tier1 / open incidents / recent risky commits. ✅

**Code review (`/code-review` + agents):** fixed redact IPv4 false-positive on version strings, fallback missing `tools=`, footer-strip over-strip (anchored to "Độ tin cậy"), viz label escape/`PROD` fallback, mermaid load retry, proxy strips unused tool `result`.

**Data integrity fix (v7 `v20260613g`):** discovered the local seed had been corrupted by the OLD JIT write-back (tier + lineage of Credit core tables, plus stray top-level `upstream/downstream` keys). Restored clean Tier1 + canonical `lineage` for the 5 Credit core tables (`account→order→bill→statement→credit-curated-etl→9 marts`). Impact graph now a clean 11-node diagram. **Redeployed v7, live-verified clean** (11 nodes, no messy labels, statement Tier1). ✅

**Web UI (`ui/`):**
- [x] **v1** — Starlette proxy (`ui/server.py`, serves SPA + forwards to agent, avoids CORS) + chat SPA. ✅
- [x] **v2 — Claude-Desktop redesign** (`ui/index.html`) with **real Acme logo** (inline SVG) + brand colors (#0033C9 blue / #00CF6A green), warm paper theme: left sidebar (new chat, quick-suggestions, **localStorage chat history**, live status), full-width assistant messages, refined composer, markdown+table render, **Mermaid diagram render on clean canvas**, tool-trace panel, confidence bar + source chips, mobile-responsive. Verified via headless-Chrome screenshots. ✅
- Run: `venv/bin/python ui/server.py` → http://localhost:3000 (proxies to live agent; or `AGENT_ENDPOINT=http://localhost:8080` for local). Deps starlette+uvicorn+httpx (in venv; add to requirements.txt before clone/deploy elsewhere).

### Session 2026-06-14/15: "Win-grade" differentiation — 3 standout features + redeploy v12
**Goal**: the existing 15 tools were table-stakes data-catalog features (discovery/ownership/impact/freshness — same as OpenMetadata/Atlan). User wanted genuine "wow" + fixed the "agent only shows cached data, not live" problem. Researched hottest 2026 agent repos (Graphiti = temporal KG; autonomous action-taking agents) and committed to 3 features. **Built, verified live end-to-end, and DEPLOYED to prod (runtime version 12, ACTIVE).**

**Root issue confirmed in code review**: engine loads ~800 datasets from static JSON once at boot and never reloads; the 3 most-used tools (`search_metadata`, `analyze_impact`, `get_ownership`) never hit a live API; live tools fall back to cache with only a `_warning` field; `ui/server.py` stripped tool results so the user could never tell live from stale.

- [x] **F1 — Live data + Trust Layer.** `search_metadata` now LIVE-verifies freshness of its top-3 dataset hits (bounded `_SEARCH_VERIFY_TIMEOUT=6s`, best-effort, attaches `_freshness`). New `_compute_freshness()`/`_classify_result()` in `copilot.py` aggregate per-tool provenance into a top-level `freshness` envelope `{level: live/partial/stale/cached, label, live_sources, fallback_sources, verified_at}`, surfaced through `main.py`. UI (`ui/index.html`) renders a 🟢/🟡/🔴 trust badge with verified-at time + source tooltip. ✅
- [x] **F2 — Autonomous RCA Investigator.** Upgraded `diagnose_entity` from single-pass correlation into a multi-phase autonomous investigation: (1) local impact/context, (2) live fan-out incl. **upstream freshness probe**, (3) **propagation analysis** — finds the real UPSTREAM culprit vs the symptom, (4) **smoking-gun deep-dive** — new `get_commit_diff()` (`git_history.py`) fetches the suspect commit's diff, (5) **remediation drafts** — deterministic Jira ticket (P0 if Tier1) + Slack message (suggested, not sent), (6) `confidence` score. System prompt renders verdict→root-cause(upstream)→smoking-gun→blast-radius→runbook→copyable drafts. ✅
- [x] **F3 — Temporal time-travel graph (Graphiti-inspired).** New `src/tools/temporal.py`: append-only bi-temporal observation log (`record_observation`, hooked into `get_data_freshness` + `get_schema`) + `get_changes_since(scope?, hours?)` tool → schema drift (live DataHub vs seed = "past snapshot"; flags potentially-breaking column changes), newly-stale Tier1, recent commits, logged observations. New `CHANGES` intent (VI/EN) + routing hint + tool def. `history/` gitignored. ✅
- [x] **Verification**: all 9 changed files `py_compile` OK; logic smoke tests pass (freshness classification 6 cases, intent routing incl. CHANGES, schema-diff, observation log, triage drafts/propagation). Tool count **15 → 16** (added `get_changes_since`); def/dispatch/source consistency verified; engine loads 882 entities. ✅
- [ ] **F4 — Action-taking / write-back (DEFERRED by user, planned future).** Close the agentic loop by actually SENDING the F2 drafts: create the Jira ticket (Jira REST), post the Slack alert, or open a GitLab MR to fix a DAG — behind a human-confirm step. F2 already produces the draft payloads, so F4 is "wire the send + confirmation". This is the strongest "Agentic Assistant" category point.
- [x] **Redeploy — DONE (2026-06-15): runtime version 12 LIVE & ACTIVE**, image `v20260615a`. All 3 features verified on prod (search+badge, diagnose_entity+jira_draft, get_changes_since).
  - **Deploy method that worked**: `runtime.sh update <id> --image <flat-image> --flavor runtime-s2-general-4x8 --env-file .env --from-cr` (NOT `greennode deploy update`). `--from-cr` uses IAM only — no registry creds needed.
  - **Critical fix**: build with `--provenance=false --sbom=false` (flat single manifest). Default buildx makes OCI-index+attestation → platform pull slow → fails rollout health-probe → versions 10 & 11 stuck **ERROR** (pod ran but never marked healthy). Flat image (version 12) → ACTIVE immediately. Also delayed startup health-check 45s (`main.py:_alert_loop`).
  - **Full procedure + every error/fix → `docx/Deploy_Runbook.md`**.
- [ ] **PROD limitation (PUBLIC mode)**: runtime can't resolve `datahub.acme.vn` / reach gitlab/jira (DNS) → live features fall back to cache on prod (Trust Layer honestly shows "stale"). For true live data on prod, deploy **VPC mode** (needs vpcId + subnetId). Local (with VPN) shows everything live/green.

---

### Session 2026-06-15 (PM): Speed + accuracy optimization + REAL STREAMING — redeploy v13
**Goal** (per user, credit no-object → optimize reasoning/search speed + answer accuracy): land safe, high-value agent upgrades 48h before deadline without re-architecting the working live agent. User explicitly approved all four + autonomous execution.

- [x] **Parallelize multi-tool-call** (`copilot.py` chat loop) — when the LLM requests several tools in one turn, dispatch concurrently via `asyncio.gather` instead of a sequential for-loop. Latency = slowest single tool, not the sum. Order preserved for `tool_call_id` alignment. Verified: impact query → `analyze_impact`+`get_ownership` run together, correct answer. ✅
- [x] **Multi-query retrieval with RRF** (`discovery.py:search_metadata_multi`) — full query + per-significant-token sub-queries, fused via Reciprocal Rank Fusion (k=60). Wired into `_run_search_metadata`. All in-memory → **zero added latency**. Boosts recall on multi-concept/paraphrased queries (e.g. "ai sở hữu bảng thanh toán qrpay" surfaces the owning team). `resolve_entity_id` unchanged (still single search). Verified: no regression on exact names/typos; better recall on multi-concept. ✅
- [x] **Instant precision rerank** — folded into `search_metadata_multi`: exact short-name match → strong boost (+0.5, dominates RRF), substring match → +0.05. **No LLM round-trip** — chose this over an LLM-reranker to protect speed (the synthesis step already reasons over top-15; an extra rerank call would add ~2-3s/query for marginal gain). Verified: "qrpay_user thuộc về ai" → `qrpay_user` #1; "loan_core_account schema" → `loan_core_account` #1. ✅
- [x] **Real streaming (SSE)** — confirmed the `greennode_agentbase` SDK streams when the entrypoint returns an async generator (`StreamingResponse`, `text/event-stream`). New `copilot.chat_stream()` async generator yields `status` (routing/tool/tools_done — shows the agent "thinking" + tool calls **live**), `token` (answer streamed live), and `done` (full envelope: tools/confidence/freshness). `main.py` gates it behind `payload.get("stream")` → **default non-streaming path is byte-for-byte unchanged** (backward-compatible). UI: added `/api/chat/stream` proxy route (`ui/server.py`) + rewrote `send()` in `ui/index.html` (live tool-status line + token streaming; graceful fallback to `/api/chat`). **First token ~2.6s vs ~17s blocking.** Refactor: extracted `_ROUTING_HINTS`/`_build_messages`/`_persist_session` helpers shared by `chat()` + `chat_stream()`. ✅
- [x] **Verification** — `py_compile` all changed files; local end-to-end (parallelize, multi-query, rerank, streaming); **full regression 5/5 demo scenarios** (discovery/onboarding/impact/incident/changes) via non-streaming path; local Docker container test (health 200 + both paths). ✅
- [x] **Redeploy v13** — built flat image `v20260615b` (`--provenance=false --sbom=false`, linux/amd64), pushed to CR, `runtime.sh update --from-cr`. **Runtime version 13 ACTIVE**, rollout fast. **Live-verified on prod**: default path (`status:success`, search_metadata) + streaming path (5 status + 887 token + 1 done, tools `search_metadata→analyze_impact`, confidence 0.8). `freshness:stale` expected (PUBLIC mode). ✅
- [ ] **NOT visually screenshot-verified**: UI browser rendering of the streaming view (proxy SSE forwarding, event flow, and JS syntax ARE verified). Open `localhost:3000` to eyeball.
- [ ] **Submission deliverables still pending** (unchanged, MANDATORY): GitHub public + sanitize, demo video, use-case (<300w), thumbnail, team name + track.

### Session 2026-06-15 (night): Cross-team impact — redeploy v14
**Goal** (user chose to demo the "Knowledge OS" cross-team vision cheaply, without a DB / all-Confluence): show that changing a Data-Platform table breaks OTHER teams.

- [x] **Cross-team consumer seed** — `src/data_platform/cross_team.json`: 4 datasets owned by OTHER teams that consume DP lending marts — Risk `credit_risk_scorecard` (Tier1), Fraud `credit_fraud_signal` (Tier1), Collection `overdue_collection_list` (Tier1), Finance `credit_revenue_report` (Tier2). Loader loads them + wires edges into the mart `.downstream` IN MEMORY (`datasets.json` untouched, reversible). Engine 882→886 entities. ✅
- [x] **`analyze_impact` cross-team aggregation** (`impact.py`) — aggregates `affected_teams` (team + slack + entity_count + is_cross_team), `cross_team_count`, `target_owner_team`; warning now adds "🚨 CROSS-TEAM IMPACT: breaks N OTHER team(s) — coordinate BEFORE the change". ✅
- [x] **Verified** — local: `analyze_impact("loan_core_statement")` → impact 14, tier1 4, cross_team_count 4. Full chat() renders all 4 teams + Mermaid blast-radius shows cross-team nodes (no system-prompt change needed). ✅
- [x] **Redeploy v14** — image `v20260615c` (flat), `runtime.sh --from-cr`. **Runtime version 14 ACTIVE**, live-verified: cross_team_count=4 (risk-analytics/collection-ops/fraud-detection/finance-bi). ✅
- [ ] **VPC mode** (user requested) — needs `vpcId` + `subnetId` (PUBLIC→VPC switch enables live internal DataHub/GitLab/Jira on prod). See VPC section below / Deploy_Runbook.
- [ ] **Phase 2 roadmap** (DB + vector + all-Confluence + full cross-team) — documented for use-case/video, NOT built (deadline scope).

### Session 2026-06-16: Submission deliverables + UI delight + GitLab fix + REAL cross-team
**Goal**: finish all submission deliverables, polish UX, fix a live-tool bug, and replace the cross-team SEED with REAL Confluence-derived data. (Prod stays v14; these changes live on the `feat/integrate-agentbase-skills` branch + the clean `public-submission` branch — a v15 redeploy is optional since prod is PUBLIC/cache anyway. For the demo, run LOCAL via `run_local.sh`.)

**Submission deliverables (all DONE, ready to submit):**
- [x] **Repo sanitization for public** — `git rm --cached` internal data (confluence_knowledge/confluence_index/file_descriptions/temp_analysis/test_jira/.idea); env-only internal hostnames in 7 source files (blank `os.getenv` default) + added `DATAHUB_BASE_URL` to local `.env`; `.env.example` hostnames → placeholders; deep secret/PII scan = 0 hits. Built a clean **orphan branch `public-submission`** (no secret blobs in history — old commit 7d0854c is dirty, so we publish the orphan, NOT the feature branch). Verified: agent still loads + live after sanitize. ✅
- [x] **README.md** — senior-grade rewrite (15-section TOC, architecture diagram, KG model, retrieval pipeline, 16-tool table, API spec, demo, tech stack). Team **AITree**. ✅
- [x] **Use case** `docs/USE_CASE.md` — VN-only, ~293 words (under 300). ✅
- [x] **Demo video script** `docs/VIDEO_SCRIPT.md` + `docs/subtitles.srt` (timed VN subtitles) + recording/subtitle tool guide (QuickTime/CapCut/ffmpeg). ✅
- [x] **Thumbnail** `docs/thumbnail.png` (1200×630) — official Acme logo (blue #0033C9 / green #00CF6A), light theme; track line "Data Analysis + Agentic Assistant". ✅
- [x] **Public docs** `docs/DEMO_NOTES.md` (live-vs-cache for BOC, VN+EN) + `docs/ROADMAP.md` (Phase 2). ✅
- [ ] **PUBLISH** (user runs): `git push origin public-submission:main --force` → set repo Public → rotate PAT. Then record video + fill submission form (team AITree, track Data Analysis + Agentic Assistant).

**UX + reliability:**
- [x] **`run_local.sh`** — 1-command local agent+UI (for LIVE demo); auto-frees ports 8080/3000; reports 🟢/🔴 Trust Layer. ✅
- [x] **UI delight** (`ui/index.html`) — replaced typing dots with a **phase-morph "thinking pill"** that morphs icon+text per SSE stage (🧭 routing → 🔍/💥 tool → ✍️ synthesizing), shimmer text, `prefers-reduced-motion` aware. Frontend-only. ✅
- [x] **GitLab resolver fix** (`src/tools/git_history.py`) — `get_recent_commits`/`get_commit_diff`/`get_merge_requests` failed for projects outside 3 hardcoded prefixes (e.g. `credit-curated-etl` lives under `dataeng/`). Added `dataeng/` + a **GitLab search-API fallback** → resolves any namespace. Verified live: 20 real commits. ✅
- [x] **Source connectivity check** (local+VPN) — DataHub / GitLab / Confluence / Jira all 🟢 live. ✅

**Cross-team impact → REAL data (replaced seed):**
- [x] **`src/ingestion/confluence_org_extractor.py`** (new) — CQL-searches Confluence for data-platform term mentions (credit/qrpay/identity/merchant), groups by space (excludes data-spaces + personal `~`/handle spaces), maps team-space → dataset anchor. Regenerated `cross_team.json` with **10 real edges across 4 real teams**: **Product Experience (PD), Platform Engineering (ZTM), Finance Operations (FAPY), Growth Products (GP)** — replacing the 4 hand-seeded teams. Raw evidence gitignored (`cache/confluence_org/`); curated output = org-level names + public URNs (no PII). ✅
- [x] **Verified** — `analyze_impact("loan_core_statement")` → 4 real cross-teams; chat renders them. Docs (README/USE_CASE/VIDEO_SCRIPT/subtitles) updated to real teams. Engine ~892 entities. ✅
- Note (honest): cross-team links are **inferred from Confluence references** (which team-space mentions the data), not column-level lineage. Precise lineage = DataHub (Phase 2).

## 4. Current Status Summary

| Field | Value |
|-------|-------|
| **Current Phase** | **PROD LIVE = runtime v14 (`v20260615c`), ACTIVE.** Local `feat/...` branch is AHEAD of prod with: **REAL cross-team impact** (Confluence-derived: Product Experience/ZTM/Accounting/GE&RC), **GitLab namespace fix**, **UI delight pill**, and all **submission deliverables** (README/use-case/video/thumbnail/sanitized `public-submission` branch). v13 (on prod): parallel tools + multi-query RRF + rerank + SSE streaming. 16 tools. **For demo → run LOCAL (`run_local.sh`, VPN = 🟢 live).** |
| **Active Task** | Submission: user to `git push origin public-submission:main --force` + set repo Public + record video + fill form. Optional: redeploy prod **v15** to carry GitLab-fix + real cross-team + UI (prod is PUBLIC/cache so low urgency). |
| **Blocking Issues** | None. Prod PUBLIC mode → internal sources fall back to cache (Trust Layer honest). Local+VPN = full live. GitHub PAT in git remote should be rotated post-submission. |
| **Next Action** | Publish `public-submission` branch + record demo video (3 cases — see VIDEO_SCRIPT) + submit. |
| **Live Endpoint** | `https://endpoint-8b483005-086d-43c9-a704-101e13eb6a3d.agentbase-runtime.aiplatform.vngcloud.vn` (**runtime version 14, image `v20260615c`, ACTIVE**). Streaming via `{"message":...,"stream":true}` → SSE. Deploy via `runtime.sh --from-cr` + flat image `--provenance=false`; see `docx/Deploy_Runbook.md`. |
| **Tools (16)** | search_metadata *(now live-verified)*, get_platform_overview, get_ownership, get_entity_details, analyze_impact, diagnose_entity *(now autonomous RCA)*, get_related_context, read_gitlab_file, read_confluence_page, search_jira_tickets, get_recent_commits, get_data_freshness, get_schema, get_platform_alerts, get_health_briefing, **get_changes_since** *(NEW — temporal)* |
| **Web UI** | `ui/server.py` + `ui/index.html` — Claude-Desktop style, Acme logo/colors, **phase-morph thinking pill**, Mermaid render, tool-trace, chat history. Run local + LIVE: `./run_local.sh` → localhost:3000 |
| **Demo cases (CHỐT — 3 cho video)** | **(1) Data Discovery + Trust Layer** "loan_core_statement là gì? ai sở hữu?" → metadata card + 🟢 live badge. **(2) Cross-team Impact (REAL)** "sửa appid trong loan_core_statement thì team nào khác bị ảnh hưởng?" → Product Experience/ZTM/Accounting/GE&RC + Mermaid blast-radius. **(3) Autonomous Incident RCA** "tại sao loan_core_statement chậm?" → upstream culprit + smoking-gun commit + draft Jira/Slack. Optional 4th: recent commits (GitLab-fixed) hoặc get_changes_since (temporal). Full script: `docs/VIDEO_SCRIPT.md`. |
| **Days to Deadline** | **~1 day — June 17, 2026, 12:00 PM (GMT+7)** |

---

## 4-BUG. Bug Registry (found 2026-06-12)

> ⚠️ All bugs below MUST be fixed before any demo testing.

### 🔴 P0 Bugs — App won't run

| ID | File | Bug | Impact |
|----|------|-----|--------|
| BUG-01 | `src/tools/discovery.py:12-18` | `Dataset(**d)` throws `TypeError`: JSON uses `entityType`, `schema`, `lineage:{upstream,downstream}` but dataclass uses `type`, no `schema`, `upstream`/`downstream` directly. `Pipeline(**p)` same issue with `directory_structure`, `files`, `lineage`. | **App crashes on first tool call — nothing works** |
| BUG-02 | `src/tools/discovery.py:236` | `asyncio.run(client.convert_html_to_markdown(...))` called inside async context → `RuntimeError: This event loop is already running` | **`read_confluence_page` tool always crashes** |

### 🟡 P1 Bugs — App runs but demo fails

| ID | File | Bug | Impact |
|----|------|-----|--------|
| BUG-03 | `src/data_platform/datasets.json` | All 856 datasets have empty `description`, `schema`, `lineage.upstream`, `lineage.downstream`. 289/856 have `owner: unknown`. | **Impact Analysis returns 0 results. Data Discovery returns names only, no useful info.** |
| BUG-04 | `src/data_platform/pipelines.json` | All 6 pipelines have empty `lineage.upstream`/`downstream`. | **Impact chain broken — cannot show pipeline affected by dataset change** |
| BUG-05 | `src/tools/discovery.py:6-19` | `load_data_platform_engine()` reads JSON from disk on **every** tool call (3-4 calls per request = 856 datasets loaded 3-4x per query). | **Performance: slow, wasteful** |
| BUG-06 | `src/tools/discovery.py:156-190` | `requests.get()` (synchronous) inside async call chain in `read_gitlab_file()` | **Blocks event loop under load** |

### 🟠 P2 Gaps — App works but quality low

| ID | File | Gap | Impact |
|----|------|-----|--------|
| GAP-01 | `src/tools/discovery.py:22-32` | `search_metadata()` has no result limit. `search("user")` → 100+ results → LLM context overflow. | **Poor answer quality, potential token limit hit** |
| GAP-02 | `src/core/schema.py` | No `KnowledgeArticle`/`Document` entity class for Confluence data. `confluence_knowledge.json` cannot be typed/searched properly. | **Confluence knowledge not searchable via tools** |
| GAP-03 | `src/core/engine.py:40-55` | BFS lineage only traverses within same entity type. No cross-entity (pipeline→dataset) traversal. `relationships: List[Dict]` declared but never used. | **Impact analysis cannot show "DAG X is affected" when dataset changes** |
| GAP-04 | `src/tools/discovery.py` | `search_metadata()` only searches datasets + pipelines. Cannot find Confluence docs. | **Onboarding scenario broken — user asks for docs, gets nothing** |

---

## 5. Pattern Adoption Decision Matrix

> Last reviewed: 2026-06-11. Score: **8/10** — solid, pragmatic, correct order.
> ⚠️ Key adjustment: Document Chunking & Hybrid Search pulled up to P2 — both directly block demo if missing.

| Pattern | Source | Decision | Priority | Rationale |
|---------|--------|----------|----------|-----------|
| Entity Schema (tier, tags, status) | OpenMetadata | ✅ ADOPT | **P1** | Foundation for everything |
| schema.yml pattern (column docs in JSON) | dbt | ✅ ADOPT | **P1** | Apply column-level docs to datasets.json |
| Multi-Owner Model | OpenMetadata | ✅ ADOPT | **P2** | Richer ownership answers in demo |
| Tier System (1/2/3) | OpenMetadata | ✅ ADOPT | **P2** | AI knows which entities are critical |
| Typed Relations | Backstage | ✅ ADOPT | **P2** | Meaningful graph edges (LOADED_BY, etc.) |
| **Document Chunking** *(adjusted up)* | RAGFlow | ✅ ADOPT | **P2** | Confluence is primary data source + MCP access available. Without this, real data cannot enter the graph. |
| **Hybrid Search** *(adjusted up)* | RAGFlow | ⚡ SIMPLIFY | **P2-P3** | Core feature — if user types "bảng user" and `user_dim` doesn't appear, demo fails immediately. Exact→partial→fuzzy ranking. |
| Domain/System Hierarchy | Backstage | ✅ ADOPT | **P3** | Group entities into System → Domain structure |
| Metadata Filtering | LlamaIndex | ✅ ADOPT | **P3** | Pre-filter by domain/tier/type before search |
| Two-Level Retrieval | GraphRAG | ⚡ SIMPLIFY | **P3** | Simplified: SPECIFIC query → direct graph lookup. BROAD query → domain/team summary scan. No full GraphRAG needed. |
| Community Detection | GraphRAG | ❌ SKIP | — | Needs thousands of nodes to be meaningful. Hackathon has < 20 nodes. |
| SQL Lineage Parsing | dbt | ❌ SKIP | — | Hardcoding lineage in JSON is faster and more stable for demo. |

---

## 6. Key Configurations Reference

| Config | Value |
|--------|-------|
| Model Path | `minimax/minimax-m2.5` |
| Base URL | `https://maas-llm-aiplatform-hcm.api.vngcloud.vn/v1` |
| Port | `8080` |
| Git Branch | `feat/integrate-agentbase-skills` |
| IAM Config | `.greennode.json` |
| API Key | `.env` → `MAAS_API_KEY` |

---

*Last Updated: 2026-06-16 — **Submission-ready.** Prod = v14 (`v20260615c`). Local branch ahead with: REAL cross-team impact (Confluence-derived: Product Experience/ZTM/Accounting/GE&RC, replaced seed), GitLab namespace fix (get_recent_commits resolves any namespace), UI phase-morph thinking pill, and ALL deliverables — README (senior) + use-case (VN <300w) + video script + subtitles.srt + Acme-brand thumbnail + clean `public-submission` branch (PII/secret-scanned). 3 demo cases chốt: Discovery+TrustLayer / Cross-team Impact / Autonomous RCA (see `docs/VIDEO_SCRIPT.md`). Remaining (user): push public-submission → set Public → record video → submit (team AITree). Prev v12 note below.*
*Prev — 2026-06-15 — DEPLOYED LIVE: runtime version 12 (image `v20260615a`), ACTIVE. F1 Trust Layer + F2 Autonomous RCA + F3 Temporal (15→16 tools). Deploy via `runtime.sh --from-cr` + flat image. Prod PUBLIC → cache fallback. Prev: v9 below.*
*Prev — Live v9 (image v20260613i). UX polish round: UI got typewriter reveal, copy/hỏi-lại buttons, chat-history delete/rename, scroll-to-bottom; sidebar "Agent Functions" catalog now uses friendly VN labels (raw fn name hidden small). Backend: onboarding → checklist, comparison → side-by-side table, cached DataHub session (lower latency). No new tools (still 15). Prev: v8 below.*
*Prev — Live v8 (image v20260613h). UX refinement per user: renamed to "Acme Data Platform AI", REMOVED confidence score (kept source citations), added contextual follow-up chips, incident verdict badge + runbook, entity-card lead, vivider Mermaid; UI got a sidebar tool catalog (all 15 tools, click-to-expand). No new tools. Previous: v7 below.*
*Prev — Live v7 (image v20260613g, 15 tools). Win-grade hardening (tier-overwrite/timeouts/redaction/bounded-triage), 3 new wow features (Mermaid lineage viz, citation+confidence footer, daily health briefing), clean Credit lineage seed, and a Claude-Desktop-style Acme Web UI (ui/) all done & verified. Reviewed via /code-review + 3 agents. Remaining for submission: README + use case + demo video + sanitize→GitHub push.*
