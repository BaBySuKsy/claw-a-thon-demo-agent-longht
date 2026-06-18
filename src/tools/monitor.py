"""
Proactive platform health monitor.

Background mode: run_health_check() is called every 30 min by main.py's
alert loop and results are stored in _alert_store.

On-demand mode: get_platform_alerts() returns the current store contents,
called as a tool by the copilot when the user asks about platform health.
"""

import hashlib
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

MAX_ALERTS = 50
TIER1_STALE_HOURS = 48
TIER2_STALE_HOURS = 72

_alert_store: list = []
_last_check_time: str = None

_MONITORED_DATASETS = [
    ("urn:li:dataset:(urn:li:dataPlatform:hdfs,acme.analytics.warehouse.bank_code_mapping,PROD)", "bank_code_mapping", "Tier1"),
    ("urn:li:dataset:(urn:li:dataPlatform:hdfs,acme.analytics.warehouse.identity_mart,PROD)", "identity_mart", "Tier1"),
    ("urn:li:dataset:(urn:li:dataPlatform:hdfs,acme.secure.lending_svc.installment.loan_core_account,PROD)", "loan_core_account", "Tier1"),
    ("urn:li:dataset:(urn:li:dataPlatform:hdfs,acme.secure.lending_svc.installment.loan_core_bill,PROD)", "loan_core_bill", "Tier1"),
    ("urn:li:dataset:(urn:li:dataPlatform:hdfs,acme.secure.lending_svc.installment.loan_core_order,PROD)", "loan_core_order", "Tier1"),
    ("urn:li:dataset:(urn:li:dataPlatform:hdfs,acme.secure.lending_svc.installment.loan_core_statement,PROD)", "loan_core_statement", "Tier1"),
    ("urn:li:dataset:(urn:li:dataPlatform:hdfs,acme.secure.lending_svc.installment.loan_core_user,PROD)", "loan_core_user", "Tier1"),
]

_CRITICAL_PIPELINES = ["credit-curated-etl"]


def _alert_id(entity_id: str, alert_type: str) -> str:
    return hashlib.sha1(f"{entity_id}:{alert_type}".encode()).hexdigest()[:12]


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


async def run_health_check() -> list:
    """
    Scan Tier1 datasets + critical pipelines + Jira for health issues.
    Deduplicates by alert ID and trims store to MAX_ALERTS.
    Returns list of newly added alerts.
    """
    global _last_check_time
    from src.tools.freshness import get_data_freshness
    from src.tools.git_history import get_recent_commits
    from src.tools.jira_live import search_jira_tickets

    candidates = []
    now_ms = datetime.now(timezone.utc).timestamp() * 1000

    # 1 — Dataset freshness check
    for entity_id, name, tier in _MONITORED_DATASETS:
        try:
            freshness = await get_data_freshness(entity_id)
            if freshness.get("source") != "datahub_live":
                continue
            last_ms = freshness.get("last_modified_ms")
            if not last_ms:
                continue
            age_hours = (now_ms - int(last_ms)) / 3_600_000
            threshold = TIER1_STALE_HOURS if tier == "Tier1" else TIER2_STALE_HOURS
            if age_hours > threshold:
                candidates.append({
                    "id": _alert_id(entity_id, "stale_data"),
                    "severity": "critical" if tier == "Tier1" else "warning",
                    "type": "stale_data",
                    "entity_id": entity_id,
                    "entity_name": name,
                    "message": (
                        f"{name} has not been updated in {age_hours:.1f}h "
                        f"(threshold: {threshold}h). "
                        f"Last updated: {freshness.get('last_modified_human', 'unknown')}."
                    ),
                    "suggested_action": (
                        f"Check the Airflow DAG feeding {name}. "
                        "Verify run status and look for failed tasks."
                    ),
                    "detected_at": _now_iso(),
                })
        except Exception as e:
            logger.debug("Freshness check failed for %s: %s", name, e)

    # 2 — Pipeline commit activity (last 24h signals risk)
    for pipeline_name in _CRITICAL_PIPELINES:
        try:
            result = await get_recent_commits(pipeline_name, days=1)
            commits = result.get("commits", [])
            if commits:
                preview = "; ".join(c["message"][:60] for c in commits[:3])
                candidates.append({
                    "id": _alert_id(pipeline_name, "pipeline_change"),
                    "severity": "warning",
                    "type": "pipeline_change",
                    "entity_id": f"pipeline:{pipeline_name}",
                    "entity_name": pipeline_name,
                    "message": (
                        f"{len(commits)} commit(s) pushed to {pipeline_name} in the last 24h. "
                        f"Recent: {preview}"
                    ),
                    "suggested_action": (
                        "Review commits for schema or logic changes before the next scheduled run."
                    ),
                    "detected_at": _now_iso(),
                })
        except Exception as e:
            logger.debug("Commit check failed for %s: %s", pipeline_name, e)

    # 3 — Open Jira incidents
    try:
        result = await search_jira_tickets("data platform", status="In Progress", limit=5)
        for ticket in result.get("tickets", []):
            key = ticket.get("key", "")
            candidates.append({
                "id": _alert_id(key, "open_incident"),
                "severity": "info",
                "type": "open_incident",
                "entity_id": key,
                "entity_name": key,
                "message": (
                    f"Open incident [{key}]: {ticket.get('summary', '')} "
                    f"(assignee: {ticket.get('assignee', 'Unassigned')})"
                ),
                "suggested_action": f"Check Jira {key} for current impact and resolution status.",
                "detected_at": _now_iso(),
            })
    except Exception as e:
        logger.debug("Jira incident check failed: %s", e)

    # 4 — Dedup and store (asyncio is single-threaded, no lock needed)
    existing_ids = {a["id"] for a in _alert_store}
    new_alerts = [a for a in candidates if a["id"] not in existing_ids]
    _alert_store.extend(new_alerts)
    if len(_alert_store) > MAX_ALERTS:
        del _alert_store[:len(_alert_store) - MAX_ALERTS]

    _last_check_time = _now_iso()
    logger.info(
        "Health check done: %d new alert(s), %d total in store",
        len(new_alerts), len(_alert_store),
    )
    return new_alerts


