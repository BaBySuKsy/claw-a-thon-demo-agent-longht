# Kịch bản Demo Video (2–3 phút) — Acme Data Platform AI

> Mục tiêu: 2:30–2:50. Quay ở **LIVE mode** (`./run_local.sh` + VPN → badge 🟢) để show năng lực realtime.
> Format gợi ý: YouTube Unlisted hoặc OneDrive. Quay màn hình + voiceover (hoặc phụ đề).
> Chuẩn bị: chạy `./run_local.sh`, mở `http://localhost:3000`, xác nhận badge 🟢 trước khi quay.

> **Triết lý demo:** **3 case sâu để gây ấn tượng** (Discovery / Cross-team / RCA), còn **bề rộng** (16 tool: onboarding, temporal, health briefing, commits…) thì để **sidebar + closing line + README chứng minh**. Combo này mạnh hơn nhồi 5 case hời hợt — mỗi case được "thở", giám khảo nhớ được, mà vẫn thấy agent làm được ~10 việc.

---

## Cảnh 0 — Mở đầu (0:00–0:20) · ~40 từ

**Hình:** logo Acme + tiêu đề "Acme Data Platform AI".

**Voiceover:**
> "Tại Acme, metadata nằm rải rác ở DataHub, GitLab, Confluence, Jira. Một câu hỏi đơn giản 'bảng này là gì, ai dùng' tốn 30 phút. Đây là AI agent biến nền tảng dữ liệu thành một knowledge graph hỏi-đáp được bằng tiếng Việt."

---

## Cảnh 1 — Data Discovery (0:20–0:55) · điểm: tốc độ + Trust Layer + bề rộng

**Trước khi gõ (2-3s):** lia chuột qua **sidebar "Agent Functions"** cho thấy danh sách 16 tool → người xem cảm nhận quy mô ngay từ đầu (đây là cách "khoe bề rộng" không tốn scene riêng).

**Gõ:** `Bảng loan_core_statement là gì? Ai sở hữu và dashboard nào dùng nó?`

**Chỉ vào (khi đang chạy):**
- **Thinking pill động** morph theo bước: 🧭 *Đang định tuyến* → 🔍 *Đang tìm metadata* (kính lúp lắc) → ✍️ *Đang viết câu trả lời* (bút) — agent "suy nghĩ" realtime, rất bắt mắt.
- Câu trả lời stream từng chữ: entity card (tier 🔴 Tier1, owner, domain), schema, lineage.
- **Badge 🟢 "Dữ liệu live"** + chips nguồn (DataHub, Knowledge Graph).

**Voiceover:**
> "Hỏi một câu, agent gọi đúng công cụ và trả về thẻ metadata đầy đủ trong vài giây — kèm nhãn xanh xác nhận dữ liệu được verify realtime từ DataHub."

---

## Cảnh 2 — Cross-team Impact (0:55–1:45) · ⭐ điểm nhấn

**Gõ:** `Nếu tôi sửa cột appid trong loan_core_statement thì những team nào khác bị ảnh hưởng?`

**Chỉ vào:**
- Cảnh báo **🚨 CROSS-TEAM IMPACT**: các team khác đang phụ thuộc dữ liệu này — Product Experience, Finance Operations, Platform Engineering, Growth Products (suy ra từ bằng chứng tham chiếu thật trong Confluence).
- Cảnh báo Tier1 + số lượng entity downstream (14).
- **Sơ đồ Mermaid blast-radius** render: statement → credit-curated-etl → marts → các bảng cross-team (tô đỏ Tier1).

**Voiceover:**
> "Đây là điểm khác biệt: không chỉ liệt kê bảng downstream, agent chỉ ra một thay đổi ở team Data sẽ ảnh hưởng tới hàng loạt team khác đang dùng dữ liệu này — Product Experience, Finance Operations, Platform Engineering — và những team này được suy ra từ chính tài liệu Confluence thật, kèm sơ đồ tác động. Đây chính là tư duy Knowledge Operating System: một thay đổi, thấy ngay blast-radius toàn công ty."

---

## Cảnh 3 — Autonomous Incident RCA (1:45–2:30) · điểm: agentic

**Gõ:** `Tại sao bảng loan_core_statement bị chậm cập nhật?`

**Chỉ vào:**
- Verdict badge (🔴/🟡) + **root cause đi ngược upstream** (không chỉ triệu chứng).
- **Smoking-gun commit** (commit nghi ngờ + diff).
- **Draft Jira ticket + Slack message** đã soạn sẵn (chỉ chờ gửi).
- Footer nguồn: DataHub + GitLab + Jira.

