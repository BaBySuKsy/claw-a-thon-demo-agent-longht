#!/usr/bin/env bash
# run_local.sh — chạy AGENT + UI ở LOCAL bằng 1 lệnh, để demo/quay video với DATA LIVE 🟢
#
# Vì sao cần local: agent local dùng VPN của máy bạn → reach được DataHub/GitLab/Jira
# nội bộ (DataHub/GitLab/Jira) → Trust Layer hiện badge "live". Endpoint PROD chạy
# PUBLIC mode (không VPN) nên luôn fallback cache ("stale") — xem docs/DEMO_NOTES.md.
#
# Dùng:
#   ./run_local.sh            # bật agent :8080 + UI :3000 (UI trỏ vào agent local)
#   Ctrl+C để dừng cả hai.
#
# Yêu cầu: ĐÃ BẬT VPN nội bộ (để live). Không có VPN vẫn chạy được nhưng badge sẽ là cache.

set -uo pipefail
cd "$(dirname "$0")"

PY="venv/bin/python"
AGENT_PORT="${PORT:-8080}"
UI_PORT="${UI_PORT:-3000}"
AGENT_LOG="/tmp/dp_agent_local.log"

[ -x "$PY" ] || { echo "❌ Không thấy $PY — tạo venv trước (python -m venv venv && venv/bin/pip install -r requirements.txt)"; exit 1; }

# Giải phóng port nếu lần chạy trước để lại process sót (tránh lỗi "address already in use")
for port in "$AGENT_PORT" "$UI_PORT"; do
  pid=$(lsof -ti tcp:"$port" 2>/dev/null) || true
  if [ -n "$pid" ]; then echo "  ⚠️  Port $port đang bị giữ (pid $pid) — giải phóng…"; kill -9 $pid 2>/dev/null || true; sleep 1; fi
done

echo "▶ Khởi động AGENT local trên :$AGENT_PORT  (log: $AGENT_LOG)"
PYTHONPATH=. PORT="$AGENT_PORT" "$PY" src/main.py > "$AGENT_LOG" 2>&1 &
AGENT_PID=$!

cleanup() { echo; echo "⏹  Dừng agent (pid $AGENT_PID)…"; kill "$AGENT_PID" 2>/dev/null || true; }
trap cleanup EXIT INT TERM

# Đợi agent sẵn sàng (health 200)
printf "  đợi agent sẵn sàng"
ready=0
for _ in $(seq 1 30); do
  if [ "$(curl -s -o /dev/null -w '%{http_code}' "http://localhost:$AGENT_PORT/health" 2>/dev/null)" = "200" ]; then
    ready=1; printf " ✓\n"; break
  fi
  printf "."; sleep 1
done
[ "$ready" = "1" ] || { echo; echo "❌ Agent không lên — xem $AGENT_LOG"; exit 1; }

# Kiểm tra Trust Layer có LIVE không (xác nhận VPN reach được nguồn nội bộ)
fresh=$(curl -s --max-time 30 -X POST "http://localhost:$AGENT_PORT/invocations" \
  -H "Content-Type: application/json" -d '{"message":"tìm loan_core_statement"}' 2>/dev/null \
  | "$PY" -c "import sys,json;print((json.load(sys.stdin).get('freshness') or {}).get('level','?'))" 2>/dev/null || echo "?")
case "$fresh" in
  live|partial) echo "  Trust Layer: 🟢 $fresh — LIVE OK, quay video được rồi!" ;;
  *)            echo "  Trust Layer: 🔴 $fresh — chưa LIVE. Kiểm tra VPN đã bật chưa (cần reach nguồn nội bộ)." ;;
esac

echo "▶ Khởi động UI trên :$UI_PORT (trỏ vào agent LOCAL, không phải prod)"
echo "  → Mở trình duyệt: http://localhost:$UI_PORT"
echo "  (Ctrl+C để dừng cả agent lẫn UI)"
echo
AGENT_ENDPOINT="http://localhost:$AGENT_PORT" UI_PORT="$UI_PORT" "$PY" ui/server.py
