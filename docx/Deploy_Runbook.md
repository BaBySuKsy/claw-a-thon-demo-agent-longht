# Acme DP Agent — Deploy Runbook

> Quy trình deploy ĐÚNG cho `acme-dp-agent` trên GreenNode AgentBase, + mọi lỗi đã gặp và cách fix.
> Mục tiêu: lần sau làm theo là chạy, không dò lại.

## 0. TL;DR — deploy 1 phát

```bash
# từ thư mục project, sau khi đã sửa code
TAG="v$(date +%Y%m%d%H%M%S)"
IMG="vcr.vngcloud.vn/111480-abp111921/acme-dp-agent:$TAG"

# 1) build amd64 (sạch, không attestation)
docker build --platform linux/amd64 --provenance=false --sbom=false -t "$IMG" .

# 2) login CR (1 lần/máy — dùng IAM, không cần gõ user/pass)
bash agentbase-skills/.claude/skills/agentbase/scripts/cr.sh credentials docker-login

# 3) push
docker push "$IMG"

# 4) deploy (DÙNG runtime.sh + --from-cr — KHÔNG dùng `greennode deploy update`)
bash agentbase-skills/.claude/skills/agentbase/scripts/runtime.sh update \
  runtime-2f0821f2-4dfc-4ab3-9d90-353a9654e97d \
  --image "$IMG" --flavor runtime-s2-general-4x8 --env-file .env --from-cr
```

Sau đó **poll tới khi ACTIVE** + verify (mục 4). DEFAULT endpoint tự trỏ sang version mới.

---

## 1. Điểm mấu chốt (đọc kỹ — đây là chỗ hay sai)

- **Công cụ deploy ĐÚNG là `runtime.sh ... --from-cr`** (trong `agentbase-skills/.claude/skills/agentbase/scripts/`), KHÔNG phải `greennode deploy update`.
  - `--from-cr` dùng **IAM Client ID + Secret** (trong `.greennode.json`) để **tự lấy credentials registry từ CR API** và nhúng vào `imageAuth`. → **KHÔNG cần `registry_url/username/password`.**
  - `greennode deploy update` (CLI pip) lại **bắt buộc** `GREENNODE_REGISTRY_URL/USERNAME/PASSWORD` → đó là lý do nó báo "Missing required items". **Đừng dùng lệnh này.**
- **Creds cần có (đủ rồi):** chỉ `.greennode.json` chứa `client_id` + `client_secret` (IAM). Đó là tất cả. Registry creds là **thừa** với `--from-cr`.
- **Docker login vào `vcr.vngcloud.vn`**: chỉ cần cho bước **push** (đẩy image lên). Không liên quan tới việc runtime *pull* image (cái đó dùng `imageAuth` từ `--from-cr`).
- **Build phải `--platform linux/amd64`** (runtime chạy amd64; máy Mac là arm64). Nên thêm `--provenance=false --sbom=false` cho ra 1 manifest sạch.
- **Image phải listen port 8080** và có `GET /health` trả 200 (Dockerfile đã đúng).

---

## 2. Giá trị tham chiếu (cố định)

| Thứ | Giá trị |
|-----|---------|
| Runtime ID | `runtime-2f0821f2-4dfc-4ab3-9d90-353a9654e97d` |
| Runtime name | `acme-dp-agent` |
| Endpoint ID (DEFAULT) | `endpoint-8b483005-086d-43c9-a704-101e13eb6a3d` |
| Endpoint URL | `https://endpoint-8b483005-086d-43c9-a704-101e13eb6a3d.agentbase-runtime.aiplatform.vngcloud.vn` |
| Registry repo path | `vcr.vngcloud.vn/111480-abp111921/acme-dp-agent` |
| Flavor | `runtime-s2-general-4x8` (4 CPU / 8GB) |
| Last known-good image | `v20260617b` (= runtime **version 16**, ACTIVE — serves web chat UI at `GET /` so endpoint is browser-accessible; deployed 2026-06-17 deadline-day) |
| Console | https://aiplatform.console.vngcloud.vn/agent-runtime?tab=runtime |

---

## 3. Các bước chi tiết

### B1. Verify IAM creds
```bash
bash agentbase-skills/.claude/skills/agentbase/scripts/check_credentials.sh iam
# → "OK: IAM credentials found in .greennode.json"
```

### B2. (Khuyến nghị) Test image LOCAL trước khi deploy
Tránh đẩy image hỏng lên prod:
```bash
docker build --platform linux/amd64 --provenance=false --sbom=false -t dp-test:local .
docker run -d --name dptest --platform linux/amd64 -p 8091:8080 \
  --env-file .env -v "$PWD/.greennode.json:/app/.greennode.json:ro" dp-test:local
sleep 8
curl -s -o /dev/null -w "health=%{http_code}\n" http://localhost:8091/health   # mong đợi 200
curl -s -X POST http://localhost:8091/invocations -H "Content-Type: application/json" \
  -d '{"message":"Tìm bảng lending"}' | python3 -c "import sys,json;print('freshness:',json.load(sys.stdin).get('freshness'))"
docker rm -f dptest
```
Nếu local OK mà platform vẫn ERROR → lỗi platform (xem mục 5).

