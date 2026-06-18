# Roadmap — từ MVP đến Acme Knowledge Operating System

> Tầm nhìn mở rộng sau hackathon. MVP hiện tại scope **Data Platform domain**; hướng tới một **Knowledge OS** cho toàn Acme.

## Hiện trạng (MVP — đã LIVE)
- Knowledge graph in-memory ~886 entity (DataHub datasets + GitLab pipelines + Confluence + teams/domains).
- 16 tools: discovery, ownership, impact (cross-entity + **cross-team**), autonomous RCA, temporal, freshness/Trust Layer.
- Real-time SSE streaming, multi-query RRF retrieval, parallel tool dispatch.

## Phase 2 (ưu tiên giảm dần)

**P2.1 — Persistent store + Vector DB.** In-memory/JSON đủ cho ~900 entity nhưng không scale tới toàn công ty. Migrate sang DB persistent + pgvector/vector DB cho semantic search quy mô lớn; bật long-term memory.

**P2.2 — Ingest toàn bộ Confluence (mọi team).** Crawl → chunk → embed → vector DB, để trả lời câu hỏi xuyên phòng ban. Cần xử lý: lọc nhiễu theo space/recency, pipeline sanitize PII mạnh, làm theo từng space ưu tiên.

**P2.3 — Full cross-team lineage (tự động).** Hiện cross-team impact dùng seed thủ công. Phase 2: parse SQL/DAG của mọi team để suy ra lineage liên-phòng-ban tự động → "một thay đổi bất kỳ → blast-radius toàn công ty".

**P2.4 — Action write-back (đóng vòng agentic).** `diagnose_entity` đã sinh draft Jira/Slack. Phase 2: gửi thật sau bước human-confirm (Jira REST, Slack, GitLab MR).

**P2.5 — Hosted live mode (VPC).** Endpoint công khai hiện PUBLIC → cache. Deploy VPC + peering tới mạng nội bộ để verify realtime trên endpoint hosted.

## Vì sao không làm Phase 2 trong hackathon
Constraint là **thời gian**, không phải chi phí. Re-architect là việc nhiều tuần; MVP đã live và ổn định. Ưu tiên: deliverable bắt buộc + một demo vững.