async def get_health_briefing() -> dict:
    """Generate a 'Daily Data Health Briefing' — a proactive digest the agent can
    deliver on demand. Runs a fresh health check, then summarizes: Tier1 freshness
    status, open incidents, and recent risky pipeline commits. Showcases autonomy.
    """
    try:
        await run_health_check()
    except Exception as e:
        logger.warning("Briefing health check failed: %s", e)

    alerts = list(_alert_store)
    by_type = {"stale_data": [], "pipeline_change": [], "open_incident": []}
    for a in alerts:
        by_type.setdefault(a.get("type"), []).append(a)

    sev = {"critical": 0, "warning": 0, "info": 0}
    for a in alerts:
        sev[a.get("severity", "info")] = sev.get(a.get("severity", "info"), 0) + 1

    overall = "healthy" if sev["critical"] == 0 and sev["warning"] == 0 else (
        "critical" if sev["critical"] > 0 else "needs_attention")

    return {
        "briefing_type": "daily_data_health",
        "generated_at": _last_check_time or _now_iso(),
        "overall_status": overall,
        "monitored_tier1_datasets": len(_MONITORED_DATASETS),
        "critical_pipelines": _CRITICAL_PIPELINES,
        "summary": {
            "stale_tier1_tables": [a["entity_name"] for a in by_type.get("stale_data", [])],
            "recent_pipeline_changes": [a["entity_name"] for a in by_type.get("pipeline_change", [])],
            "open_incidents": [a["entity_name"] for a in by_type.get("open_incident", [])],
            "alert_counts": sev,
        },
        "alerts": alerts,
        "render_hint": "Present as a concise morning briefing IN THE USER'S LANGUAGE: "
                       "overall status badge, then any stale Tier1 tables, recent risky commits, "
                       "open incidents, each with the suggested action. If all clear, say so positively.",
    }


def get_platform_alerts(severity: str = None, entity_id: str = None) -> dict:
    """Return current alerts from the store, optionally filtered by severity or entity."""
    alerts = list(_alert_store)

    if severity:
        alerts = [a for a in alerts if a.get("severity") == severity]
    if entity_id:
        needle = entity_id.lower()
        alerts = [
            a for a in alerts
            if needle in a.get("entity_id", "").lower()
            or needle in a.get("entity_name", "").lower()
        ]

    last = _last_check_time or "not yet run"
    if not alerts:
        return {
            "alerts": [],
            "total": 0,
            "message": f"No active alerts. Last check: {last}",
            "last_check": last,
        }

    by_sev = {"critical": 0, "warning": 0, "info": 0}
    for a in alerts:
        by_sev[a.get("severity", "info")] = by_sev.get(a.get("severity", "info"), 0) + 1

    return {
        "alerts": alerts,
        "total": len(alerts),
        "critical_count": by_sev["critical"],
        "warning_count": by_sev["warning"],
        "info_count": by_sev["info"],
        "last_check": last,
    }
