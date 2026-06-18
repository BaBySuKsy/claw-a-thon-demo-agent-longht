# Project Plan: Acme Knowledge Platform (Data Platform Agent Ai)

> ⚠️ **MANDATORY RULE**: This file MUST be updated after EVERY completed action and EVERY new planned task. No exceptions.
> Track all execution progress in: [Session_Progress_Tracker.md](file:///Users/lap14489/Documents/claw-a-thon-demo-agent-longht/docx/Session_Progress_Tracker.md)

---

## 1. Vision & Strategy

- **Long-term Vision**: **Acme Knowledge Operating System**. A unified platform where AI understands the entire ecosystem: Organizational structure, Products, Services, Data Lineage, and Documentation.
- **MVP Scope (Claw-a-thon)**: **Data Platform Domain**. Focusing on Hive, Spark, Airflow, and Confluence within the Data Platform team to prove value quickly.
- **Core Philosophy**: **Metadata-First + Knowledge Graph**. We don't just dump documents; we standardize knowledge into a typed Graph structure. AI is the interface; Metadata is the "Moat".
- **Competition Strategy**: Primary category → **Data Analysis**. Secondary → **Agentic Assistant**.

---

## 2. Technical Architecture (Senior Level)

### 2.1 Data Sources

#### MVP Real Sources (connected via Ingestion Pipeline)
| Source | Access | Extracts |
|--------|--------|----------|
| **DataHub** | REST/GraphQL API (no token — public internal endpoint) | Table schemas, column definitions, lineage graph, tags, owners, platforms (Hive/Kafka/S3) |
| **GitLab** | REST API + PAT token | Airflow DAG definitions (`.py`), SQL scripts, project READMEs, pipeline configs |
| **Confluence** | REST API + token | Table documentation pages, ETL logic docs, team onboarding docs, runbooks |

#### Future Sources (Phase 2)
- **Jira**: Task context, ownership, feature updates.
- **Direct Hive/Presto Catalog**: Live schema introspection.

### 2.2 Industry-Standard Schema Design

Entity schema follows **OpenMetadata** and **Backstage** patterns:

```json
{
  "id": "dataset:user_dim",
  "name": "user_dim",
  "entityType": "table",
  "owner": {
    "type": "team",
    "name": "data-platform",
    "slack": "#data-platform-oncall"
  },
  "domain": "User",
  "tier": "Tier1",
  "tags": ["pii", "core", "hive"],
  "status": "active",
  "description": "Dimension table storing Acme user profile and Identity status.",
  "lineage": {
    "upstream": ["dataset:user_raw", "dataset:identity_raw"],
    "downstream": ["dataset:user_session_mart", "dashboard:user_analytics"]
  },
  "schema": {
    "database": "analytics",
    "table": "user_dim",
    "columns": [
      {"name": "user_id", "type": "STRING", "nullable": false, "pii": true},
      {"name": "identity_status", "type": "STRING", "nullable": false}
    ]
  }
}
```

### 2.3 Relationship Types (Backstage-inspired)

Typed graph edges for the Knowledge Engine:

| Relation Type | Example |
|---------------|---------|
| `LOADED_BY` | `dataset:user_dim` ← `pipeline:user-etl` |
| `OWNED_BY` | `dataset:user_dim` → `team:data-platform` |
| `DEPENDS_ON` | `dashboard:user_analytics` → `dataset:user_dim` |
| `PRODUCES` | `pipeline:user-etl` → `dataset:user_session_mart` |
| `CONSUMES` | `pipeline:user-etl` ← `dataset:user_raw` |
| `PART_OF` | `team:data-platform` → `domain:data-platform` |

### 2.4 Tier System (OpenMetadata)

| Tier | Meaning | Example |
|------|---------|---------|
| `Tier1` | Production-critical, affects revenue/users | `transaction_fact`, `user_dim` |
| `Tier2` | Important but not real-time critical | `user_session_mart`, `payment_summary` |
| `Tier3` | Experimental / Dev / Non-production | `sandbox_logs`, `test_*` tables |

### 2.5 Backend Stack (MVP)

```
User Query (Natural Language)
    ↓
[copilot.py] Query Router → classify intent
    ↓                        (discovery / impact_analysis / onboarding)
[MiniMax-M2.5 via MaaS] ← tool definitions injected
    ↓ tool_call response
[Tool Dispatcher]
    ├── search_metadata(query, domain?, tier?, type?) → filtered results
    ├── get_ownership(entity_id) → structured owner dict
    ├── analyze_impact(entity_id) → recursive BFS downstream
    └── get_lineage(entity_id, direction) → full multi-hop chain
    ↓
[KnowledgeEngine] in-memory graph (loaded from JSON)
    ↓
Final synthesized response with Tier-awareness
```

### 2.6 Query Routing Strategy (Simplified GraphRAG)

```
"What is user_dim?" → LOCAL search (specific entity lookup)
"Who owns transaction_fact?" → LOCAL search (ownership)
"If I change raw_transaction, what breaks?" → LOCAL search (impact analysis)
"What does the Data Platform team do?" → GLOBAL search (domain/team summary)
"I just joined, what should I read?" → ONBOARDING flow (curated entity list)
```

### 2.7 Ingestion Pipeline Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  REAL DATA SOURCES                       │
│  DataHub API ──┐                                        │
│  GitLab API  ──┼──→ src/ingestion/                      │
│  Confluence  ──┘     ├── datahub_client.py              │
│                      ├── gitlab_client.py               │
│                      └── confluence_client.py           │
└──────────────────────────────┬──────────────────────────┘
                               ↓
                    src/ingestion/extractor.py
                    (normalize → OpenMetadata schema)
                               ↓
            ┌──────────────────┴──────────────────┐
            ↓                                     ↓
  datasets.json (tables)               pipelines.json (DAGs)
            └──────────────────┬──────────────────┘
                               ↓
               KnowledgeEngine (in-memory graph)
                               ↓
                  DataPlatformCopilot (MiniMax-M2.5)
```

**Extraction targets per source:**
```
DataHub  → entity URNs → table name, platform, schema, columns, lineage, owners, tags
GitLab   → DAG files (.py) → dag_id, schedule, upstream datasets, owner team
Confluence → pages → table descriptions, team context, ETL notes, runbooks
```

---

## 3. Implementation Roadmap

> Status Legend: `[ ]` Pending | `[→]` In Progress | `[x]` Done

### 🔴 P0 — CRITICAL: Bug Fixes (App Won't Run Without These)
**Goal**: Fix runtime crashes identified in 2026-06-12 code review. ALL must be done before any testing.

| # | Task | File(s) | Bug | Acceptance Criteria |
|---|------|---------|-----|---------------------|
| P0.1 | `[x]` ~~Implement real AsyncOpenAI LLM call~~ | `src/agents/copilot.py` | *(done in Session 2)* | Agent uses MiniMax-M2.5 via tool-calling loop |
| P0.2 | `[x]` **Fix schema mismatch in `load_data_platform_engine()`** | `src/tools/discovery.py` | BUG-01 FIXED: Added `_normalize_dataset()`, `_normalize_pipeline()`, `_normalize_article()`. Engine loads 867 entities. | ✅ |
| P0.3 | `[x]` **Fix `asyncio.run()` inside async context** | `src/tools/discovery.py` | BUG-02 FIXED: `read_confluence_page()` is `async def`, uses `await`. | ✅ |

---

### 🟡 P1 — Foundation: Performance + Data Enrichment
**Goal**: Fix performance bugs and enrich data so the 3 demo scenarios actually work.

| # | Task | File(s) | Bug | Acceptance Criteria |
|---|------|---------|-----|---------------------|
| P1.1 | `[x]` ~~Upgrade `schema.py`~~ | `src/core/schema.py` | *(done)* OpenMetadata fields already added | `tier`, `tags`, `owner: Dict` present |
| P1.2 | `[x]` ~~Fix `engine.py` lineage to BFS~~ | `src/core/engine.py` | *(done)* Recursive BFS with depth tracking | Works for multi-hop |
| P1.3 | `[x]` **Make `KnowledgeEngine` a singleton** | `src/tools/discovery.py` | BUG-05 FIXED: `get_engine()` singleton — engine loaded once, reused. | ✅ |
| P1.4 | `[x]` **Sync HTTP → thread pool executor** | `src/agents/copilot.py` | BUG-06 FIXED: `_run_read_gitlab_file()` uses `run_in_executor()`. | ✅ |
| P1.5 | `[x]` **Enrich `datasets.json`**: 14 key tables enriched | `src/data_platform/datasets.json` | BUG-03 FIXED: 14 datasets have real descriptions + lineage + tier. | ✅ |
| P1.6 | `[x]` **Enrich `pipelines.json`**: `credit-curated-etl` lineage added | `src/data_platform/pipelines.json` | BUG-04 PARTIAL: credit-curated-etl has 5 upstream Credit tables. Tier→Tier1. | ✅ |

---

### 🟠 P2 — Knowledge Graph Enrichment + Search Quality
**Goal**: Make graph semantically richer, ensure search is demo-reliable, add Confluence to unified search.
**⚠️ Note**: GAP-01, GAP-02, GAP-04 directly break demo scenarios — fix these before P3.

| # | Task | File(s) | Gap | Acceptance Criteria |
|---|------|---------|-----|---------------------|
| P2.1 | `[x]` **Limit `search_metadata()` to 15, sort Tier1 first** | `src/tools/discovery.py` | GAP-01 FIXED: `limit=15`, `_TIER_ORDER` sort. | ✅ |
| P2.2 | `[x]` **Add `KnowledgeArticle` entity to `schema.py`** | `src/core/schema.py` | GAP-02 FIXED: `KnowledgeArticle(Entity)` with `content_chunks`, `page_id`, `relations`. | ✅ |
| P2.3 | `[x]` **Load Confluence into engine + unified search** | `src/tools/discovery.py` | GAP-04 FIXED: `confluence_knowledge.json` loaded into engine, searchable. | ✅ |
| P2.4 | `[x]` **`add_relationship()` + `find_by_relation()` to engine** | `src/core/engine.py` | GAP-03 FIXED: typed edge methods added, `relationships` list now used. | ✅ |
| P2.5 | `[x]` **Cross-entity BFS lineage (Dataset↔Pipeline)** | `src/core/engine.py` | GAP-03 FIXED: reverse-index traversal, Impact Analysis crosses entity type boundaries. | ✅ |
| P2.6 | `[x]` Tier-aware impact analysis: Tier1 warning flag | `src/tools/impact.py` | P3.3 DONE: `critical_tier1_count` + warning string. Singleton fix. Tier1-first sort. | ✅ |
| P2.7 | `[ ]` **[Hybrid Search]** Exact → partial → fuzzy ranking | `src/tools/discovery.py` | *(P3)* | `search("bảng user")` still finds `user_dim` |
| P2.8 | `[ ]` Add `teams.json` + `domains.json` seed data | `src/data_platform/` | *(P3)* | Onboarding flow returns team structure |

---

### 🟡 P1 — Foundation: Schema, Data & Ingestion Pipeline
**Goal**: Make the knowledge graph industry-standard AND populated with real Acme data from actual sources.

#### P1-A: Code Fixes (schema + engine)
| # | Task | File(s) | Acceptance Criteria |
|---|------|---------|---------------------|
| P1.1 | `[ ]` Upgrade `schema.py`: add `tier`, `tags`, `status`, `owner: Dict` | `src/core/schema.py` | All entity dataclasses have OpenMetadata fields |
| P1.2 | `[ ]` Fix `engine.py` lineage: recursive BFS traversal with depth tracking | `src/core/engine.py` | `get_lineage("dataset:raw_transaction", "downstream")` returns all nodes at all depths |

#### P1-B: Ingestion Pipeline (extract real data from 3 sources)
| # | Task | File(s) | Acceptance Criteria |
|---|------|---------|---------------------|
| P1.3 | `[ ]` **DataHub client**: explore API → extract all table entities (name, schema, lineage, owner, tags) | `src/ingestion/datahub_client.py` | Fetch 10+ table entities from `https://datahub.acme.vn` via REST/GraphQL API |
| P1.4 | `[ ]` **GitLab client**: authenticate with PAT → list DP projects → extract DAG `.py` files + READMEs | `src/ingestion/gitlab_client.py` | Fetch DAG list with `dag_id`, `schedule`, `owner` from at least 5 DAG files |
| P1.5 | `[ ]` **Confluence client**: authenticate → crawl Data Platform space → extract table doc pages | `src/ingestion/confluence_client.py` | Fetch 10+ Confluence pages with table name, description, owner extracted |
| P1.6 | `[ ]` **Extractor + normalizer**: orchestrate 3 clients → normalize all raw data → OpenMetadata JSON schema | `src/ingestion/extractor.py` | Running `python src/ingestion/extractor.py` outputs valid `datasets.json` + `pipelines.json` |
| P1.7 | `[ ]` Update `discovery.py` loader to handle new schema fields | `src/tools/discovery.py` | `load_data_platform_engine()` correctly deserializes `owner: Dict`, `tier`, `tags` |

#### P1-C: Output Validation
| # | Task | File(s) | Acceptance Criteria |
|---|------|---------|---------------------|
| P1.8 | `[ ]` Validate extracted data: `datasets.json` 15+ records, `pipelines.json` 8+ records | `src/data_platform/` | Agent answers "What is `user_dim`?" with real schema info from DataHub |

**Acceptance criteria**: `datasets.json` has 15+ real records; Impact Analysis shows Tier1 warning; Agent answers with real table schemas.

| # | Task | File(s) | Acceptance Criteria |
|---|------|---------|---------------------|
| P3.1 | `[ ]` Pre-filtering in `search_metadata` (domain, tier, entity_type) | `src/tools/discovery.py` | `search_metadata("transaction", tier="Tier1")` returns only Tier1 entities |
| P3.2 | `[x]` **`_route_query()` intent classifier** | `src/agents/copilot.py` | DONE 2026-06-13: IMPACT/ONBOARDING/SPECIFIC/BROAD routing with Vietnamese+English patterns. 4/4 tests pass. Routing hint injected as system message. | ✅ |
| P3.3 | `[x]` **Tier-aware impact: `critical_tier1_count` + warning** | `src/tools/impact.py` | DONE 2026-06-13: Singleton + Tier1-first sort + warning string. Verified. | ✅ |
| P3.4 | `[x]` **Upgrade system prompt: Tier-awareness + onboarding flow** | `src/agents/prompts/system.py` | DONE 2026-06-13: Tier system explained, tool guidelines, Tier1 warning format, onboarding 4-step flow. | ✅ |

---

### 🟢 P4 — Deployment & Submission
**Goal**: Ship to production and submit on time.

| # | Task | File(s) | Acceptance Criteria |
|---|------|---------|---------------------|
| P4.1 | `[x]` Harden `Dockerfile` (non-root user, port 8080, healthcheck) | `Dockerfile` | ✅ python:3.10-slim, non-root appuser, healthcheck |
| P4.2 | `[x]` Docker build (linux/amd64) | — | ✅ `v20260613e` built + pushed to CR |
| P4.3 | `[x]` Agent identity (auto-provisioned by runtime) | `agentbase-skills/` | ✅ runtime `acme-dp-agent` registered |
| P4.4 | `[x]` Deploy to GreenNode AgentBase Runtime | — | ✅ LIVE, public endpoint, runtime version 5 ACTIVE |
| P4.5 | `[x]` End-to-end validation of demo scenarios | — | ✅ Onboarding/Incident/Impact/Discovery/Alerts all pass live |
| P4.6 | `[ ]` Record 2-3 min demo video | — | Video shows scenarios live (pending) |
| P4.7 | `[ ]` Write 100-200 word use case description | — | `docx/Use_Case_Description.md` (pending) |
| P4.8 | `[ ]` Public GitHub repo + README | `README.md` | DEFERRED — sanitize internal data (IPs/DB-users/emails) before public push |

---

## 3b. Differentiation Features (2026-06-14) — beyond a standard catalog

The base 15 tools were table-stakes (discovery/ownership/impact/freshness = OpenMetadata/Atlan parity). To stand out as an *agent* (not a catalog chatbot), three features were added — inspired by the hottest 2026 agent repos (Graphiti temporal KG; autonomous action-taking agents):

| # | Feature | What makes it "wow" | Status |
|---|---------|---------------------|--------|
| **F1** | **Live data + Trust Layer** | Most-used tool (`search_metadata`) now live-verifies the freshness of its top hits; every answer carries a 🟢 live / 🟡 cache / 🔴 stale badge with verified-at time. Solves "is this the latest data?" — a trust + demo win. | ✅ **LIVE (v12)** |
| **F2** | **Autonomous RCA Investigator** | `diagnose_entity` is now multi-step & autonomous: walks UPSTREAM lineage to find the *real culprit* (not just the symptom), fetches the *smoking-gun commit diff*, and drafts a ready-to-file Jira ticket + Slack alert with a confidence score. This is the headline demo. | ✅ **LIVE (v12)** |
| **F3** | **Temporal time-travel graph** | `get_changes_since` answers "what changed in the last 24h that could break my table?" — schema drift (live vs baseline = potentially breaking), newly-stale Tier1, recent commits. Graphiti-style observation log accumulates over time. A capability a static catalog cannot offer. | ✅ **LIVE (v12)** |
| **F4** | **Action-taking / write-back** *(planned future)* | Close the agentic loop: actually SEND the F2 drafts — create the Jira ticket (Jira REST), post the Slack alert, or open a GitLab MR to fix a DAG — behind a human-confirm step. F2 already emits the draft payloads, so F4 = "wire the send + confirmation". Strongest **Agentic Assistant** category point. | ⏳ deferred |

> **Deploy (2026-06-15):** runtime **version 12** (image `v20260615a`) ACTIVE. Deploy via `runtime.sh update --from-cr` (IAM only) + **flat image** `--provenance=false --sbom=false` (default OCI-index+attestation image caused rollout health-probe ERROR on v10/v11). Prod is **PUBLIC mode** → can't reach internal DataHub/GitLab/Jira → live features fall back to cache (Trust Layer shows "stale"); deploy **VPC mode** for true live data. Full runbook: `docx/Deploy_Runbook.md`.

---

## 4. High-Impact Demo Scenarios

| # | Scenario | Query | Tools Invoked | "Wow" Factor |
|---|----------|-------|---------------|--------------|
| 1 | **Data Discovery** | "What is the `user_dim` table? Who owns it? Which dashboards use it?" | `search_metadata` → `get_ownership` → `get_lineage` | Complete metadata card in seconds |
| 2 | **Smart Onboarding** | "I just joined the Data Platform team. What are the key projects and docs I must read?" | `search_metadata(domain=data-platform)` + team summary | Curated onboarding guide from graph |
| 3 | **Impact Analysis** | "If I change the `appid` column in `raw_transaction`, what downstream tables and DAGs will break?" | `analyze_impact` → recursive BFS → tier-sorted result | Shows Tier1 warning + full impact chain |

---

## 5. Resource Configuration

| Config | Value |
|--------|-------|
| Default Model | `minimax/minimax-m2.5` |
| MaaS Endpoint | `https://maas-llm-aiplatform-hcm.api.vngcloud.vn/v1` |
| Infrastructure | Docker + GreenNode AgentBase Runtime |
| Port | `8080` |
| Git Branch | `feat/integrate-agentbase-skills` |

---

## 6. Success Metrics

| Metric | Before | Target |
|--------|--------|--------|
| Data discovery time | 30 min (manual Confluence search) | < 1 min (AI-powered) |
| Impact analysis | Manual, error-prone | Automated, full lineage with Tier warnings |
| Knowledge centralization | Siloed (Confluence + chat + memory) | Unified Knowledge Graph, queryable via chat |
| Demo stability | N/A | 100% uptime during demo (no external API dependency except MaaS) |

---

*Last Updated: 2026-06-16 — Submission-ready. Prod = v14 (`v20260615c`); local branch ahead with REAL cross-team impact (Confluence-derived team refs: Product Experience/ZTM/Accounting/GE&RC, replaced seed via `src/ingestion/confluence_org_extractor.py`), GitLab namespace-resolution fix, UI phase-morph thinking pill, and all submission deliverables (README/use-case/video/thumbnail + clean `public-submission` branch). 3 demo cases chốt: Discovery+TrustLayer / Cross-team Impact / Autonomous RCA. Prev (v13) note below.*
*Prev — 2026-06-15 (PM) — runtime version 13 (`v20260615b`): parallel multi-tool dispatch, multi-query RRF retrieval + precision rerank, REAL SSE streaming (first-token ~2.6s). Prev note below.*
*Prev — 2026-06-15 — 3 differentiation features (§3b) DEPLOYED LIVE: runtime version 12 (image `v20260615a`), ACTIVE. F1 Trust Layer + F2 Autonomous RCA + F3 Temporal (tool count 15→16), all verified on prod. Deploy via runtime.sh --from-cr + flat image (see docx/Deploy_Runbook.md). Prod PUBLIC mode → live features fall back to cache (VPC needed for live data). F4 write-back deferred. Prev note below.*
*Prev — 2026-06-13 (Evening) — Agent LIVE v7 (15 tools). Beyond v5: win-grade hardening (no tier-overwrite, HTTP timeouts, bounded incident triage, redaction guard, name resolution), 3 wow features (Mermaid lineage viz, citation+confidence footer, daily health briefing), clean Credit lineage seed, + a Claude-Desktop-style Acme Web UI (ui/server.py + ui/index.html). Reviewed via /code-review + agents. Remaining for submission: demo video + 100-200w use case + README + sanitize→public GitHub push.*
