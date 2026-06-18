"""
Incident Triage / Root-Cause analysis.

`diagnose_entity()` is an agentic orchestration tool: when a user reports that a
table is "stale / chậm / lỗi / có vấn đề", it correlates SEVERAL existing signals
in parallel — data freshness (DataHub), recent pipeline commits (GitLab), open
Jira incidents, and downstream Tier1 impact — then returns STRUCTURED signals +
a likely root cause + recommended actions. The LLM renders the report in the
user's language (so it stays consistent for VN or EN questions).

It reuses verified single-purpose tools (no logic is reimplemented here):
    freshness.get_data_freshness, git_history.get_recent_commits,
    jira_live.search_jira_tickets, impact.analyze_impact,
    discovery.get_related_context.
"""

import asyncio
import logging

logger = logging.getLogger(__name__)

_STALE_HOURS_TIER1 = 48
_STALE_HOURS_OTHER = 72
_LIVE_GATHER_TIMEOUT = 18  # cap on the slow live-API fan-out (seconds)
_DIFF_TIMEOUT = 8          # cap on the smoking-gun commit-diff deep-dive (seconds)
_MAX_UPSTREAM_PROBE = 3    # how many immediate upstream datasets to freshness-probe


def _short_name(entity) -> str:
    name = getattr(entity, "name", "") or ""
    return name.split(".")[-1] if name else ""


def _related_pipeline_names(engine, entity_id: str, entity) -> list:
    """Pipelines that produce or consume this dataset — candidates for the cause."""
    if not engine._lineage_cache_valid:
        engine._build_lineage_cache()
    pipe_ids = set()
    pipe_ids.update(engine._pipeline_produces.get(entity_id, []))
    pipe_ids.update(engine._pipeline_consumes.get(entity_id, []))
    for up in getattr(entity, "upstream", []) or []:
        if "dataFlow" in up:
            pipe_ids.add(up)
    names = []
    for pid in pipe_ids:
        p = engine.get_entity(pid)
        if p and p.name:
            names.append(p.name)
    return names


def _owner_contact(entity) -> dict:
    """Normalize an entity owner (dict or string) into a contact dict."""
    owner = getattr(entity, "owner", None)
    if isinstance(owner, dict):
        return {
            "team": owner.get("team") or owner.get("name"),
            "slack": owner.get("slack"),
            "tech_lead": owner.get("tech_lead"),
        }
    if isinstance(owner, str) and owner:
        return {"team": owner}
    return {}


def _upstream_dataset_ids(entity) -> list:
    """Immediate upstream dataset URNs — candidates for staleness propagation."""
    ups = getattr(entity, "upstream", []) or []
    return [u for u in ups if isinstance(u, str) and u.startswith("urn:li:dataset:")][:_MAX_UPSTREAM_PROBE]


def _age_hours(last_ms) -> float:
    from datetime import datetime, timezone
    return (datetime.now(timezone.utc).timestamp() * 1000 - int(last_ms)) / 3_600_000


_RC_DESC = {
    "upstream_dependency_stale": "An upstream dependency is stale (staleness propagates downstream)",
    "ingestion_pipeline_failed_or_delayed": "The ingestion pipeline failed or is delayed",
    "recent_pipeline_code_change": "A recent pipeline code change",
    "tracked_jira_incident": "A tracked Jira incident",
    "no_significant_anomaly": "No significant anomaly detected",
}


def _build_jira_draft(short, tier, severity, root_cause_desc, blast, owner, smoking_gun) -> dict:
    """Deterministic Jira ticket draft (SUGGESTED — not sent; sending is future F4)."""
    tier1 = tier == "Tier1" or blast.get("tier1_count", 0) > 0
    priority = "P0 - Blocker" if tier1 else ("P1 - Critical" if severity in ("critical", "warning") else "P2 - Major")
    lines = [
        f"*Affected table:* {short} ({tier or 'Untiered'})",
        f"*Likely root cause:* {root_cause_desc}",
        f"*Blast radius:* {blast.get('count', 0)} downstream entities, {blast.get('tier1_count', 0)} Tier1.",
    ]
    if smoking_gun:
        lines.append(
            f"*Suspect change:* commit {smoking_gun.get('sha', '')} by "
            f"{smoking_gun.get('author', '')} — {smoking_gun.get('message', '')}"
        )
    return {
        "project": "PDPDW",
        "issue_type": "Incident",
        "priority": priority,
        "title": f"[Data Incident] {short} — {root_cause_desc[:60]}",
        "description": "\n".join(lines),
        "suggested_assignee": owner.get("tech_lead") or owner.get("team"),
        "labels": ["data-incident", "auto-triaged"] + (["tier1"] if tier1 else []),
    }


