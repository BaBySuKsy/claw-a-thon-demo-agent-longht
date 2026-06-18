# Acme Knowledge Platform — Phase 2 Roadmap (post-hackathon vision)

> Mục đích: phác thảo hướng mở rộng từ MVP (Data Platform domain) → **Acme Knowledge Operating System** toàn công ty. Dùng cho phần "Use case / Roadmap" trong bài dự thi + video demo. **Đây là vision, KHÔNG build trong hackathon** (scope deadline). Giám khảo đánh giá cao tầm nhìn mở rộng rõ ràng.

---

## Hiện trạng (MVP — đã LIVE, runtime v14)

- Knowledge graph in-memory ~886 entity (DataHub datasets + GitLab pipelines + Confluence DP-space + teams/domains).
- 16 tools: discovery, ownership, impact, RCA tự động (diagnose_entity), temporal (get_changes_since), freshness/Trust Layer, v.v.
- **Cross-team impact** (v14): đổi 1 bảng Data Platform → show team Risk/Fraud/Finance/Collection nào bị ảnh hưởng.
- Real SSE streaming, multi-query RRF retrieval, parallel tool dispatch.
- Giới hạn: chỉ scope **Data Platform domain**; live data nội bộ fallback cache trên prod (PUBLIC mode).

---

## Phase 2 — các hướng mở rộng (ưu tiên giảm dần)

### P2.1 — Persistent store + Vector DB (nền tảng để scale)
**Vì sao:** in-memory + JSON đủ cho ~900 entity, nhưng KHÔNG scale tới toàn-công-ty (chục nghìn doc + table). Cần DB persistent + vector index.
- **Managed DB trên GreenNode** (Postgres + pgvector, hoặc vector DB chuyên dụng). Credit dư (4.8M) → chi phí không phải rào cản; **rào cản là thời gian + data quality**.
- Migrate knowledge graph từ JSON → DB; thêm embedding cho semantic search (RAGFlow pattern đã ghi trong plan §5).
- **Lợi ích:** persistent qua restart, share giữa nhiều replica, semantic retrieval ở quy mô lớn, hỗ trợ AgentBase Memory module (long-term).

### P2.2 — Ingest TOÀN BỘ Confluence (không chỉ DP space)
**Vì sao:** mở knowledge ra mọi team → trả lời được câu hỏi xuyên phòng ban.
- Crawl toàn Confluence → chunk (semantic recursive tree đã có cho DP) → embed → vector DB.
- **Rủi ro cần xử lý:** (a) noise/độ nhiễu (nhiều page vô quan làm loãng retrieval → cần lọc theo space/label/recency); (b) **PII/secret gấp nhiều lần** → cần pipeline sanitize mạnh trước khi index + nghiêm ngặt redaction; (c) thời gian crawl + embed lớn.
- Nên làm **theo từng space ưu tiên** (Risk, Payment, Fraud...) thay vì all-at-once.

### P2.3 — Full Cross-Team Impact / Knowledge OS (mở rộng cái đã demo)
**Hiện tại (v14):** đã demo cross-team với seed thủ công (4 team consume bảng DP).
**Phase 2:** dựng lineage cross-team **tự động & toàn diện**:
- Parse SQL/DAG của MỌI team để suy ra "team X consume bảng của team Y" (dbt SQL-lineage pattern).
- Mô hình hóa: domain → team → service → dataset → dashboard xuyên toàn bộ tổ chức.
- **Use case mạnh:** "Nếu data team đổi schema bảng A → Risk mất scorecard, Fraud mù tín hiệu, Finance sai báo cáo, Collection thiếu danh sách thu hồi" — phân tích tác động liên-phòng-ban tự động, kèm danh sách team cần thông báo + Slack channel.
- Đây chính là lõi **Knowledge Operating System**: một thay đổi ở bất kỳ đâu → biết ngay blast-radius toàn công ty.

### P2.4 — Action-taking / write-back (đóng vòng agentic) — F4
**Hiện tại:** `diagnose_entity` đã sinh DRAFT Jira ticket + Slack message (chưa gửi).
**Phase 2:** gửi thật sau bước human-confirm: tạo Jira ticket (Jira REST), post Slack alert, mở GitLab MR fix DAG. → điểm mạnh nhất cho category **Agentic Assistant**.

### P2.5 — VPC mode (live data thật trên prod)
**Hiện tại:** prod PUBLIC mode → live tool fallback cache (Trust Layer báo "stale" trung thực).
**Phase 2:** deploy VPC mode để reach DataHub/GitLab/Jira nội bộ → badge "live" thật.
- **Cần:** (1) IAM có quyền quản lý network (hiện **403** — cần admin cấp), (2) VPC+subnet có **peering/VPN tới mạng corporate Acme** (hạ tầng team network). Lệnh deploy đã sẵn trong `Deploy_Runbook.md §5b`.

---

## Tại sao KHÔNG làm Phase 2 trong hackathon
- **Constraint là THỜI GIAN (deadline 17/06), không phải credit.** Re-architect (DB/all-Confluence/full-lineage) là việc nhiều tuần.
- Agent MVP đã LIVE, ổn định, demo tốt. Build dở dang Phase 2 = rủi ro phá cái đang chạy + trượt deadline.
- 3 deliverable bắt buộc (GitHub public, video, use-case) là ưu tiên #1 để bài hợp lệ.

*Tạo 2026-06-15 (night). Vision tham chiếu §1 của `Acme_Knowledge_Platform_Plan.md`.*
