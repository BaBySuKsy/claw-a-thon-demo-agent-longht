# Use Case Description (Tiếng Việt, ~260 từ)

> Dán bản dưới đây vào form submit (yêu cầu: dưới 300 từ).

---

**Acme Data Platform AI** giải quyết bài toán kiến thức phân mảnh trong nền tảng dữ liệu. Tại Acme, metadata nằm rải rác ở DataHub, GitLab, Confluence và Jira; một kỹ sư mất trung bình 30 phút chỉ để trả lời "bảng này là gì, ai sở hữu, ai đang dùng", còn việc phân tích tác động khi đổi schema lại làm thủ công nên dễ sót và gây sự cố P0.

Chúng tôi xây một AI agent đặt trên một **knowledge graph metadata hợp nhất** (~886 entity, chuẩn OpenMetadata/Backstage). Người dùng hỏi bằng tiếng Việt hoặc Anh; agent phân loại ý định, gọi đúng công cụ trong bộ 16 tools, và trả lời có dẫn nguồn kèm nhãn độ tin cậy, hỗ trợ streaming realtime.

Ba năng lực tạo khác biệt: (1) **Phân tích tác động xuyên team** — đổi một bảng Data Platform, agent chỉ ra ngay các team khác đang phụ thuộc dữ liệu đó (Product Experience, Finance Operations, Platform Engineering — suy ra từ Confluence thật) kèm sơ đồ blast-radius; (2) **Điều tra sự cố tự động** — agent đi ngược lineage tìm nguyên nhân gốc thật, lấy đúng commit gây lỗi, và soạn sẵn ticket Jira cùng cảnh báo Slack; (3) **Trust Layer** — mỗi câu trả lời gắn nhãn dữ liệu live hay cache, không bao giờ giả vờ realtime.

Giá trị: giảm thời gian tra cứu từ 30 phút xuống dưới 1 phút, biến phân tích tác động thủ-công-dễ-sai thành tự động và an toàn, rút ngắn thời gian xử lý sự cố. Agent đã deploy live trên GreenNode AgentBase (MiniMax-M2.5) với giao diện web streaming. Đây là bước đầu hướng tới một **Knowledge Operating System** cho toàn Acme.
