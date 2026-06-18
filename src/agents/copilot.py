"""
DataPlatformCopilot — Acme Knowledge Platform Agent Core.

Implements a real LLM-powered agent using MiniMax-M2.5 via GreenNode MaaS
with OpenAI-compatible function calling (tool-calling loop).

Architecture:
    User Query
        → _route_query()         # intent pre-classification
        → inject_context()       # pre-fetch relevant context into messages
        → LLM call with tools    # MiniMax-M2.5 decides which tool to call
        → tool dispatcher        # executes the requested tool
        → LLM synthesis call     # LLM generates final answer with tool result
        → structured response
"""

import asyncio
import json
import logging
import os
import re
from datetime import datetime, timezone
from typing import Any

from openai import AsyncOpenAI

from src.agents.prompts import SYSTEM_PROMPT, TOOL_DEFINITIONS
from src.tools.discovery import (
    search_metadata, search_metadata_multi, get_ownership, get_entity_details,
    get_related_context, read_gitlab_file, read_confluence_page,
    get_platform_overview,
)
from src.tools.impact import analyze_impact
from src.tools.triage import diagnose_entity
from src.tools.jira_live import search_jira_tickets
from src.tools.git_history import get_recent_commits, get_merge_requests
from src.tools.freshness import get_data_freshness
from src.tools.discovery import get_schema
from src.tools.monitor import get_platform_alerts, get_health_briefing
from src.tools.temporal import get_changes_since
from src.tools.redact import redact
from collections import deque

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────────────
MAX_TOOL_ITERATIONS = 6  # Safety limit: prevents infinite tool-calling loops / token burn
_SEARCH_VERIFY_TIMEOUT = 6  # cap (s) on live freshness-verification of top search hits

# Intent classifier patterns — ordered from most specific to most general
_INTENT_PATTERNS = {
    "INCIDENT": [
        r"\bstale\b", r"\bbroken\b", r"\bfail(ed|ing)?\b", r"\bdelay(ed)?\b",
        r"\bdebug\b", r"\bdiagnos", r"\bnot.updat", r"\bwhy.is\b", r"\broot.cause\b",
        r"\blỗi\b", r"\bsự.cố\b", r"\bbị.chậm\b", r"\bchậm\b", r"\bhỏng\b",
        r"\bkhông.cập.nhật\b", r"\bchưa.cập.nhật\b", r"\btại.sao\b", r"\bvì.sao\b",
        r"\bcó.vấn.đề\b", r"\bđiều.tra\b", r"\btrục.trặc\b",
    ],
    "IMPACT": [
        r"\bimpact\b", r"\baffect\b", r"\bdownstream\b", r"\bbreaking.change\b",
        r"\bif.i.change\b", r"\bif.i.modify\b", r"\bwhat.breaks\b", r"\bwhat.depends\b",
        r"\bdepends.on\b", r"\bbreak\b",
        r"\bảnh.hưởng\b", r"\btác.động\b", r"\bphụ.thuộc\b", r"\bsửa\b",
    ],
    "BRIEFING": [
        r"\bbriefing\b", r"\bmorning.brief", r"\bhealth.summary\b", r"\bdaily.report\b",
        r"\bplatform.health\b", r"\boverview.*health\b",
        r"\btình.hình\b", r"\btổng.quan.sức.khỏe\b", r"\bsức.khỏe.*platform\b",
        r"\bbáo.cáo.*ngày\b", r"\bhôm.nay.*(thế.nào|ra.sao|có.gì)\b",
    ],
    "CHANGES": [
        r"\bwhat.changed\b", r"\bwhat'?s.changed\b", r"\brecent.changes\b",
        r"\bsince.yesterday\b", r"\bwhat'?s.new\b", r"\bchanges.in.the.last\b",
        r"\bschema.drift\b", r"\bschema.change",
        r"\bcó.gì.thay.đổi\b", r"\bthay.đổi.gì\b", r"\btừ.hôm.qua\b",
        r"\bgần.đây.có.gì\b", r"\bcó.gì.mới\b", r"\bđổi.schema\b", r"\bthay.đổi.gần.đây\b",
    ],
    "ONBOARDING": [
        r"\bonboard\b", r"\bget.start\b", r"\bnew.joiner\b", r"\bwhere.do.i.start\b",
        r"\bhướng.dẫn\b", r"\bbắt.đầu\b", r"\bnhập.môn\b", r"\bgiới.thiệu\b",
    ],
    "SPECIFIC": [
        r"\bwho.owns\b", r"\bowner\b", r"\bschema\b", r"\bcolumn\b",
        r"\bdescription.of\b", r"\bdetail\b", r"\bchủ.sở.hữu\b", r"\bthông.tin\b",
    ],
    "BROAD": [
        r"\bshow.me\b", r"\blist\b", r"\bfind\b", r"\bsearch\b", r"\ball\b",
        r"\btìm\b", r"\bliệt.kê\b", r"\bcác.bảng\b", r"\bcó.những\b",
    ],
}

