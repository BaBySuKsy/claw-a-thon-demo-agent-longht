#!/usr/bin/env python3
"""Dev-only smoke test: call all 16 LLM tools + get_commit_diff + get_merge_requests
with seeded args against the synthetic dataset. Run offline (no env) so every live
call falls back to cache — mirrors the public/PUBLIC-mode agent. Prints PASS/FAIL."""
import sys, json, asyncio, inspect
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.tools.discovery import (get_engine, search_metadata, get_ownership,
    get_platform_overview, get_entity_details, get_related_context,
    read_gitlab_file, read_confluence_page, get_schema)
from src.tools.impact import analyze_impact
from src.tools.triage import diagnose_entity
from src.tools.jira_live import search_jira_tickets
from src.tools.git_history import get_recent_commits, get_commit_diff, get_merge_requests
from src.tools.freshness import get_data_freshness
from src.tools.monitor import get_platform_alerts, get_health_briefing
from src.tools.temporal import get_changes_since

DP = Path("src/data_platform")
PAGE_ID = json.loads((DP / "confluence_index.json").read_text())[0]["page_id"]
CREDIT_SHA = json.loads((DP / "cache/gitlab/credit-curated-etl/_commits.json").read_text())[0]["short_id"]

async def call(fn, *a, **k):
    r = fn(*a, **k)
    return await r if inspect.isawaitable(r) else r

def nonempty(r):
    if isinstance(r, dict):
        if "error" in r:
            return False
        return any(v for k, v in r.items() if k not in ("error", "source"))
    return bool(r)

CASES = [
    ("search_metadata",       lambda: call(search_metadata, "loan statement")),
    ("get_platform_overview", lambda: call(get_platform_overview)),
    ("get_ownership",         lambda: call(get_ownership, "loan_core_account")),
    ("get_entity_details",    lambda: call(get_entity_details, "loan_core_statement")),
    ("analyze_impact",        lambda: call(analyze_impact, "loan_core_statement")),
    ("diagnose_entity",       lambda: call(diagnose_entity, "loan_statement_fact")),
    ("get_related_context",   lambda: call(get_related_context, "loan_statement_fact")),
    ("read_gitlab_file",      lambda: call(read_gitlab_file, "credit-curated-etl", "dags/credit_curated_etl.py")),
    ("read_confluence_page",  lambda: call(read_confluence_page, PAGE_ID)),
    ("search_jira_tickets",   lambda: call(search_jira_tickets, "loan_statement")),
    ("get_recent_commits",    lambda: call(get_recent_commits, "credit-curated-etl")),
    ("get_data_freshness",    lambda: call(get_data_freshness, "loan_core_statement")),
    ("get_schema",            lambda: call(get_schema, "loan_core_statement")),
    ("get_platform_alerts",   lambda: call(get_platform_alerts)),
    ("get_health_briefing",   lambda: call(get_health_briefing)),
    ("get_changes_since",     lambda: call(get_changes_since, None, 72)),
    ("get_commit_diff",       lambda: call(get_commit_diff, "credit-curated-etl", CREDIT_SHA)),
    ("get_merge_requests",    lambda: call(get_merge_requests, "credit-curated-etl")),
]

async def main():
    eng = get_engine()
    print(f"engine: {len(eng.entities)} entities, {len(eng.relationships)} relationships\n")
    npass = 0
    extra = {}
    for name, thunk in CASES:
        try:
            r = await thunk()
            ok = nonempty(r)
            # capture a few signal fields
            if name == "analyze_impact" and isinstance(r, dict):
                extra[name] = f"impact={r.get('impact_count')} cross_team={r.get('cross_team_count')}"
            elif name == "diagnose_entity" and isinstance(r, dict):
                extra[name] = f"smoking_gun={'YES' if r.get('signals',{}).get('smoking_gun') or r.get('smoking_gun') else 'no'} severity={r.get('severity')}"
            elif name == "get_related_context" and isinstance(r, dict):
                extra[name] = f"jira={r.get('jira_ticket_count')} confluence={r.get('confluence_page_count')}"
            elif name == "search_jira_tickets" and isinstance(r, dict):
                extra[name] = f"source={r.get('source')} total={r.get('total')}"
            elif name == "get_recent_commits" and isinstance(r, dict):
                extra[name] = f"source={r.get('source')} count={r.get('count')}"
            print(f"  {'PASS' if ok else 'FAIL'}  {name:24} {extra.get(name,'')}")
            npass += ok
        except Exception as e:
            print(f"  ERR   {name:24} {type(e).__name__}: {e}")
    print(f"\n{npass}/{len(CASES)} tools returned non-empty, no-error payloads")
    sys.exit(0 if npass == len(CASES) else 1)

if __name__ == "__main__":
    asyncio.run(main())