### B3. Build + push (xem TL;DR mục 0)

### B4. Deploy bằng runtime.sh --from-cr
```bash
bash agentbase-skills/.claude/skills/agentbase/scripts/runtime.sh update \
  runtime-2f0821f2-4dfc-4ab3-9d90-353a9654e97d \
  --image "$IMG" --flavor runtime-s2-general-4x8 --env-file .env --from-cr
```
Lệnh tạo runtime version mới; DEFAULT endpoint auto-trỏ sang nó.

---

## 4. Verify sau deploy

```bash
RID="runtime-2f0821f2-4dfc-4ab3-9d90-353a9654e97d"
EP="https://endpoint-8b483005-086d-43c9-a704-101e13eb6a3d.agentbase-runtime.aiplatform.vngcloud.vn"

# Poll status tới ACTIVE (rollout ~1-2 phút, pod cũ phục vụ trong lúc swap)
bash agentbase-skills/.claude/skills/agentbase/scripts/runtime.sh get $RID | grep status

# Health
curl -s -o /dev/null -w "%{http_code}\n" "$EP/health"   # 200

# Xác nhận ĐÚNG version mới đang chạy (vd marker của v10+: field "freshness")
curl -s -X POST "$EP/invocations" -H "Content-Type: application/json" \
  -d '{"message":"hi"}' | python3 -c "import sys,json;print(json.load(sys.stdin).get('freshness'))"
# None = pod cũ còn phục vụ (chưa swap xong / version mới ERROR); có dict = version mới đã live
```

> ⚠️ **Log chỉ trả của pod ĐANG active.** Nếu version mới ERROR, không xem được log của nó qua CLI — phải vào **console**.

---

## 5. Troubleshooting (lỗi thật đã gặp ngày 2026-06-14)

| Triệu chứng | Nguyên nhân | Cách xử lý |
|-------------|-------------|-----------|
| `Missing required items: GREENNODE_REGISTRY_URL/USERNAME/PASSWORD` | Dùng **nhầm** `greennode deploy update` (CLI pip) — lệnh này đòi registry env vars | Dùng `runtime.sh update ... --from-cr` (nó dùng IAM, không cần registry creds) |
| `HTTP 400: imageAuth cannot be null` (khi dùng `runtime.sh patch` hoặc `greennode runtime patch`) | `patch` không set được `imageAuth` cho private registry | Dùng `runtime.sh update ... --from-cr` (tự nhúng imageAuth từ IAM) |
| `flavorId Field required` (greennode runtime patch) | thiếu file cấu hình `.greennode_runtime.json` / không truyền `--flavor-id` | Dùng `runtime.sh update --flavor runtime-s2-general-4x8 ...` |
| Status **ERROR** dù pod chạy được (log có `Engine ready`, serve query OK) | **NGUYÊN NHÂN ĐÃ XÁC NHẬN (2026-06-15):** build kiểu mặc định của buildx tạo **OCI image index + attestation manifest** (multi-part) → platform pull/dựng pod chậm hơn → **rớt cửa sổ health-probe lúc rollout** → gắn nhãn ERROR (dù app vẫn lên & serve). | **FIX:** build **image phẳng** = thêm `--provenance=false --sbom=false` vào `docker build` (cho ra 1 manifest đơn, pull nhanh). Đã có sẵn trong lệnh ở mục 0. Kèm theo: startup health-check đã được **dời 45s** (`main.py:_alert_loop`) để probe readiness chạy sạch. → version 12 lên **ACTIVE** ngay. |
| Status ERROR + **không log, không event** (pod không lên hẳn) | Có thể capacity/quota (rolling update cần 2 pod 4CPU/8GB) | Endpoint live tự fail-over giữ version cũ (demo không sập). Mở **console → version lỗi → Status Reason** (CLI giấu). Thử deploy lại với image phẳng (fix ở trên). |
| Build ra image arm64 → pod crash | Quên `--platform linux/amd64` (máy Mac arm64) | Build lại với `--platform linux/amd64` |
| Push "unauthorized/denied" | Chưa login CR / secret đã rotate | `bash .../cr.sh credentials docker-login` |

---

## 5b. VPC mode (live internal data trên prod) — ĐIỀU TRA 2026-06-15, hiện BLOCKED

**Mục tiêu:** chuyển runtime từ PUBLIC → VPC để prod reach được `datahub.acme.vn` / `gitlab.acme.vn` / `jira.acme.vn` (live thật, badge xanh thay vì "stale" cache).

