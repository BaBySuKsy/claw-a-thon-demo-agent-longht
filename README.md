<div align="center">

# 🤖 ZaloPay Data Platform AI

**Knowledge Operating System cho nền tảng dữ liệu — hỏi đáp metadata, phân tích tác động xuyên team, và điều tra sự cố tự động bằng ngôn ngữ tự nhiên.**

[![Track](https://img.shields.io/badge/Track-Data%20Analysis-0033C9)](#)
[![Secondary](https://img.shields.io/badge/Secondary-Agentic%20Assistant-00CF6A)](#)
[![Model](https://img.shields.io/badge/LLM-MiniMax--M2.5-7C3AED)](#)
[![Runtime](https://img.shields.io/badge/Runtime-GreenNode%20AgentBase-1E293B)](#)
[![Status](https://img.shields.io/badge/status-LIVE-00CF6A)](#)

**Team AITree** · GreenNode Claw-a-thon 2026

</div>

---

> [!NOTE]
> **Synthetic data — safe to explore.** This is a ZaloPay-branded hackathon product, but the
> repository and the live demo run on a **fully synthetic, fictional dataset** — **no production
> data is used**. This is a deliberate choice to eliminate any risk of leaking internal/sensitive
> information, while still letting anyone experience the agent end-to-end. Every table, pipeline,
> team, owner, doc, Jira ticket and commit is fabricated by `scripts/generate_synthetic_data.py`
> (fictional `acme.*` namespace); the agent's answers are accurate and internally consistent, but
> the underlying data is not real.
>
> *Toàn bộ dữ liệu trong repo & bản demo là **dữ liệu giả hoàn toàn** (không dùng data
> production) để tránh rủi ro lộ thông tin nội bộ — nhưng vẫn cho trải nghiệm agent y như thật.*

> [!TIP]
> **Using real production data (optional, local only).** The hosted/public deployment is
> intentionally cut off from internal systems and **only ever serves the synthetic cache**. To run
> the agent against **real** data you must run it **locally** — inside your corporate network / VPN —
> and supply your **own credentials/tokens for every source** you want it to reach (DataHub, GitLab,
> Jira, Confluence) in a local `.env` (see `.env.example`). The agent only queries the sources you
> provide tokens for; anything without a token falls back to the synthetic cache. Real credentials
> are never committed and never baked into the published image.
>
> *Muốn dùng **data thật**: chỉ có thể **chạy project ở local** (trong mạng nội bộ / VPN) và **tự
> cung cấp toàn bộ key/token** cho mọi nguồn muốn truy cập (DataHub / GitLab / Jira / Confluence)
> trong `.env`. Nguồn nào không có token sẽ tự fallback về cache giả.*

---

## Mục lục
- [1. Bối cảnh & vấn đề](#1-bối-cảnh--vấn-đề)
- [2. Giải pháp](#2-giải-pháp)
- [3. Điểm khác biệt](#3-điểm-khác-biệt)
- [4. Kiến trúc hệ thống](#4-kiến-trúc-hệ-thống)
- [5. Mô hình Knowledge Graph](#5-mô-hình-knowledge-graph)
- [6. Pipeline truy hồi & suy luận](#6-pipeline-truy-hồi--suy-luận)
- [7. Bộ 16 công cụ](#7-bộ-16-công-cụ)
- [8. Điểm nhấn kỹ thuật](#8-điểm-nhấn-kỹ-thuật)
- [9. Cài đặt & chạy](#9-cài-đặt--chạy)
- [10. API](#10-api)
- [11. Kịch bản demo](#11-kịch-bản-demo)
- [12. Live vs Cache](#12-live-vs-cache)
- [13. Cấu trúc dự án](#13-cấu-trúc-dự-án)
- [14. Roadmap](#14-roadmap)
- [15. Tech stack](#15-tech-stack)

---

## 1. Bối cảnh & vấn đề

Một nền tảng dữ liệu trưởng thành (Hive/Spark/Airflow, hàng trăm bảng, DAG, dashboard) có một nghịch lý: **dữ liệu thì nhiều, nhưng *kiến thức về dữ liệu* lại phân mảnh và khó truy vấn.** Metadata nằm rải rác ở DataHub (schema, lineage), GitLab (DAG code), Confluence (tài liệu), Jira (sự cố) — và phần lớn ở trong đầu vài người.

Hệ quả, ba câu hỏi lặp lại mỗi ngày đều tốn kém:

| Câu hỏi | Hiện tại | Chi phí |
|---------|----------|---------|
| "Bảng này là gì? Ai sở hữu? Ai đang dùng?" | Lục Confluence + hỏi chat | **~30 phút/lần** |
| "Sửa cột này thì cái gì hỏng?" | Dò lineage thủ công | Dễ sót → **rủi ro sự cố P0** |
| "Bảng đang trễ, lỗi do đâu?" | Soi freshness + commit + Jira bằng tay | **Chậm khi đang cháy** |

**Insight cốt lõi:** vấn đề không phải thiếu dữ liệu, mà thiếu một **lớp tri thức hợp nhất, có cấu trúc, hỏi-đáp-được**.

## 2. Giải pháp

Một **AI agent** đặt trên một **knowledge graph metadata hợp nhất** (~886 entity, ingest từ DataHub/GitLab/Confluence/Jira, chuẩn hoá theo OpenMetadata & Backstage). Người dùng hỏi tiếng Việt/Anh; agent phân loại ý định → gọi đúng công cụ → tổng hợp câu trả lời **có dẫn nguồn + nhãn độ tin cậy**, có thể **stream realtime**.

> **Triết lý thiết kế — Metadata-First + Knowledge Graph.** AI là *giao diện*; metadata chuẩn hoá là *moat*. Chúng tôi không nhồi tài liệu thô vào LLM — chúng tôi mô hình hoá tri thức thành graph có kiểu (typed graph) rồi để LLM điều phối công cụ trên đó. Điều này cho câu trả lời *grounded* (có gốc), giảm hallucination, và mở rộng được.

## 3. Điểm khác biệt

Bộ tính năng "catalog" (discovery/ownership/impact/freshness) là điều kiện cần — ngang OpenMetadata/Atlan. Ba thứ dưới đây là điều kiện đủ để nó là một **agent**, không phải chatbot tra cứu:

1. 🔗 **Phân tích tác động XUYÊN TEAM (dữ liệu thật).** Không chỉ "bảng downstream nào hỏng" — agent chỉ ra **team KHÁC nào đang phụ thuộc dữ liệu này** (vd Product Experience, Finance Operations, Platform Engineering, Growth Products) kèm sơ đồ blast-radius. Các quan hệ cross-team được **suy ra từ bằng chứng tham chiếu thật trong Confluence** (team-space nào nhắc tới dữ liệu data-platform), không phải seed. Đây là tư duy *Knowledge OS*: một thay đổi → thấy hệ luỵ toàn tổ chức.
2. 🚨 **Điều tra sự cố tự động (Autonomous RCA).** `diagnose_entity` đi **ngược lineage** tìm *nguyên nhân gốc thật* (không dừng ở triệu chứng), lấy đúng **commit gây lỗi (smoking-gun)**, và soạn sẵn **draft Jira + Slack** — chỉ chờ người xác nhận.
3. 🟢 **Trust Layer (live vs cache).** Mỗi câu trả lời gắn nhãn 🟢 *live* / 🔴 *cache* với thời điểm verify. Agent **không bao giờ giả vờ dữ liệu là realtime** khi nó không phải — yếu tố sống còn với một công cụ data.

## 4. Kiến trúc hệ thống

```
                          User query (NL · VN/EN)
                                   │
                    ┌──────────────▼───────────────┐
                    │  _route_query()  intent       │  IMPACT · INCIDENT · ONBOARDING
                    │  classifier (regex VI+EN)     │  CHANGES · BRIEFING · SPECIFIC · BROAD
                    └──────────────┬───────────────┘
                                   │ + routing hint
                    ┌──────────────▼───────────────┐
                    │   MiniMax-M2.5 (GreenNode     │◀── 16 tool schemas (OpenAI function-calling)
                    │   MaaS, tool-calling loop)    │     temperature 0.1 · max 6 iterations
                    └──────────────┬───────────────┘
                                   │ tool_calls
                    ┌──────────────▼───────────────┐
                    │  Tool dispatcher              │  asyncio.gather (song song)
                    │  + redaction guard            │  scrub IP/email/cred khỏi output
                    └───────┬───────────────┬───────┘
                            │               │
              ┌─────────────▼───┐   ┌───────▼──────────────────────────┐
              │ KnowledgeEngine │   │ Live clients (JIT + cache fallback)│
              │ in-memory graph │   │ DataHub · GitLab · Confluence · Jira│
              │ BFS lineage     │   └────────────────────────────────────┘
              │ (cross-entity)  │
              └─────────────┬───┘
                            │
              ┌─────────────▼────────────────────────────┐
              │ Synthesis + Trust Layer badge + citations │ → JSON  hoặc  SSE stream
              └───────────────────────────────────────────┘
```

**Quyết định kiến trúc đáng chú ý:**
- **Graph in-memory, nạp 1 lần lúc boot** (singleton) — đọc graph là thao tác mili-giây, không phụ thuộc API ngoài → demo ổn định, độ trễ thấp.
- **Live data là *lớp phủ*, không phải đường dẫn nóng** — 3 tool dùng nhiều nhất đọc graph; live API chỉ verify freshness top-hit (bounded timeout) rồi gắn nhãn. Mất mạng nội bộ ⇒ degrade mượt về cache, không vỡ.
- **Tool chạy song song** — khi LLM xin nhiều tool/lượt, `asyncio.gather` gộp độ trễ về tool chậm nhất.

## 5. Mô hình Knowledge Graph

Schema theo **OpenMetadata** (tier/tags/owner) + quan hệ kiểu **Backstage**:

```jsonc
{
  "id": "urn:li:dataset:(...,loan_core_statement,PROD)",
  "name": "loan_core_statement",
  "entityType": "dataset",
  "tier": "Tier1",                        // Tier1=critical (P0) · Tier2 · Tier3
  "owner": {"type":"team","name":"data-engineering","slack":"#dp-lending-oncall"},
  "domain": "lending",
  "lineage": {"upstream":[...], "downstream":["dataFlow:credit-curated-etl", ...]}
}
```

- **Entity types:** `Dataset`, `Pipeline`, `KnowledgeArticle` (Confluence), `Team`, `Domain`.
- **Tier system:** Tier1 (ảnh hưởng doanh thu/người dùng) → cảnh báo P0 khi đụng vào.
- **Quan hệ có kiểu:** `OWNED_BY`, `DEPENDS_ON`, `PRODUCES`, `CONSUMES`, `PART_OF`, `LOADED_BY`.
- **BFS lineage cross-entity:** traversal đi qua ranh giới Dataset ↔ Pipeline (qua reverse-index) → impact analysis thấy được "DAG nào produce/consume bảng này", không chỉ bảng→bảng.

## 6. Pipeline truy hồi & suy luận

- **Intent routing** — phân loại 7 ý định (VI+EN regex) → tiêm routing-hint để giảm số vòng gọi tool.
- **Hybrid retrieval** — BM25 tiếng Việt (bỏ dấu + đồng nghĩa) → fuzzy fallback (difflib, chống gõ sai) → **multi-query RRF** (sinh biến thể câu hỏi, search song song, fuse theo Reciprocal Rank Fusion) → **precision rerank** tức thời (exact name-match nổi lên #1). Tất cả in-memory, không thêm độ trễ.
- **Tổng hợp** — LLM render câu trả lời + footer dẫn nguồn (suy ra từ tool đã gọi) + nhãn Trust Layer.

## 7. Bộ 16 công cụ

| Nhóm | Tools |
|------|-------|
| **Discovery** | `search_metadata` *(multi-query + live-verify)* · `get_entity_details` · `get_schema` · `get_platform_overview` |
| **Ownership & quan hệ** | `get_ownership` · `get_related_context` (Jira/Confluence/pipeline cross-links) |
| **Impact** | `analyze_impact` *(cross-entity BFS + cross-team + Mermaid)* |
| **Incident** | `diagnose_entity` *(RCA tự động: upstream culprit + smoking-gun commit + draft Jira/Slack)* |
| **Live sources** | `read_gitlab_file` · `read_confluence_page` · `search_jira_tickets` · `get_recent_commits` · `get_data_freshness` |
| **Giám sát & thời gian** | `get_platform_alerts` · `get_health_briefing` · `get_changes_since` *(temporal: schema-drift, newly-stale, recent commits)* |

## 8. Điểm nhấn kỹ thuật

- **Real-time SSE streaming** — entrypoint trả async-generator → AgentBase stream `text/event-stream`. Event `status` (định tuyến/gọi tool live) + `token` (trả lời từng chữ) + `done` (envelope đầy đủ). **First-token ~2.6s** thay vì chờ trắng ~17s.
- **Redaction guard** — scrub private-range IP/email/DB-cred khỏi output trước khi tới LLM context lẫn người dùng.
- **RCA có giới hạn** — `diagnose_entity` bọc `asyncio.wait_for` → trả partial khi timeout (từng treo >100s).
- **Multi-turn memory** — session store bounded (deque), giữ ngữ cảnh hội thoại.
- **Confidence scoring** — chấm 0–1 theo độ phủ dữ liệu của các tool đã gọi.
- **Proactive health loop** — quét sức khoẻ nền (stale Tier1 / sự cố mở / commit rủi ro).

## 9. Cài đặt & chạy

> Yêu cầu: Python 3.10+, (tuỳ chọn) Docker. Sao chép `.env.example` → `.env`, điền `LLM_API_KEY` (+ credentials nguồn dữ liệu nếu muốn live).

```bash
python -m venv venv && venv/bin/pip install -r requirements.txt
cp .env.example .env

# Cách 1 — agent + UI cùng lúc (khuyến nghị để demo LIVE)
./run_local.sh                       # → http://localhost:3000

# Cách 2 — chỉ agent
PYTHONPATH=. venv/bin/python src/main.py     # → http://localhost:8080
```

Docker:
```bash
docker build --platform linux/amd64 -t acme-dp-agent .
docker run -p 8080:8080 --env-file .env acme-dp-agent
```

## 10. API

**`POST /invocations`**
```jsonc
// request
{ "message": "loan_core_statement là gì? ai sở hữu?", "session_id": "optional", "stream": false }

// response (non-stream)
{
  "status": "success",
  "answer": "## ...markdown...",
  "tools_called": [{"tool":"search_metadata","args":{...}}],
  "confidence": 0.8,
  "freshness": {"level":"live","label":"Dữ liệu live","live_sources":["DataHub"],"verified_at":"08:55 UTC"},
  "model": "minimax/minimax-m2.5"
}
```

**Streaming** (`"stream": true`) → SSE, mỗi dòng `data: {…}`:
```
data: {"type":"status","stage":"routing","intent":"IMPACT"}
data: {"type":"status","stage":"tool","tool":"analyze_impact"}
data: {"type":"token","content":"## Kết quả..."}
data: {"type":"done","answer":"...","confidence":0.8,"freshness":{...}}
```

`GET /health` → `200`.

## 11. Kịch bản demo

1. **Discovery** — *"Bảng `loan_core_statement` là gì? Ai sở hữu? Dashboard nào dùng?"* → metadata card (tier, owner, schema, lineage) + nhãn live.
2. **Cross-team Impact** — *"Sửa cột `appid` trong `loan_core_statement` thì team nào khác bị ảnh hưởng?"* → cảnh báo Tier1 + các team thật đang phụ thuộc (Product Experience, Finance Operations, Platform Engineering…) + Mermaid blast-radius.
3. **Incident RCA** — *"Tại sao `loan_core_statement` bị chậm cập nhật?"* → culprit upstream + smoking-gun commit + draft Jira/Slack.

## 12. Live vs Cache

Agent có 2 chế độ, Trust Layer **báo trung thực**: 🟢 **live** (chạy trong mạng nội bộ + VPN → verify realtime) và 🔴 **cache** (endpoint công khai PUBLIC mode → trả lời từ knowledge graph đã ingest). Endpoint công khai hiển thị "cache" là **đúng thiết kế, không phải lỗi**. Chi tiết: [`docs/DEMO_NOTES.md`](docs/DEMO_NOTES.md).

## 13. Cấu trúc dự án

```
src/
  agents/        copilot.py — tool-calling loop, chat_stream (SSE), intent routing · prompts/
  core/          schema.py (entity model) · engine.py (graph + BFS lineage cross-entity)
  tools/         16 tools: discovery, impact, triage(RCA), freshness, temporal,
                 monitor, git_history, jira_live, viz(Mermaid), redact, semantic(BM25)
  ingestion/     DataHub / GitLab / Confluence / Jira clients (env-config, cache fallback)
  analytics/ datasets · pipelines · domains · teams · cross_team (.json metadata)
ui/              Starlette proxy + SPA — streaming, Mermaid render, Trust Layer badge
run_local.sh     chạy agent + UI local (demo LIVE)
docs/            USE_CASE · DEMO_NOTES · ROADMAP · VIDEO_SCRIPT · thumbnail
```

## 14. Roadmap

Mở rộng MVP (Data Platform domain) → **ZaloPay Knowledge Operating System** toàn công ty: vector DB persistent, ingest toàn Confluence, full cross-team lineage tự động (parse SQL/DAG), action write-back (gửi thật Jira/Slack/MR), hosted live mode (VPC). Chi tiết: [`docs/ROADMAP.md`](docs/ROADMAP.md).

## 15. Tech stack

| Lớp | Công nghệ |
|-----|-----------|
| LLM | `minimax/minimax-m2.5` qua GreenNode MaaS (OpenAI-compatible) |
| Agent | Python · OpenAI function-calling · async tool-calling loop |
| Graph/Search | In-memory typed graph · `rank_bm25` · difflib fuzzy · RRF |
| Sources | DataHub (GraphQL) · GitLab (REST) · Confluence (REST) · Jira (REST) |
| Serving | greennode-agentbase (Starlette/uvicorn) · SSE streaming · port 8080 |
| UI | Starlette proxy + SPA · marked + DOMPurify · Mermaid |
| Hạ tầng | Docker (linux/amd64) · GreenNode AgentBase Runtime |

---

<div align="center">
<sub><b>ZaloPay Data Platform AI</b> · GreenNode Claw-a-thon 2026 · Powered by MiniMax-M2.5 on GreenNode AgentBase</sub>
</div>
