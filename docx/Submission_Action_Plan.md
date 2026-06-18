# 🚀 Submission Action Plan — Claw-a-thon 2026

> **DEADLINE: 17/06/2026, 12:00 PM (GMT+7).** Làm theo thứ tự dưới. Mục P0 là bắt buộc để bài hợp lệ.
> Team: **AITree** · Track: **Data Analysis + Agentic Assistant** · Use-case: `docs/USE_CASE.md`

---

## ⏱️ Thứ tự đề xuất (tổng ~60-75 phút)

### ☑ B1 — Redeploy prod v15 ✅ DONE (2026-06-17) — endpoint đã KHỚP video/README
**Đã xong:** runtime **version 15** (image `v20260617a`, digest `sha256:ada0d30…`) ACTIVE. Verified live: `analyze_impact` lending core → cross_team_count=4 với team THẬT **Platform Engineering / Finance Operations / Growth Products / Product Experience** (không còn seed Risk/Fraud/Finance/Collection). `freshness:cached` đúng cho prod PUBLIC mode.
**Vì sao (lý do ban đầu):** prod trước là **v14** (cross-team còn SEED, chưa có GitLab-fix/UI mới). Video + README show **team THẬT**. Đã deploy v15 cho đồng bộ.
```bash
cd /Users/lap14489/Documents/claw-a-thon-demo-agent-longht
TAG="v20260617a"; IMG="vcr.vngcloud.vn/111480-abp111921/acme-dp-agent:$TAG"
docker build --platform linux/amd64 --provenance=false --sbom=false -t "$IMG" .
bash agentbase-skills/.claude/skills/agentbase/scripts/cr.sh credentials docker-login
docker push "$IMG"
bash agentbase-skills/.claude/skills/agentbase/scripts/runtime.sh update \
  runtime-2f0821f2-4dfc-4ab3-9d90-353a9654e97d \
  --image "$IMG" --flavor runtime-s2-general-4x8 --env-file .env --from-cr
# poll tới ACTIVE + verify cross_team_count (xem Deploy_Runbook.md §4)
```
*(Nếu quá gấp giờ → có thể bỏ qua, nhưng nên làm. Endpoint v14 vẫn chạy, chỉ là cross-team là seed.)*

### ☑ B2 — Publish GitHub repo PUBLIC ✅ DONE (2026-06-17)
**Đã xong:** push commit orphan SẠCH `2984b89` → `main` (--force), repo đã **Public** (verify ẩn danh: repo page 200, raw README 200).
**⚠️ Bắt được PII trước khi push:** `datasets.json` chứa **95 handle nhân viên thật** (owner type:user, 553 lượt) — đã redact → `data-platform-team`. Làm phẳng thành 1 commit orphan (history cũ chứa handle KHÔNG được push). Final scan: 0 handle/secret/hostname/email/IP. README team → AITree, subtitles.srt synced.
- Repo: `https://github.com/BaBySuKsy/claw-a-thon-demo-agent-longht` (Public, default branch `main`).

### ☐ B3 — Quay + upload video demo (BẮT BUỘC) — ~30-45'
```bash
./run_local.sh          # BẬT VPN trước → đợi "Trust Layer: 🟢 live"
```
- Mở `http://localhost:3000`, quay theo **`docs/VIDEO_SCRIPT.md`** — 3 case: Discovery → Cross-team → RCA (2:30–2:50).
- Mẹo: lia sidebar 16 tool ở Cảnh 1; để thinking pill 🧭→🔍→✍️ chạy.
- Burn phụ đề: `docs/subtitles.srt` (CapCut import / hoặc `ffmpeg -i demo.mp4 -vf "subtitles=docs/subtitles.srt" -c:a copy out.mp4`).
- Upload **YouTube Unlisted** hoặc **OneDrive** → đảm bảo link **public/accessible**.

### ☐ B4 — Điền form submit (BẮT BUỘC) — ~10'
Form: https://greennode.ai/events/greennode-claw-a-thon
- ☐ GitHub repo link (đã Public)
- ☐ Video demo link (Unlisted/OneDrive, mở được)
- ☐ Endpoint: `https://endpoint-8b483005-086d-43c9-a704-101e13eb6a3d.agentbase-runtime.aiplatform.vngcloud.vn` (v16 — **mở bằng browser ra trang chat**, đã verify GET / → 200; giám khảo chat trực tiếp, ẩn danh OK)
- ☐ Use-case: paste từ `docs/USE_CASE.md` (bản VN, <300 từ)
- ☐ Thumbnail: upload `docs/thumbnail.png`
- ☐ Tên team: **AITree**
- ☐ Track: **Data Analysis** (+ Agentic Assistant nếu form cho chọn nhiều)

### ☐ B5 — SUBMIT trước 12:00 ✅
(Form cho sửa sau khi nộp tới deadline — nộp sớm rồi tinh chỉnh còn hơn lỡ giờ.)

---

## 🔒 Sau khi nộp (post-submission)
- ☐ **Rotate GitHub PAT** (token đang nhúng trong `.git/config` — đổi token mới cho an toàn).
- ☐ (Tuỳ) Tắt `run_local.sh` (Ctrl+C) để giải phóng port.

---

## 📌 Ghi chú nhanh
- **Demo LIVE** chỉ chạy local + VPN (prod PUBLIC = cache, có note `docs/DEMO_NOTES.md` giải thích cho BTC — không phải lỗi).
- Nếu BTC hỏi sao endpoint ra "cache" → chỉ họ `docs/DEMO_NOTES.md`.
- Branch nguồn sạch để push = **`public-submission`** (KHÔNG push `feat/integrate-agentbase-skills` — history còn data nhạy cảm ở commit cũ).
- Mọi tài liệu đã đồng bộ: README / USE_CASE / VIDEO_SCRIPT / subtitles / thumbnail / DEMO_NOTES / ROADMAP.

*Tạo 2026-06-17 (deadline day).*