def _build_slack_draft(short, channel, root_cause_desc, actions) -> dict:
    """Deterministic Slack alert draft (SUGGESTED — not sent; sending is future F4)."""
    first = next((a for a in actions if a != "no_anomaly_detected"), "investigate")
    return {
        "channel": channel or "#data-platform-oncall",
        "text": (
            f":rotating_light: *{short}* incident detected. "
            f"Likely cause: {root_cause_desc}. "
            f"Suggested first step: {first}. (auto-triaged by Acme DP Copilot)"
        ),
    }


async def diagnose_entity(entity_id: str) -> dict:
    """Autonomous incident investigation — find the REAL culprit, not just the symptom.

    Phases (each bounded so a live demo never hangs):
      1. Local signals: impact / related context / related pipelines.
      2. Live fan-out: freshness of the entity AND its upstream deps, recent commits,
         open Jira — concurrently.
      3. Propagation analysis: if an upstream table is staler than this one, the root
         cause is upstream (symptom vs cause).
      4. Smoking-gun deep-dive: fetch the diff of the most recent suspect commit.
      5. Remediation drafts: a ready-to-file Jira ticket + Slack alert (suggested only).
      6. Verdict + confidence.

    Returns structured signals; the LLM composes the human-facing report in the
    user's language.
    """
    from src.tools.discovery import get_engine, search_metadata, get_related_context, resolve_entity_id
    from src.tools.freshness import get_data_freshness
    from src.tools.git_history import get_recent_commits, get_commit_diff
    from src.tools.jira_live import search_jira_tickets
    from src.tools.impact import analyze_impact

    engine = get_engine()
    entity_id = resolve_entity_id(entity_id)
    entity = engine.get_entity(entity_id)
    if entity is None:
        hits = search_metadata(entity_id)
        if hits:
            entity, entity_id = hits[0], hits[0].id
        else:
            return {"error": f"Entity '{entity_id}' not found. Try a different name."}

    short = _short_name(entity)
    tier = getattr(entity, "tier", None)
    owner = _owner_contact(entity)
    pipelines = _related_pipeline_names(engine, entity_id, entity)
    upstream_ids = _upstream_dataset_ids(entity)
    pipe_slice = pipelines[:2]

    # ── Phase 1: fast, local signals (never block) ──────────────────────────────
    impact = analyze_impact(entity_id)
    context = get_related_context(entity_id) or {}

    # ── Phase 2: live fan-out (entity + upstream freshness + commits + jira) ─────
    freshness, jira, commit_results, upstream_freshness, partial = {}, {}, [], {}, False
    try:
        async def _gather():
            tasks = [get_data_freshness(entity_id), search_jira_tickets(short or entity_id)]
            tasks += [get_recent_commits(p, days=3) for p in pipe_slice]
            tasks += [get_data_freshness(u) for u in upstream_ids]
            return await asyncio.gather(*tasks, return_exceptions=True)

        res = await asyncio.wait_for(_gather(), timeout=_LIVE_GATHER_TIMEOUT)
        ok = lambda x: x if not isinstance(x, Exception) else {}
        freshness, jira = ok(res[0]), ok(res[1])
        commit_results = [ok(c) for c in res[2:2 + len(pipe_slice)]]
        for uid, r in zip(upstream_ids, res[2 + len(pipe_slice):]):
            upstream_freshness[uid] = ok(r)
    except asyncio.TimeoutError:
        partial = True
        logger.warning("diagnose_entity live fan-out timed out for %s", entity_id)

    # ── Build structured signals (language-neutral data) ────────────────────────
    signals = {}
    severity = "info"
    root_causes = []

    # 1) Freshness of the queried entity
    stale = False
    entity_age = None
    if freshness.get("source") == "datahub_live" and freshness.get("last_modified_ms"):
        entity_age = _age_hours(freshness["last_modified_ms"])
        threshold = _STALE_HOURS_TIER1 if tier == "Tier1" else _STALE_HOURS_OTHER
        stale = entity_age > threshold
        signals["freshness"] = {
            "stale": stale, "age_hours": round(entity_age, 1), "threshold_hours": threshold,
            "last_updated": freshness.get("last_modified_human"), "row_count": freshness.get("row_count"),
        }
        if stale:
            severity = "critical" if tier == "Tier1" else "warning"
            root_causes.append("ingestion_pipeline_failed_or_delayed")
    else:
        signals["freshness"] = {"available": False, "note": "DataHub freshness unavailable (cache only)"}

    # 2) Propagation — is an UPSTREAM table the real culprit (staler than this one)?
    root_cause_entity = None
    worst_age = entity_age or 0.0
    for uid, fr in upstream_freshness.items():
        if fr.get("source") == "datahub_live" and fr.get("last_modified_ms"):
            ua = _age_hours(fr["last_modified_ms"])
            if ua > worst_age and ua > _STALE_HOURS_OTHER:
                worst_age = ua
                up_ent = engine.get_entity(uid)
                root_cause_entity = {
                    "id": uid,
                    "name": _short_name(up_ent) if up_ent else uid,
                    "age_hours": round(ua, 1),
                    "tier": getattr(up_ent, "tier", None) if up_ent else None,
                }
    if root_cause_entity:
        root_causes.insert(0, "upstream_dependency_stale")
        severity = "critical" if (tier == "Tier1" or root_cause_entity.get("tier") == "Tier1") else "warning"
        signals["propagation"] = {
            "symptom": short,
            "root_cause_entity": root_cause_entity["name"],
            "note": (
                f"{root_cause_entity['name']} is staler ({root_cause_entity['age_hours']}h) than {short} "
                f"— staleness propagates downstream. Fix the upstream source first."
            ),
        }

    # 3) Recent commits on related pipelines (newest first)
    recent_commits = []
    for cr in commit_results:
        for c in cr.get("commits", []):
            recent_commits.append({"project": cr.get("project"), "id": c.get("id"),
                                   "message": c.get("message"), "author": c.get("author"),
                                   "date": c.get("date")})
    recent_commits.sort(key=lambda c: c.get("date") or "", reverse=True)
    if recent_commits:
        if "recent_pipeline_code_change" not in root_causes:
            root_causes.append("recent_pipeline_code_change")
        severity = severity if severity == "critical" else "warning"
    signals["recent_commits"] = [{k: c[k] for k in ("project", "message", "author", "date")}
                                 for c in recent_commits[:5]]

    # 4) Smoking-gun deep-dive — fetch the diff of the newest suspect commit
    smoking_gun = None
    suspect = recent_commits[0] if recent_commits else None
    if suspect and suspect.get("id") and suspect.get("project") and not partial:
        try:
            diff = await asyncio.wait_for(
                get_commit_diff(suspect["project"], suspect["id"]), timeout=_DIFF_TIMEOUT)
            if diff and not diff.get("error"):
                smoking_gun = {
                    "project": suspect["project"], "sha": suspect["id"],
                    "author": suspect["author"], "date": suspect["date"],
                    "message": suspect["message"],
                    "changed_files": diff.get("changed_files", []),
                    "diff_preview": (diff.get("files") or [{}])[0].get("diff", "")[:800],
                }
                signals["smoking_gun"] = smoking_gun
        except Exception as e:
            logger.debug("smoking-gun diff fetch skipped: %s", e)

    # 5) Open Jira incidents
    open_tickets = [t for t in jira.get("tickets", []) if "done" not in (t.get("status", "").lower())]
    if open_tickets:
        root_causes.append("tracked_jira_incident")
    signals["open_jira_tickets"] = open_tickets[:5]

    # 6) Downstream Tier1 impact
    signals["downstream"] = {"count": impact.get("impact_count", 0),
                             "tier1_count": impact.get("critical_tier1_count", 0)}
    if impact.get("critical_tier1_count", 0) > 0:
        severity = "critical"

    # ── Recommended actions (neutral keys; LLM phrases them per language) ────────
    actions = []
    if root_cause_entity:
        actions.append(f"investigate_upstream:{root_cause_entity['name']}")
    if stale:
        actions += [f"check_pipeline:{p}" for p in pipe_slice] or ["check_ingestion_job"]
    if smoking_gun:
        actions.append(f"review_commit:{smoking_gun['sha']}")
    elif recent_commits:
        actions.append("review_recent_commits_for_schema_change")
    if open_tickets:
        actions.append("track_jira:" + ",".join(t.get("key", "") for t in open_tickets[:3]))
    if impact.get("critical_tier1_count", 0) > 0:
        actions.append("coordinate_owning_team_P0_change_management")
    if not actions:
        actions.append("no_anomaly_detected")

    # ── Verdict + remediation drafts ────────────────────────────────────────────
    likely = root_causes[0] if root_causes else "no_significant_anomaly"
    root_cause_desc = _RC_DESC.get(likely, likely)
    if likely == "upstream_dependency_stale" and root_cause_entity:
        root_cause_desc = f"Upstream table {root_cause_entity['name']} is stale ({root_cause_entity['age_hours']}h)"

    blast = {"count": impact.get("impact_count", 0), "tier1_count": impact.get("critical_tier1_count", 0)}
    jira_draft = slack_draft = None
    if root_causes:
        jira_draft = _build_jira_draft(short, tier, severity, root_cause_desc, blast, owner, smoking_gun)
        slack_draft = _build_slack_draft(short, owner.get("slack"), root_cause_desc, actions)

    confidence = 0.3
    if stale:
        confidence += 0.25
    if root_cause_entity:
        confidence += 0.15
    if smoking_gun:
        confidence += 0.20
    if open_tickets:
        confidence += 0.10
    if blast["tier1_count"] > 0:
        confidence += 0.10
    if partial:
        confidence = min(confidence, 0.5)
    confidence = round(min(confidence, 1.0), 2)

    # Did we actually reach live sources? (drives the Trust Layer badge)
    live_ok = (
        freshness.get("source") == "datahub_live"
        or jira.get("source") == "live"
        or any(c.get("commits") for c in commit_results)
        or any(f.get("source") == "datahub_live" for f in upstream_freshness.values())
    )

    return {
        "entity_id": entity_id,
        "entity_name": short,
        "tier": tier,
        "severity": severity,
        "confidence": confidence,
        "source": "datahub_live" if live_ok else "cache_only",
        "likely_root_cause": likely,
        "root_cause_description": root_cause_desc,
        "root_cause_entity": root_cause_entity,   # the upstream culprit, if propagation found
        "all_hypotheses": root_causes,
        "signals": signals,
        "smoking_gun": smoking_gun,                # the suspect commit + diff, if found
        "recommended_actions": actions,
        "remediation_drafts": {"jira": jira_draft, "slack": slack_draft},
        "related_pipelines": pipelines,
        "related_docs": context.get("confluence_pages", []),
        "partial_result": partial,  # true if live fan-out timed out
        "render_hint": (
            "Present as an autonomous incident investigation IN THE USER'S LANGUAGE: "
            "(1) a severity verdict badge + one-line summary; (2) the likely root cause — if "
            "root_cause_entity is set, say the staleness comes from that UPSTREAM table, not the "
            "queried one; (3) the smoking_gun commit (author, message, changed files) if present; "
            "(4) blast radius; (5) a numbered runbook from recommended_actions; (6) finally show the "
            "remediation_drafts (Jira ticket + Slack message) in fenced code blocks, labeled as "
            "'đề xuất — chưa gửi tự động' (suggested — not auto-sent)."
        ),
    }