**Voiceover:**
> "Khi có sự cố, agent tự điều tra: đi ngược lineage tìm nguyên nhân gốc thật, lấy đúng commit gây lỗi, và soạn sẵn ticket Jira cùng cảnh báo Slack. Kỹ sư chỉ việc xác nhận và gửi."

---

## Cảnh 4 — Kết (2:30–2:50) · ~35 từ

**Hình:** sidebar tool catalog (16 tools) + dòng "Deployed live on GreenNode AgentBase".

**Voiceover:**
> "16 công cụ, knowledge graph 886 entity, streaming realtime, deploy live trên GreenNode AgentBase với MiniMax-M2.5. Từ Data Platform hôm nay đến Knowledge Operating System cho toàn Acme. Xin cảm ơn."

---

## Mẹo quay
- **Trước khi quay:** chạy mỗi câu hỏi 1 lần để cache LLM ấm + xác nhận badge 🟢 (tránh "stale" giữa video).
- **Lia sidebar "Agent Functions" (16 tool) ở Cảnh 1** — cách khoe bề rộng agent mà không tốn scene; ở closing nhắc lại "16 công cụ".
- Phóng to khung chat; ẩn bookmark bar cho gọn.
- Nếu 1 câu chạy lâu, cứ để streaming + thinking pill chạy — nó cho thấy agent "suy nghĩ" (điểm cộng), hoặc cắt dựng nhẹ.
- Giữ đúng **3 case sâu** (đừng nhồi thêm → quá 3 phút, mỗi case bị hời hợt).
- Nói rõ "dữ liệu live verify realtime" khi chỉ vào badge 🟢 — đây là điểm tin cậy.

---

## 🎥 Quay bằng tool nào? (macOS)

| Tool | Giá | Khi nào dùng |
|------|-----|--------------|
| **QuickTime Player** | Free (sẵn macOS) | Nhanh gọn: `Cmd+Shift+5` → quay màn hình + mic. Đủ để nộp. |
| **OBS Studio** | Free | Cần overlay webcam/logo, nhiều scene, kiểm soát hơn. |
| **Screen Studio** | ~$89 | Đẹp nhất: tự zoom theo chuột, con trỏ mượt — kiểu "product demo". Nếu muốn ăn điểm hình ảnh. |

→ **Gợi ý:** QuickTime (đơn giản) hoặc Screen Studio (đẹp). Quay 1080p, khung trình duyệt to.

## 💬 Thêm phụ đề theo kịch bản (đã có sẵn file SRT)

T đã tạo sẵn **`docs/subtitles.srt`** — đúng lời thoại kịch bản này, đã canh giờ theo từng cảnh (bạn chỉ cần tinh chỉnh lại cho khớp recording thực tế).

**Cách 1 — CapCut (free, dễ nhất, hỗ trợ tiếng Việt):**
1. Kéo video vào CapCut.
2. **Captions → Import caption → chọn `docs/subtitles.srt`** (hoặc **Auto captions** nếu bạn đọc voiceover → CapCut tự nhận tiếng Việt).
3. Chỉnh font/vị trí → **Export** (phụ đề được burn vào video).

**Cách 2 — DaVinci Resolve (free, chuyên nghiệp):**
- Tab Edit → menu phụ đề → **Import Subtitle → subtitles.srt** → kéo vào subtitle track → chỉnh style → Deliver (render kèm phụ đề).

**Cách 3 — ffmpeg (1 lệnh, burn cứng, nhanh nhất nếu đã có SRT khớp giờ):**
```bash
ffmpeg -i demo.mp4 \
  -vf "subtitles=docs/subtitles.srt:force_style='FontName=Arial,FontSize=20,OutlineColour=&H80000000,BorderStyle=3'" \
  -c:a copy demo_subbed.mp4
```

**Lưu ý canh giờ:** mốc thời gian trong `subtitles.srt` dựa trên kịch bản (2:50). Sau khi quay xong, thời lượng thực tế sẽ lệch chút — mở SRT/CapCut kéo lại cho khớp là xong (5 phút).

**Workflow khuyến nghị:** Quay (QuickTime) → đọc voiceover theo kịch bản → CapCut **Auto captions** (tự transcribe tiếng Việt, khớp đúng lời nói) → chỉnh nhẹ → export. Nếu KHÔNG voiceover → dùng `subtitles.srt` import + canh lại giờ.
