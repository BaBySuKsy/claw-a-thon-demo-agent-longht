import os
import time
import requests
import asyncio
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Cached authenticated DataHub session — avoids a login round-trip on every call
# (the background health check alone freshness-checks 7 Tier1 datasets per scan).
_DH_SESSION = None
_DH_SESSION_TS = 0.0
_DH_TTL = 600  # re-login after 10 minutes


def _datahub_session(base: str, force: bool = False):
    global _DH_SESSION, _DH_SESSION_TS
    if not force and _DH_SESSION is not None and (time.time() - _DH_SESSION_TS) < _DH_TTL:
        return _DH_SESSION
    s = requests.Session()
    s.post(
        f"{base}/logIn",
        json={"username": os.getenv("DATAHUB_USERNAME"), "password": os.getenv("DATAHUB_PASSWORD")},
        timeout=10,
    )
    _DH_SESSION, _DH_SESSION_TS = s, time.time()
    return s


async def get_data_freshness(entity_id: str) -> dict:
    """Get last update time and row count for a dataset from DataHub.
    Falls back to cached entity status if DataHub is unreachable."""
    from src.tools.discovery import resolve_entity_id
    entity_id = resolve_entity_id(entity_id)
    loop = asyncio.get_event_loop()
    base = os.getenv("DATAHUB_BASE_URL", "")

    def _fetch():
        s = _datahub_session(base)
        query = """
        query Freshness($urn: String!) {
          dataset(urn: $urn) {
            properties { lastModified { time } }
            datasetProfiles(limit: 1) { timestampMillis rowCount columnCount }
          }
        }
        """
        payload = {"query": query, "variables": {"urn": entity_id}}
        hdr = {"Content-Type": "application/json"}
        r = s.post(f"{base}/api/graphql", json=payload, headers=hdr, timeout=10)
        if r.status_code in (401, 403):  # cached session expired — re-login once
            s = _datahub_session(base, force=True)
            r = s.post(f"{base}/api/graphql", json=payload, headers=hdr, timeout=10)
        r.raise_for_status()
        return r.json()

    try:
        data = await loop.run_in_executor(None, _fetch)
        ds = ((data.get("data") or {}).get("dataset")) or {}
        props = ds.get("properties") or {}
        profiles = ds.get("datasetProfiles") or []
        last_ms = (props.get("lastModified") or {}).get("time")
        profile = profiles[0] if profiles else {}
        # Temporal layer: record this live observation so "what changed?" queries
        # accumulate history over time (best-effort, never blocks).
        try:
            from src.tools.temporal import record_observation
            record_observation(entity_id, "freshness",
                               {"last_modified_ms": last_ms, "row_count": profile.get("rowCount")})
        except Exception:
            pass
        return {
            "entity_id": entity_id,
            "last_modified_ms": last_ms,
            "last_modified_human": _ms_to_human(last_ms),
            "row_count": profile.get("rowCount"),
            "column_count": profile.get("columnCount"),
            "source": "datahub_live",
        }
    except Exception as e:
        logger.warning("DataHub freshness failed for %s: %s", entity_id, e)
        from src.tools.discovery import get_engine
        engine = get_engine()
        entity = engine.get_entity(entity_id)
        return {
            "entity_id": entity_id,
            "source": "cache_only",
            "status": getattr(entity, "status", "unknown") if entity else "not_found",
            "note": "DataHub unreachable — showing cached status only",
        }


def _ms_to_human(ms) -> str:
    if not ms:
        return None
    return datetime.fromtimestamp(int(ms) / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
