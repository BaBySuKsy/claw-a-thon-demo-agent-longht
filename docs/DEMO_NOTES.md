# Demo Notes — Live vs Cache (đọc trước khi chấm / Read before evaluating)

> Note ngắn để BTC/người dùng không thắc mắc khi badge dữ liệu hiện "cache" trên endpoint công khai.
> Short note so the BOC/users aren't confused when the data badge shows "cache" on the public endpoint.

---

## 🇻🇳 Tiếng Việt

**Agent có 2 chế độ dữ liệu, và Trust Layer hiển thị TRUNG THỰC chế độ đang dùng:**

| Chế độ | Khi nào | Badge | Ý nghĩa |
|--------|---------|-------|---------|
| 🟢 **Live** | Agent chạy **trong mạng Acme** (có VPN) | "Dữ liệu live" | Verify realtime với DataHub/GitLab/Jira nội bộ |
| 🔴 **Cache** | Agent chạy trên **endpoint công khai** (cloud, PUBLIC mode) | "Cache — nguồn live không phản hồi" | Trả lời từ knowledge graph đã ingest sẵn |

**Vì sao endpoint công khai (link BTC trải nghiệm) hiển thị "cache":**
Các nguồn dữ liệu (DataHub, GitLab, Jira của Acme) là **nội bộ** (host nội bộ → IP private RFC1918), **chỉ truy cập được trong mạng công ty / qua VPN**. Endpoint công khai chạy ở GreenNode Cloud (PUBLIC mode) **không nằm trong mạng nội bộ** → không reach được nguồn live → agent **chủ động fallback** về knowledge graph đã ingest và **báo trung thực** "cache". Đây **KHÔNG phải lỗi** — đây là thiết kế Trust Layer: không bao giờ giả vờ dữ liệu là realtime khi nó không phải.

**Video demo được quay ở chế độ LIVE** (agent chạy trong mạng Acme) để thể hiện đầy đủ năng lực verify realtime (freshness, smoking-gun commit, schema-drift). Khi BTC dùng link công khai, chất lượng câu trả lời **vẫn nguyên vẹn** (knowledge graph ~886 entity đã ingest từ chính các nguồn đó) — chỉ khác là dữ liệu thời điểm verify được lấy từ snapshot thay vì realtime.

**Để bật Live thật:** deploy VPC mode (cần quyền IAM network + peering tới mạng corporate — xem `Deploy_Runbook.md §5b`).

---

## 🇬🇧 English

**The agent has two data modes; the Trust Layer HONESTLY shows which one is active:**

| Mode | When | Badge | Meaning |
|------|------|-------|---------|
| 🟢 **Live** | Agent runs **inside the Acme network** (VPN) | "Live data" | Real-time verification against internal DataHub/GitLab/Jira |
| 🔴 **Cache** | Agent runs on the **public endpoint** (cloud, PUBLIC mode) | "Cache — live source unreachable" | Answers from the pre-ingested knowledge graph |

**Why the public endpoint shows "cache":**
The data sources (the internal DataHub/GitLab/Jira) are **internal** (an internal host → a private RFC1918 IP), reachable **only from inside the corporate network / via VPN**. The public endpoint runs on GreenNode Cloud (PUBLIC mode), which is **outside** that network, so it cannot reach the live sources. The agent **deliberately falls back** to the ingested knowledge graph and **honestly reports** "cache". This is **not a bug** — it is the Trust Layer design: never pretend data is real-time when it isn't.

**The demo video is recorded in LIVE mode** (agent running inside the Acme network) to show the full real-time verification capability (freshness, smoking-gun commit diff, schema-drift). On the public link, **answer quality is unchanged** (the ~886-entity knowledge graph was ingested from those same sources) — only the verification timestamp comes from a snapshot rather than real-time.

**To enable true Live on a hosted endpoint:** deploy in VPC mode (requires IAM network permission + peering to the corporate network).

---

*Cập nhật / Updated: 2026-06-16. Liên quan: `run_local.sh` (chạy local để demo LIVE).*