_SESSION_STORE: dict = {}
_MAX_SESSIONS = 100
_MAX_HISTORY = 16  # 8 user turns + 8 assistant turns


class DataPlatformCopilot:
    """
    AI Copilot for Acme Data Platform.

    Wraps MiniMax-M2.5 with tool-calling capability for metadata discovery,
    ownership lookup, and downstream impact analysis.
    """

    def __init__(self) -> None:
        self.model: str = os.getenv("LLM_MODEL", "minimax/minimax-m2.5")
        self.client = AsyncOpenAI(
            api_key=os.getenv("LLM_API_KEY"),
            base_url=os.getenv("LLM_BASE_URL", "https://maas-llm-aiplatform-hcm.api.vngcloud.vn/v1"),
        )
        # Tool dispatcher: maps function name → callable
        self._tool_dispatch: dict[str, Any] = {
            "search_metadata": self._run_search_metadata,
            "get_platform_overview": self._run_get_platform_overview,
            "get_ownership": self._run_get_ownership,
            "analyze_impact": self._run_analyze_impact,
            "diagnose_entity": self._run_diagnose_entity,
            "get_entity_details": self._run_get_entity_details,
            "get_related_context": self._run_get_related_context,
            "read_gitlab_file": self._run_read_gitlab_file,
            "read_confluence_page": self._run_read_confluence_page,
            "search_jira_tickets": self._run_search_jira,
            "get_recent_commits": self._run_get_recent_commits,
            "get_data_freshness": self._run_get_data_freshness,
            "get_schema": self._run_get_schema,
            "get_platform_alerts": self._run_get_platform_alerts,
            "get_health_briefing": self._run_get_health_briefing,
            "get_changes_since": self._run_get_changes_since,
        }

    # ──────────────────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────────────────

    async def chat(self, user_message: str, session_id: str = None) -> dict:
        """
        Process a user query end-to-end:
        1. Classify intent via _route_query().
        2. Pre-fetch relevant context for ONBOARDING / BROAD queries.
        3. Send to LLM with tool definitions.
        4. If LLM requests a tool call → execute tool → send result back to LLM.
        5. Repeat up to MAX_TOOL_ITERATIONS.
        6. Return the final synthesized response.
        """
        intent = self._route_query(user_message)
        logger.info("Query intent classified as: %s", intent)

        messages = self._build_messages(user_message, intent, session_id)

        tools_called: list[dict] = []

        for iteration in range(MAX_TOOL_ITERATIONS):
            logger.info("LLM iteration %d for query: %s", iteration + 1, user_message[:80])

            # ── Step 1: Call LLM ──────────────────────────────────────────────
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=TOOL_DEFINITIONS,
                tool_choice="auto",
                temperature=0.1,  # Low temperature for factual metadata answers
            )

            assistant_message = response.choices[0].message

            # ── Step 2: Check if LLM wants to call a tool ────────────────────
            if not assistant_message.tool_calls:
                # No more tool calls — LLM has final answer
                final_text = assistant_message.content or ""
                logger.info("LLM produced final answer after %d tool call(s).", len(tools_called))
                self._persist_session(session_id, user_message, final_text)
                return self._build_response(
                    answer=final_text,
                    tools_called=tools_called,
                    iterations=iteration + 1,
                    session_id=session_id,
                )

            # ── Step 3: Execute all tool calls requested by LLM (in parallel) ─
            messages.append(assistant_message)  # Add assistant's tool-call request

            # Parse every requested call first, then dispatch them CONCURRENTLY.
            # When the LLM asks for several tools in one turn (e.g. analyze_impact +
            # get_ownership + get_data_freshness), running them with asyncio.gather
            # collapses total latency to the SLOWEST single call instead of the sum.
            # _dispatch_tool swallows its own exceptions (returns {"error": ...}),
            # so gather never raises here. Order is preserved by gather, which keeps
            # each tool result aligned to its originating tool_call_id.
            parsed_calls = []
            for tool_call in assistant_message.tool_calls:
                try:
                    tool_args = json.loads(tool_call.function.arguments or "{}")
                except json.JSONDecodeError:
                    logger.warning("Malformed tool args for %s: %r",
                                   tool_call.function.name, tool_call.function.arguments)
                    tool_args = {}
                logger.info("Dispatching tool: %s(%s)", tool_call.function.name, tool_args)
                parsed_calls.append((tool_call, tool_call.function.name, tool_args))

            tool_results = await asyncio.gather(
                *[self._dispatch_tool(name, args) for _, name, args in parsed_calls]
            )

            for (tool_call, tool_name, tool_args), tool_result in zip(parsed_calls, tool_results):
                tools_called.append({"tool": tool_name, "args": tool_args, "result": tool_result})

                # Append tool result to conversation context (order matches tool_calls)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(tool_result, ensure_ascii=False, default=str),
                })

        # Graceful fallback: force one final synthesis WITHOUT tools so the user
        # gets a real answer from whatever was gathered (never a dead-end message).
        logger.warning("Reached MAX_TOOL_ITERATIONS (%d) for query: %s", MAX_TOOL_ITERATIONS, user_message)
        try:
            messages.append({
                "role": "system",
                "content": "Tool budget reached. Synthesize the best possible answer NOW "
                           "from the tool results already gathered. Do not request more tools.",
            })
            # Keep tools in scope (history contains tool_calls) but forbid new calls,
            # so OpenAI-compatible backends don't reject the replayed conversation.
            final = await self.client.chat.completions.create(
                model=self.model, messages=messages, tools=TOOL_DEFINITIONS,
                tool_choice="none", temperature=0.1,
            )
            answer = final.choices[0].message.content or "Đã tổng hợp từ dữ liệu thu thập được."
        except Exception as exc:
            logger.warning("Final synthesis fallback failed: %s", exc)
            answer = "Mình đã thu thập một số dữ liệu nhưng chưa tổng hợp xong — bạn thử hỏi cụ thể hơn nhé."
        return self._build_response(
            answer=answer, tools_called=tools_called,
            iterations=MAX_TOOL_ITERATIONS, session_id=session_id,
        )

    async def chat_stream(self, user_message: str, session_id: str = None):
        """Streaming variant of chat() — an async generator of SSE event dicts.

        Yields, in order:
          • {"type": "status", "stage": "routing", "intent": ...}     once at start
          • {"type": "status", "stage": "tool",  "tool": ..., "args": ...}  per tool dispatched
          • {"type": "status", "stage": "tools_done", "count": N}     after a tool round
          • {"type": "token",  "content": "..."}                      streamed answer chunks
          • {"type": "done",   ...full response envelope...}           once at the end

        Same tool-calling loop and helpers as chat(); the only difference is the LLM
        call uses stream=True so the final answer tokens flow live, and tool progress
        is surfaced as status events. The non-streaming chat() path is untouched.
        """
        intent = self._route_query(user_message)
        logger.info("Stream query intent: %s", intent)
        yield {"type": "status", "stage": "routing", "intent": intent}

        messages = self._build_messages(user_message, intent, session_id)
        tools_called: list[dict] = []
        final_text = ""

        for iteration in range(MAX_TOOL_ITERATIONS):
            stream = await self.client.chat.completions.create(
                model=self.model, messages=messages, tools=TOOL_DEFINITIONS,
                tool_choice="auto", temperature=0.1, stream=True,
            )

            content_buf: list[str] = []
            tool_acc: dict[int, dict] = {}  # index → {id, name, args}
            async for chunk in stream:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                if getattr(delta, "content", None):
                    content_buf.append(delta.content)
                    yield {"type": "token", "content": delta.content}
                for tc in (getattr(delta, "tool_calls", None) or []):
                    slot = tool_acc.setdefault(tc.index, {"id": None, "name": "", "args": ""})
                    if tc.id:
                        slot["id"] = tc.id
                    if tc.function and tc.function.name:
                        slot["name"] = tc.function.name
                    if tc.function and tc.function.arguments:
                        slot["args"] += tc.function.arguments

            # No tool calls this turn → the streamed content IS the final answer.
            if not tool_acc:
                final_text = "".join(content_buf)
                break

            # Rebuild the assistant tool-call message for conversation context.
            ordered = [tool_acc[i] for i in sorted(tool_acc)]
            messages.append({
                "role": "assistant",
                "content": "".join(content_buf) or None,
                "tool_calls": [
                    {"id": s["id"], "type": "function",
                     "function": {"name": s["name"], "arguments": s["args"] or "{}"}}
                    for s in ordered
                ],
            })

            parsed = []
            for s in ordered:
                try:
                    args = json.loads(s["args"] or "{}")
                except json.JSONDecodeError:
                    logger.warning("Malformed streamed tool args for %s: %r", s["name"], s["args"])
                    args = {}
                parsed.append((s, s["name"], args))
                yield {"type": "status", "stage": "tool", "tool": s["name"], "args": args}

            results = await asyncio.gather(
                *[self._dispatch_tool(name, args) for _, name, args in parsed]
            )
            for (s, name, args), result in zip(parsed, results):
                tools_called.append({"tool": name, "args": args, "result": result})
                messages.append({
                    "role": "tool",
                    "tool_call_id": s["id"],
                    "content": json.dumps(result, ensure_ascii=False, default=str),
                })
            yield {"type": "status", "stage": "tools_done", "count": len(parsed)}
        else:
            # Reached MAX_TOOL_ITERATIONS — force one final synthesis without tools.
            logger.warning("Stream reached MAX_TOOL_ITERATIONS for: %s", user_message[:80])
            messages.append({
                "role": "system",
                "content": "Tool budget reached. Synthesize the best possible answer NOW "
                           "from the tool results already gathered. Do not request more tools.",
            })
            try:
                final_stream = await self.client.chat.completions.create(
                    model=self.model, messages=messages, tools=TOOL_DEFINITIONS,
                    tool_choice="none", temperature=0.1, stream=True,
                )
                buf = []
                async for chunk in final_stream:
                    if chunk.choices and getattr(chunk.choices[0].delta, "content", None):
                        buf.append(chunk.choices[0].delta.content)
                        yield {"type": "token", "content": chunk.choices[0].delta.content}
                final_text = "".join(buf) or "Đã tổng hợp từ dữ liệu thu thập được."
            except Exception as exc:
                logger.warning("Stream final synthesis fallback failed: %s", exc)
                final_text = "Mình đã thu thập một số dữ liệu nhưng chưa tổng hợp xong — bạn thử hỏi cụ thể hơn nhé."

        self._persist_session(session_id, user_message, final_text)
        # The done envelope carries the citation-footer'd answer (source of truth for
        # the client to render once streaming ends) plus tools/confidence/freshness.
        response = self._build_response(
            answer=final_text, tools_called=tools_called,
            iterations=iteration + 1, session_id=session_id,
        )
        yield {"type": "done", **response}

    # ──────────────────────────────────────────────────────────────────────────
    # Tool Dispatcher
    # ──────────────────────────────────────────────────────────────────────────

    async def _dispatch_tool(self, tool_name: str, args: dict) -> Any:
        """Route tool call to the correct implementation. Returns serializable result."""
        handler = self._tool_dispatch.get(tool_name)
        if handler is None:
            logger.error("Unknown tool requested by LLM: %s", tool_name)
            return {"error": f"Unknown tool: {tool_name}"}
        try:
            result = await handler(**args)
            # Redaction guard: scrub internal IPs / emails / DB credentials from
            # tool output before it reaches the LLM context or the user.
            return redact(result)
        except Exception as exc:
            logger.exception("Tool '%s' raised an error: %s", tool_name, exc)
            return {"error": str(exc)}

    async def _run_search_metadata(self, query: str) -> list[dict]:
        """Search metadata, then LIVE-verify the freshness of the top dataset hits.

        search_metadata() itself is an in-memory graph read (fast, but the seed is
        static). To make the most-used tool reflect real-time state, we opportunistically
        check DataHub freshness for the top results and annotate each with `_freshness`.
        Bounded + best-effort: on timeout/failure the cached results are returned as-is.

        Retrieval uses multi-query Reciprocal Rank Fusion (search_metadata_multi) for
        higher recall on multi-concept / paraphrased questions.
        """
        entities = search_metadata_multi(query)
        dicts = [self._entity_to_dict(e) for e in entities]
        await self._annotate_freshness(entities, dicts, top_n=3)
        return dicts

    async def _annotate_freshness(self, entities: list, dicts: list[dict], top_n: int = 3) -> None:
        """Attach live `_freshness` to the top dataset results (in place, best-effort)."""
        targets = [
            (e, d) for e, d in zip(entities, dicts)
            if getattr(e, "type", "") == "dataset"
        ][:top_n]
        if not targets:
            return

        async def _one(entity, d):
            fr = await get_data_freshness(entity.id)
            if fr.get("source") == "datahub_live":
                d["_freshness"] = {
                    "source": "datahub_live",
                    "last_updated": fr.get("last_modified_human"),
                    "row_count": fr.get("row_count"),
                }
            else:
                d["_freshness"] = {"source": fr.get("source", "cache_only")}

        try:
            await asyncio.wait_for(
                asyncio.gather(*[_one(e, d) for e, d in targets], return_exceptions=True),
                timeout=_SEARCH_VERIFY_TIMEOUT,
            )
        except Exception as exc:  # TimeoutError or any live-fetch failure
            logger.debug("search freshness verification skipped: %s", exc)

    async def _run_get_platform_overview(self, domain: str = None) -> dict:
        """Wrapper: curated platform overview for onboarding (single call)."""
        return get_platform_overview(domain)

    async def _run_get_ownership(self, entity_id: str) -> dict:
        """Wrapper: get_ownership returns dict or None."""
        result = get_ownership(entity_id)
        return result or {"error": f"Entity '{entity_id}' not found."}

    async def _run_get_entity_details(self, entity_id: str) -> dict:
        """Wrapper: get_entity_details for JIT freshness verification."""
        result = get_entity_details(entity_id)
        return result or {"error": f"Entity '{entity_id}' not found."}

    async def _run_analyze_impact(self, entity_id: str) -> dict:
        """Wrapper: analyze_impact returns structured impact dict."""
        return analyze_impact(entity_id)

    async def _run_diagnose_entity(self, entity_id: str) -> dict:
        """Wrapper: incident triage / root-cause orchestration (async)."""
        return await diagnose_entity(entity_id)

    async def _run_get_related_context(self, entity_id: str) -> dict:
        """Wrapper: get_related_context — returns Jira, Confluence, pipeline cross-links."""
        return get_related_context(entity_id)

    async def _run_read_gitlab_file(self, project_name: str, file_path: str) -> dict:
        """Wrapper: read_gitlab_file (sync) — run in thread pool to avoid blocking event loop."""
        import asyncio
        from functools import partial
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, partial(read_gitlab_file, project_name, file_path))

    async def _run_read_confluence_page(self, page_id: str) -> dict:
        """Wrapper: read_confluence_page (async)."""
        return await read_confluence_page(page_id)

    async def _run_search_jira(self, query: str, status: str = None) -> dict:
        return await search_jira_tickets(query, status)

    async def _run_get_recent_commits(self, project_name: str, days: int = 7) -> dict:
        return await get_recent_commits(project_name, days)

    async def _run_get_data_freshness(self, entity_id: str) -> dict:
        return await get_data_freshness(entity_id)

    async def _run_get_schema(self, entity_id: str) -> dict:
        return await get_schema(entity_id)

    async def _run_get_platform_alerts(self, severity: str = None, entity_id: str = None) -> dict:
        return get_platform_alerts(severity=severity, entity_id=entity_id)

    async def _run_get_health_briefing(self) -> dict:
        """Wrapper: daily data health briefing (proactive digest)."""
        return await get_health_briefing()

    async def _run_get_changes_since(self, scope: str = None, hours: int = 24) -> dict:
        """Wrapper: temporal 'what changed recently' digest (schema drift + commits + staleness)."""
        return await get_changes_since(scope=scope, hours=hours)

    # ──────────────────────────────────────────────────────────────────────────
    # Intent Classifier
    # ──────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _route_query(query: str) -> str:
        """
        Classify query intent into one of: IMPACT, ONBOARDING, SPECIFIC, BROAD.

        Returns intent string. Falls back to SPECIFIC if no pattern matches.
        Checked in priority order: INCIDENT > IMPACT > BRIEFING > CHANGES > ONBOARDING > SPECIFIC > BROAD.
        """
        q = query.lower()
        for intent in ("INCIDENT", "IMPACT", "BRIEFING", "CHANGES", "ONBOARDING", "SPECIFIC", "BROAD"):
            for pattern in _INTENT_PATTERNS[intent]:
                if re.search(pattern, q):
                    return intent
        return "SPECIFIC"

    # Per-intent routing hints injected as a system message to steer the first
    # tool choice (reduces tool iterations). Shared by chat() and chat_stream().
    _ROUTING_HINTS = {
        "ONBOARDING": (
            "[ROUTING HINT] This is an ONBOARDING query. "
            "Call get_platform_overview() FIRST (single call) to get domains, Tier1 tables, "
            "key pipelines, owning team and must-read docs. Then synthesize a friendly, "
            "structured onboarding guide. Do NOT make repeated search_metadata calls."
        ),
        "INCIDENT": (
            "[ROUTING HINT] This is an INCIDENT / TROUBLESHOOTING query. "
            "Call diagnose_entity(entity_id) — it correlates freshness, recent commits, "
            "open Jira incidents and downstream Tier1 impact in one step. Present the findings, "
            "the likely root cause, and the recommended actions clearly."
        ),
        "IMPACT": (
            "[ROUTING HINT] This is an IMPACT ANALYSIS query. "
            "Use analyze_impact to find downstream entities. "
            "If critical_tier1_count > 0, include the warning prominently in your answer."
        ),
        "BRIEFING": (
            "[ROUTING HINT] This is a PLATFORM HEALTH BRIEFING query. "
            "Call get_health_briefing() once and present it as a concise morning briefing."
        ),
        "CHANGES": (
            "[ROUTING HINT] This is a 'WHAT CHANGED RECENTLY' query. "
            "Call get_changes_since(scope?, hours?) once — it returns schema drift, newly stale "
            "Tier1 tables and recent pipeline commits in the window. Flag any schema change as "
            "potentially breaking and suggest analyze_impact if relevant."
        ),
        "BROAD": (
            "[ROUTING HINT] This is a BROAD DISCOVERY query. "
            "Use search_metadata first, then get_entity_details for the top results."
        ),
    }

    def _build_messages(self, user_message: str, intent: str, session_id: str = None) -> list:
        """Assemble the LLM message list: system prompt + history + routing hint + user turn."""
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        if session_id and session_id in _SESSION_STORE:
            messages.extend(list(_SESSION_STORE[session_id]))
        hint = self._ROUTING_HINTS.get(intent)
        if hint:
            messages.append({"role": "system", "content": hint})
        messages.append({"role": "user", "content": user_message})
        return messages

    @staticmethod
    def _persist_session(session_id: str, user_message: str, final_text: str) -> None:
        """Append a user/assistant turn pair to the bounded session memory."""
        if not session_id:
            return
        if session_id not in _SESSION_STORE:
            if len(_SESSION_STORE) >= _MAX_SESSIONS:
                del _SESSION_STORE[next(iter(_SESSION_STORE))]
            _SESSION_STORE[session_id] = deque(maxlen=_MAX_HISTORY)
        _SESSION_STORE[session_id].append({"role": "user", "content": user_message})
        _SESSION_STORE[session_id].append({"role": "assistant", "content": final_text})

    # ──────────────────────────────────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _entity_to_dict(entity: Any) -> dict:
        """Safely convert a dataclass entity to a plain dict for JSON serialization."""
        try:
            import dataclasses
            return dataclasses.asdict(entity)
        except TypeError:
            # Fallback for non-dataclass objects
            return vars(entity)

    @staticmethod
    def _compute_confidence(tools_called: list) -> float:
        """Score 0.0-1.0 based on data coverage from tool results."""
        score = 0.3  # baseline
        tool_set = {t["tool"] for t in tools_called}
        results = {t["tool"]: t["result"] for t in tools_called}

        if "search_metadata" in tool_set or "get_entity_details" in tool_set:
            r = results.get("search_metadata") or results.get("get_entity_details")
            if r:
                first = r[0] if isinstance(r, list) else r
                if isinstance(first, dict):
                    if first.get("description"):
                        score += 0.15
                    if first.get("upstream") or first.get("downstream") or first.get("inputs"):
                        score += 0.10
                # Breadth bonus: surfacing several distinct entities = good coverage
                if isinstance(r, list) and len(r) >= 3:
                    score += 0.10
        # Onboarding: a single grounded overview is high-confidence by construction
        if "get_platform_overview" in tool_set:
            r = results.get("get_platform_overview", {})
            if isinstance(r, dict) and r.get("domains"):
                score += 0.40
        # Incident triage: a completed diagnosis is a strong, multi-source answer
        if "diagnose_entity" in tool_set:
            r = results.get("diagnose_entity", {})
            if isinstance(r, dict) and not r.get("error"):
                score += 0.25
        # Platform alerts: a successful health check (even "no alerts") is reliable signal
        if "get_platform_alerts" in tool_set:
            r = results.get("get_platform_alerts", {})
            if isinstance(r, dict) and "last_check" in r and r.get("last_check") != "not yet run":
                score += 0.30
        if "analyze_impact" in tool_set:
            r = results.get("analyze_impact", {})
            if isinstance(r, dict) and r.get("impact_count", 0) > 0:
                score += 0.20
                if r.get("critical_tier1_count", 0) > 0:
                    score += 0.10  # found critical downstream — high-value answer
            else:
                score += 0.05
        if "get_related_context" in tool_set:
            r = results.get("get_related_context", {})
            if isinstance(r, dict) and (r.get("jira_tickets") or r.get("confluence_pages")):
                score += 0.15
        if "get_schema" in tool_set:
            r = results.get("get_schema", {})
            if isinstance(r, dict) and r.get("columns"):
                score += 0.10
        if "get_data_freshness" in tool_set:
            r = results.get("get_data_freshness", {})
            if isinstance(r, dict) and r.get("last_modified_ms"):
                score += 0.10
        if "search_jira_tickets" in tool_set:
            r = results.get("search_jira_tickets", {})
            if isinstance(r, dict) and r.get("tickets"):
                score += 0.05
        if "get_recent_commits" in tool_set:
            r = results.get("get_recent_commits", {})
            if isinstance(r, dict) and r.get("commits"):
                score += 0.05
        return round(min(score, 1.0), 2)

    # Maps each tool to the upstream source it draws from (for citations).
    _TOOL_SOURCE = {
        "search_metadata": "DataHub", "get_entity_details": "DataHub",
        "get_schema": "DataHub", "get_data_freshness": "DataHub",
        "analyze_impact": "Knowledge Graph", "get_ownership": "Knowledge Graph",
        "get_platform_overview": "Knowledge Graph",
        "read_confluence_page": "Confluence", "get_related_context": "Confluence + Jira",
        "search_jira_tickets": "Jira",
        "get_recent_commits": "GitLab", "read_gitlab_file": "GitLab",
        "get_platform_alerts": "Live Monitor", "get_health_briefing": "Live Monitor",
        "diagnose_entity": "DataHub + GitLab + Jira",
        "get_changes_since": "DataHub + GitLab",
    }

    @staticmethod
    def _citation_footer(tools_called: list) -> str:
        """Deterministic provenance footer: the data sources actually used (no score)."""
        sources = []
        for t in tools_called:
            for s in DataPlatformCopilot._TOOL_SOURCE.get(t["tool"], "").split(" + "):
                if s and s not in sources:
                    sources.append(s)
        if not sources:
            return ""
        return f"\n\n---\n*🔎 Nguồn: {', '.join(sources)}*"

    # ── Trust Layer: live-vs-cache provenance ──────────────────────────────────
    # Tools that attempt a live external fetch (vs pure in-memory graph reads).
    _LIVE_CAPABLE = {
        "search_metadata", "get_entity_details", "get_schema", "get_data_freshness",
        "read_gitlab_file", "read_confluence_page", "get_recent_commits",
        "get_merge_requests", "search_jira_tickets", "diagnose_entity",
        "get_health_briefing", "get_platform_alerts", "get_changes_since",
    }

    @staticmethod
    def _classify_result(result: Any) -> str:
        """Classify a single tool result as 'live' | 'fallback' | 'cached' | None.

        Reads the source markers the tools already emit — no tool changes needed.
        """
        # search_metadata → list of entity dicts carrying per-item `_freshness`
        if isinstance(result, list):
            seen_live = seen_any = False
            for item in result:
                if isinstance(item, dict) and "_freshness" in item:
                    seen_any = True
                    if item["_freshness"].get("source") == "datahub_live":
                        seen_live = True
            if seen_live:
                return "live"
            if seen_any:
                return "fallback"
            return "cached"
        if not isinstance(result, dict):
            return None
        if result.get("_warning") or result.get("partial_result"):
            return "fallback"
        src = result.get("source")
        if src in ("datahub_live", "live"):
            return "live"
        if src in ("cache_only", "unavailable", "cache"):
            return "cached" if src == "cache" else "fallback"
        status = (result.get("status") or "")
        if status.startswith("Fetched live"):
            return "live"
        if "local cache" in status.lower():
            return "fallback"
        return None

    @staticmethod
    def _compute_freshness(tools_called: list) -> dict:
        """Aggregate per-tool provenance into one trust badge for the whole answer."""
        live_sources, fallback_sources = [], []
        any_live_capable = False
        for t in tools_called:
            tool = t["tool"]
            if tool not in DataPlatformCopilot._LIVE_CAPABLE:
                continue
            any_live_capable = True
            cls = DataPlatformCopilot._classify_result(t.get("result"))
            bucket = live_sources if cls == "live" else (
                fallback_sources if cls == "fallback" else None)
            if bucket is None:
                continue
            for s in DataPlatformCopilot._TOOL_SOURCE.get(tool, tool).split(" + "):
                if s and s not in bucket:
                    bucket.append(s)

        if live_sources and not fallback_sources:
            level = "live"
        elif live_sources:
            level = "partial"
        elif any_live_capable and fallback_sources:
            level = "stale"
        else:
            level = "cached"

        labels = {
            "live": "Dữ liệu live",
            "partial": "Live (một phần)",
            "stale": "Cache — nguồn live không phản hồi",
            "cached": "Cache (knowledge graph)",
        }
        return {
            "level": level,
            "label": labels[level],
            "live_sources": live_sources,
            "fallback_sources": fallback_sources,
            "verified_at": datetime.now(timezone.utc).strftime("%H:%M UTC"),
        }

    @staticmethod
    def _build_response(answer: str, tools_called: list, iterations: int, session_id: str = None) -> dict:
        """Build the standardized response envelope returned to main.py."""
        confidence = DataPlatformCopilot._compute_confidence(tools_called)
        if answer and tools_called:
            answer = answer + DataPlatformCopilot._citation_footer(tools_called)
        return {
            "model": os.getenv("LLM_MODEL", "minimax/minimax-m2.5"),
            "answer": answer,
            "tools_called": tools_called,
            "tool_call_count": len(tools_called),
            "llm_iterations": iterations,
            "confidence": confidence,
            "freshness": DataPlatformCopilot._compute_freshness(tools_called),
            "session_id": session_id,
        }
