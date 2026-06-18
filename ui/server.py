"""
Lightweight web UI for the Acme Data Platform Copilot.

Serves a single-page chat interface and proxies requests to the AgentBase agent
endpoint server-side (the agent endpoint sends no CORS headers, so the browser
cannot call it directly). Run:

    venv/bin/python ui/server.py
    # then open http://localhost:3000

Point at a different agent with AGENT_ENDPOINT, e.g. a local agent:
    AGENT_ENDPOINT=http://localhost:8080 venv/bin/python ui/server.py
"""

import os
from pathlib import Path

import json

import httpx
import uvicorn
from starlette.applications import Starlette
from starlette.responses import JSONResponse, FileResponse, StreamingResponse
from starlette.routing import Route

# Default: the live AgentBase deployment. Override via env for local testing.
AGENT_ENDPOINT = os.getenv(
    "AGENT_ENDPOINT",
    "https://endpoint-8b483005-086d-43c9-a704-101e13eb6a3d.agentbase-runtime.aiplatform.vngcloud.vn",
).rstrip("/")

_UI_DIR = Path(__file__).parent
_TIMEOUT = float(os.getenv("AGENT_TIMEOUT", "150"))


async def index(request):
    return FileResponse(_UI_DIR / "index.html")


async def chat(request):
    """Proxy a chat turn to the agent's /invocations endpoint."""
    try:
        payload = await request.json()
    except Exception:
        return JSONResponse({"status": "error", "message": "Invalid JSON body"}, status_code=400)

    message = (payload or {}).get("message", "").strip()
    if not message:
        return JSONResponse({"status": "error", "message": "Empty message"}, status_code=400)

    body = {"message": message}
    if payload.get("session_id"):
        body["session_id"] = payload["session_id"]

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(f"{AGENT_ENDPOINT}/invocations", json=body)
        resp.raise_for_status()
        data = resp.json()
        # Trim per-tool `result` blobs the UI never renders — smaller payload, less
        # internal data over the wire (the UI only shows tool name + args).
        for t in data.get("tools_called", []) or []:
            t.pop("result", None)
        return JSONResponse(data)
    except httpx.TimeoutException:
        return JSONResponse(
            {"status": "error", "message": "Agent timed out — thử lại hoặc hỏi ngắn gọn hơn."},
            status_code=504,
        )
    except Exception as exc:
        return JSONResponse({"status": "error", "message": f"Agent error: {exc}"}, status_code=502)


async def chat_stream(request):
    """Proxy a STREAMING chat turn: forward the agent's SSE events to the browser.

    Sends {"stream": true} to the agent and relays each `data: {...}` event live so
    the UI can render tool-progress and the answer token-by-token. The `done` event's
    per-tool `result` blobs are stripped (same as the non-streaming proxy) — smaller
    payload, no internal data over the wire.
    """
    try:
        payload = await request.json()
    except Exception:
        return JSONResponse({"status": "error", "message": "Invalid JSON body"}, status_code=400)

    message = (payload or {}).get("message", "").strip()
    if not message:
        return JSONResponse({"status": "error", "message": "Empty message"}, status_code=400)

    body = {"message": message, "stream": True}
    if payload.get("session_id"):
        body["session_id"] = payload["session_id"]

    async def event_gen():
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                async with client.stream("POST", f"{AGENT_ENDPOINT}/invocations", json=body) as resp:
                    resp.raise_for_status()
                    async for line in resp.aiter_lines():
                        if not line.startswith("data: "):
                            continue
                        raw = line[6:]
                        try:
                            ev = json.loads(raw)
                        except Exception:
                            yield line + "\n\n"
                            continue
                        if ev.get("type") == "done":
                            for t in ev.get("tools_called", []) or []:
                                t.pop("result", None)
                        yield "data: " + json.dumps(ev, ensure_ascii=False) + "\n\n"
        except Exception as exc:
            yield "data: " + json.dumps({"type": "error", "message": f"Agent error: {exc}"}) + "\n\n"

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


async def health(request):
    return JSONResponse({"status": "ok", "agent_endpoint": AGENT_ENDPOINT})


app = Starlette(routes=[
    Route("/", index),
    Route("/api/chat", chat, methods=["POST"]),
    Route("/api/chat/stream", chat_stream, methods=["POST"]),
    Route("/api/health", health),
])


if __name__ == "__main__":
    port = int(os.getenv("UI_PORT", "3000"))
    print(f"\n  Acme DP Copilot UI → http://localhost:{port}")
    print(f"  Proxying to agent: {AGENT_ENDPOINT}\n")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="warning")
