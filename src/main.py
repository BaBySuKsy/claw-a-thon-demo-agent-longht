import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from greennode_agentbase import (
    GreenNodeAgentBaseApp,
    RequestContext,
    PingStatus,
)
from starlette.responses import HTMLResponse, JSONResponse, StreamingResponse

from src.agents.copilot import DataPlatformCopilot

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def _alert_loop():
    """Background loop: run health check shortly after startup, then every 30 min.

    The first scan is delayed so the platform's readiness probe (GET /health) can
    pass on a clean event loop — the health check fans out to internal services
    (DataHub/GitLab/Jira) that may be slow/unreachable from the runtime, and we don't
    want that connection storm competing with the startup readiness window.
    """
    from src.tools.monitor import run_health_check
    await asyncio.sleep(45)  # let readiness probe mark the runtime ACTIVE first
    # First scan after startup so alerts are populated before normal usage
    try:
        new_alerts = await run_health_check()
        logger.info("Startup health check: %d alert(s) detected", len(new_alerts))
    except Exception as e:
        logger.warning("Startup health check failed: %s", e)
    while True:
        await asyncio.sleep(1800)  # 30 minutes
        try:
            new_alerts = await run_health_check()
            if new_alerts:
                logger.info("Periodic health check: %d new alert(s)", len(new_alerts))
        except Exception as e:
            logger.warning("Periodic health check failed: %s", e)


@asynccontextmanager
async def _lifespan(app):
    task = asyncio.create_task(_alert_loop())
    try:
        yield
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


app = GreenNodeAgentBaseApp(lifespan=_lifespan)

# Warm up engine at startup — avoids 1.5s cold start on first request
logger.info("Warming up Knowledge Engine...")
from src.tools.discovery import get_engine
_engine = get_engine()
logger.info("Engine ready: %d entities, %d relationships", len(_engine.entities), len(_engine.relationships))

copilot = DataPlatformCopilot()


# --- Web UI (served at GET / so the public endpoint is browsable) ---------------
# The deployed endpoint otherwise exposes only POST /invocations + GET /health, so a
# judge opening the URL in a browser would see 404. Serving the SPA here makes the
# same public URL a working chat page (it calls /api/chat[/stream] same-origin — no CORS).
try:
    _UI_HTML = (Path(__file__).resolve().parent.parent / "ui" / "index.html").read_text(encoding="utf-8")
except Exception as _e:  # pragma: no cover — UI is optional, agent still serves /invocations
    logger.warning("UI index.html not found, GET / will show a minimal page: %s", _e)
    _UI_HTML = "<h1>Acme Data Platform AI</h1><p>POST /invocations with {\"message\": \"...\"}.</p>"


async def _ui_index(request):
    return HTMLResponse(_UI_HTML)


def _envelope(result: dict, session_id):
    for t in result.get("tools_called", []) or []:
        t.pop("result", None)  # UI only renders tool name + args; keep payload small
    return {
        "status": "success",
        "agent": "Acme Data Platform AI",
        "answer": result.get("answer", ""),
        "tools_called": result.get("tools_called", []),
        "tool_call_count": result.get("tool_call_count", 0),
        "llm_iterations": result.get("llm_iterations", 0),
        "confidence": result.get("confidence", 0.0),
        "freshness": result.get("freshness"),
        "model": result.get("model", ""),
        "session_id": session_id,
        "timestamp": datetime.now().isoformat(),
    }


async def _api_chat(request):
    try:
        payload = await request.json()
    except Exception:
        return JSONResponse({"status": "error", "message": "Invalid JSON body"}, status_code=400)
    message = (payload or {}).get("message", "").strip()
    if not message:
        return JSONResponse({"status": "error", "message": "Empty message"}, status_code=400)
    session_id = payload.get("session_id")
    try:
        result = await copilot.chat(message, session_id=session_id)
    except Exception as exc:
        return JSONResponse({"status": "error", "message": f"Agent error: {exc}"}, status_code=502)
    return JSONResponse(_envelope(result, session_id))


async def _api_chat_stream(request):
    try:
        payload = await request.json()
    except Exception:
        return JSONResponse({"status": "error", "message": "Invalid JSON body"}, status_code=400)
    message = (payload or {}).get("message", "").strip()
    if not message:
        return JSONResponse({"status": "error", "message": "Empty message"}, status_code=400)
    session_id = payload.get("session_id")

    async def event_gen():
        try:
            async for ev in copilot.chat_stream(message, session_id=session_id):
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


app.add_route("/", _ui_index, methods=["GET"])
app.add_route("/api/chat", _api_chat, methods=["POST"])
app.add_route("/api/chat/stream", _api_chat_stream, methods=["POST"])


@app.entrypoint
async def handle_request(payload: dict, context: RequestContext) -> dict:
    """GreenNode AgentBase entrypoint — Acme Data Platform AI Agent."""
    user_query = payload.get("message", "")
    session_id = getattr(context, "session_id", None) or payload.get("session_id")

    if not user_query:
        return {
            "status": "error",
            "message": "No query provided. Send {\"message\": \"your question\"}.",
            "timestamp": datetime.now().isoformat(),
        }

    # Streaming path (opt-in via {"stream": true}). Returning an async generator makes
    # the AgentBase runtime stream each yielded event as SSE (text/event-stream). The
    # default (non-streaming) path below is unchanged for backward compatibility.
    if payload.get("stream"):
        async def _event_stream():
            async for event in copilot.chat_stream(user_query, session_id=session_id):
                yield event
        return _event_stream()

    result = await copilot.chat(user_query, session_id=session_id)

    return {
        "status": "success",
        "agent": "Acme Data Platform AI",
        "answer": result.get("answer", ""),
        "tools_called": result.get("tools_called", []),
        "tool_call_count": result.get("tool_call_count", 0),
        "llm_iterations": result.get("llm_iterations", 0),
        "confidence": result.get("confidence", 0.0),
        "freshness": result.get("freshness"),
        "model": result.get("model", ""),
        "session_id": session_id,
        "timestamp": datetime.now().isoformat(),
    }


@app.ping
def health_check() -> PingStatus:
    """AgentBase health check endpoint."""
    return PingStatus.HEALTHY


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    app.run(port=port, host="0.0.0.0")