**`runtime.sh update` ĐÃ hỗ trợ VPC:**
```bash
bash agentbase-skills/.claude/skills/agentbase/scripts/runtime.sh update \
  runtime-2f0821f2-4dfc-4ab3-9d90-353a9654e97d \
  --image <IMG> --flavor runtime-s2-general-4x8 --env-file .env --from-cr \
  --network-mode VPC --vpc-id <VPC_ID> --subnet-id <SUBNET_ID> \
  --route-cidrs <internal CIDRs, vd 10.0.0.0/8>
```
Lấy `vpcId`/`subnetId`: `vserver.sh projects` → `vserver.sh vpcs <project>` → `vserver.sh subnets <project> <vpc>`.

**BLOCKER hiện tại (2 cái):**
1. **IAM 403** — `vserver.sh vpcs pro-9332a571-203d-47ce-838e-69154039e798` trả **HTTP 403**: IAM user (client_id `a17b22b3...`) **không có quyền quản lý network/VPC**. → cần BTC/admin cấp quyền hoặc tạo VPC sẵn rồi đưa `vpcId+subnetId`.
2. **Routing nội bộ** — kể cả có VPC cloud, nó **không tự reach `*.acme.vn` nội bộ** trừ khi có **peering/VPN** giữa VPC GreenNode và mạng corporate Acme. Đây là hạ tầng cần team network, không tự làm được.

**Khuyến nghị:** với cuộc thi, **KHÔNG ưu tiên VPC** — agent cached-mode chạy tốt, Trust Layer báo "stale" trung thực. VPC chỉ đổi badge "stale"→"live" nhưng tốn hạ tầng + rủi ro. Để Phase 2 (xem `docx/Phase2_Roadmap.md`).

## 6. Rollback (về version cũ đang chạy tốt)

DEFAULT endpoint **không** update trực tiếp được — rollback bằng cách deploy lại image cũ:
```bash
bash agentbase-skills/.claude/skills/agentbase/scripts/runtime.sh update \
  runtime-2f0821f2-4dfc-4ab3-9d90-353a9654e97d \
  --image vcr.vngcloud.vn/111480-abp111921/acme-dp-agent:v20260613i \
  --flavor runtime-s2-general-4x8 --env-file .env --from-cr
```
(`v20260613i` = version 9, bản tốt gần nhất.)

---

## 7. Logs & debug khi cần

```bash
RID="runtime-2f0821f2-4dfc-4ab3-9d90-353a9654e97d"
EID="endpoint-8b483005-086d-43c9-a704-101e13eb6a3d"
# log ứng dụng (chỉ pod đang active)
bash agentbase-skills/.claude/skills/agentbase/scripts/runtime.sh logs $RID --from 0 --limit 100
# event hạ tầng (image-pull/OOM/schedule/health-probe) — chỗ đầu tiên khi pod không ACTIVE
bash agentbase-skills/.claude/skills/agentbase/scripts/runtime.sh endpoints events $RID $EID
# versions (xem image + flavor từng version)
bash agentbase-skills/.claude/skills/agentbase/scripts/runtime.sh versions $RID
```

> Nếu `events` rỗng + `logs` chỉ có pod cũ + image test local OK → gần như chắc chắn vấn đề capacity/schedule phía platform → **console** là nơi duy nhất thấy lý do.

---

---

## 8. Bài học phiên 2026-06-15 (đã giải quyết)

- **Triệu chứng:** deploy F1/F2/F3 (16 tools) → runtime version 10 & 11 đều **ERROR** dù pod chạy được (log `Engine ready`, serve query OK), live tự fail-over giữ v9.
- **Sai lầm ban đầu:** dùng `greennode deploy update` (đòi `GREENNODE_REGISTRY_*`) thay vì `runtime.sh --from-cr` (chỉ cần IAM). Đã sửa.
- **Nguyên nhân thật của ERROR:** image build mặc định = **OCI index + attestation manifest** → platform pull chậm → rớt health-probe rollout → ERROR.
- **Cách fix (THÀNH CÔNG):** build `--provenance=false --sbom=false` (image phẳng) + dời startup health-check 45s → **version 12 (image `v20260615a`) lên ACTIVE xanh, serve đủ 3 feature.**
- **Lưu ý prod:** runtime ở **PUBLIC mode** → KHÔNG reach được DataHub/GitLab/Jira nội bộ (`Failed to resolve datahub.acme.vn`). Các tính năng live (badge xanh, smoking-gun commit, schema-drift) **fallback cache** trên prod; muốn live thật phải deploy **VPC mode** (cần vpcId + subnetId). Trust Layer báo trung thực "stale" khi không verify được — đúng thiết kế.

*Tạo 2026-06-15. Trạng thái cuối: **version 12 (image `v20260615a`) — ACTIVE, live, 3 feature mới chạy.** F1 Trust Layer + F2 Autonomous RCA + F3 Temporal, 16 tools.*
