"""
Temporal knowledge layer (Graphiti-inspired).

A static catalog can only tell you the CURRENT state. This layer adds the time
dimension so the agent can answer "what changed recently?" — schema drift, fresh-
ness regressions, recent commits — which is what actually breaks downstream jobs.

Two parts:
  1. record_observation(): append-only, bi-temporal observation log (best-effort,
     never blocks or raises — it only enriches future "what changed" answers).
  2. get_changes_since(): aggregate everything that changed in a recent window from
     LIVE sources + the observation log. The seed/cached schema acts as the "past
     snapshot", so schema-drift detection works from day one.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

_HISTORY_DIR = Path("src/data_platform/history")
_OBS_LOG = _HISTORY_DIR / "observations.jsonl"
_MAX_OBS_SCAN = 5000      # cap lines read back from the log
_PROBE_LIMIT = 5          # how many monitored datasets to probe live per call
_CHANGES_TIMEOUT = 20     # cap (s) on the live fan-out


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def record_observation(entity_id: str, kind: str, value, observed_at: str = None) -> None:
    """Append a timestamped observation to the log. Best-effort; never raises.

    kind ∈ {"freshness", "schema"}. Called opportunistically from the live tools
    so the temporal graph grows as the agent is used.
    """
    try:
        _HISTORY_DIR.mkdir(parents=True, exist_ok=True)
        rec = {
            "entity_id": entity_id,
            "kind": kind,
            "value": value,
            "observed_at": observed_at or _now_iso(),
        }
        with open(_OBS_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")
    except Exception as e:  # logging only — temporal recording must never break a tool
        logger.debug("record_observation failed for %s: %s", entity_id, e)


# ── Schema-drift comparator ─────────────────────────────────────────────────────

def _col_map(columns) -> dict:
    """Normalize a column list (DataHub / seed formats) → {name: type}."""
    out = {}
    for c in columns or []:
        if isinstance(c, dict):
            name = c.get("name") or c.get("fieldPath") or c.get("column")
            typ = c.get("type") or c.get("dataType") or c.get("nativeDataType") or ""
            if name:
                out[str(name)] = str(typ)
        elif isinstance(c, str):
            out[c] = ""
    return out


def diff_schema(old_columns, new_columns) -> dict:
    """Compare two column lists → {added, removed, type_changed}."""
    old, new = _col_map(old_columns), _col_map(new_columns)
    added = [{"name": n, "type": new[n]} for n in new if n not in old]
    removed = [{"name": n, "type": old[n]} for n in old if n not in new]
    type_changed = [{"name": n, "from": old[n], "to": new[n]}
                    for n in new if n in old and old[n] and new[n] and old[n] != new[n]]
    return {"added": added, "removed": removed, "type_changed": type_changed}


def _recent_observations(hours: int) -> list:
    """Read back observations from the log within the window."""
    if not _OBS_LOG.exists():
        return []
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    out = []
    try:
        lines = _OBS_LOG.read_text(encoding="utf-8").splitlines()[-_MAX_OBS_SCAN:]
        for ln in lines:
            try:
                rec = json.loads(ln)
                t = datetime.strptime(rec.get("observed_at", ""), "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
                if t >= cutoff:
                    out.append({"entity_id": rec.get("entity_id"), "kind": rec.get("kind"),
                                "observed_at": rec.get("observed_at")})
            except Exception:
                continue
    except Exception as e:
        logger.debug("reading observation log failed: %s", e)
    return out


async def get_changes_since(scope: str = None, hours: int = 24) -> dict:
    """What changed across the Data Platform in the last `hours`?

    Aggregates LIVE signals + the observation log:
      - schema_drift: live DataHub schema vs the seed/cached schema (potentially breaking)
      - newly_stale_tier1: Tier1 tables now past their freshness threshold
      - recent_commits: commits on critical pipelines in the window
      - logged_observations: recent entries from the temporal log

    Bounded by a timeout so a live demo never hangs.
    """
    from src.tools.monitor import _MONITORED_DATASETS, _CRITICAL_PIPELINES, TIER1_STALE_HOURS
    from src.tools.discovery import get_engine, get_schema
    from src.tools.freshness import get_data_freshness
    from src.tools.git_history import get_recent_commits

    engine = get_engine()
    days = max(1, round(hours / 24))

    monitored = _MONITORED_DATASETS
    if scope:
        needle = scope.lower()
        monitored = [m for m in _MONITORED_DATASETS if needle in m[1].lower()] or _MONITORED_DATASETS
    probe = monitored[:_PROBE_LIMIT]

    live_seen = {"v": False}  # did ANY probe get a live response? (drives the trust badge)

    async def _schema_drift_one(entity_id, name):
        ent = engine.get_entity(entity_id)
        seed_cols = (getattr(ent, "metadata", None) or {}).get("schema") if ent else None
        if not seed_cols:
            return None
        live = await get_schema(entity_id)
        if live.get("source") == "datahub_live":
            live_seen["v"] = True
            d = diff_schema(seed_cols, live.get("columns", []))
            if d["added"] or d["removed"] or d["type_changed"]:
                return {"entity": name, "entity_id": entity_id, **d}
        return None

    async def _fresh_one(entity_id, name):
        fr = await get_data_freshness(entity_id)
        if fr.get("source") == "datahub_live":
            live_seen["v"] = True
            if fr.get("last_modified_ms"):
                age = (datetime.now(timezone.utc).timestamp() * 1000 - int(fr["last_modified_ms"])) / 3_600_000
                if age > TIER1_STALE_HOURS:
                    return {"entity": name, "age_hours": round(age, 1),
                            "last_updated": fr.get("last_modified_human")}
        return None

    schema_drift, newly_stale, recent_commits, partial = [], [], [], False
    try:
        n = len(probe)
        tasks = [_schema_drift_one(eid, nm) for eid, nm, _ in probe]
        tasks += [_fresh_one(eid, nm) for eid, nm, _ in probe]
        tasks += [get_recent_commits(p, days=days) for p in _CRITICAL_PIPELINES]
        res = await asyncio.wait_for(asyncio.gather(*tasks, return_exceptions=True),
                                     timeout=_CHANGES_TIMEOUT)
        for r in res[:n]:
            if isinstance(r, dict) and r:
                schema_drift.append(r)
        for r in res[n:2 * n]:
            if isinstance(r, dict) and r:
                newly_stale.append(r)
        for r in res[2 * n:]:
            if isinstance(r, dict) and r.get("commits"):
                for c in r["commits"]:
                    recent_commits.append({"project": r.get("project"),
                                           "message": c.get("message"),
                                           "author": c.get("author"), "date": c.get("date")})
    except asyncio.TimeoutError:
        partial = True
        logger.warning("get_changes_since live fan-out timed out")

    logged = _recent_observations(hours)
    total = len(schema_drift) + len(newly_stale) + len(recent_commits)

    return {
        "window_hours": hours,
        "scope": scope,
        "change_count": total,
        # Surfaced for the Trust Layer badge: did we actually reach live sources?
        "source": "datahub_live" if live_seen["v"] else "cache_only",
        "changes": {
            "schema_drift": schema_drift,
            "newly_stale_tier1": newly_stale,
            "recent_commits": recent_commits[:10],
            "logged_observations": logged[:10],
        },
        "partial_result": partial,
        "render_hint": (
            "Present as a 'what changed recently' digest IN THE USER'S LANGUAGE. Lead with the change "
            "count + window, then group: SCHEMA DRIFT (columns added/removed/type-changed — flag these "
            "as POTENTIALLY BREAKING for downstream jobs), NEWLY STALE Tier1 tables, and RECENT pipeline "
            "commits. If a schema change could break downstream, say so explicitly and suggest "
            "analyze_impact. If nothing changed, say so positively."
        ),
    }
