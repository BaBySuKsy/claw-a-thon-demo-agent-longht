import os
import json
import asyncio
import logging
from pathlib import Path
from atlassian import Jira

logger = logging.getLogger(__name__)
_JIRA_DIR = Path("src/data_platform/cache/jira")


async def search_jira_tickets(query: str, status: str = None, limit: int = 10) -> dict:
    """Search Jira tickets live via JQL. Falls back to local cache on failure."""
    jql = f'project in (PCDCM, PDPDW) AND text ~ "{query}"'
    if status:
        jql += f' AND status = "{status}"'
    jql += " ORDER BY updated DESC"

    loop = asyncio.get_event_loop()
    try:
        client = Jira(
            url=os.getenv("JIRA_URL", ""),
            token=os.getenv("JIRA_TOKEN") or os.getenv("JIRA_API_TOKEN"),
            cloud=False,
        )
        result = await loop.run_in_executor(None, lambda: client.jql(jql, limit=limit))
        tickets = [
            {
                "key": i["key"],
                "summary": i["fields"].get("summary", ""),
                "status": i["fields"].get("status", {}).get("name", ""),
                "assignee": (i["fields"].get("assignee") or {}).get("displayName", "Unassigned"),
                "type": i["fields"].get("issuetype", {}).get("name", ""),
                "updated": i["fields"].get("updated", ""),
            }
            for i in result.get("issues", [])
        ]
        return {
            "tickets": tickets,
            "total": result.get("total", len(tickets)),
            "source": "live",
            "jql": jql,
        }
    except Exception as e:
        logger.warning("Live Jira search failed, using cache: %s", e)
        return _cache_search(query, status, limit)


def _cache_search(query: str, status: str, limit: int) -> dict:
    """Fallback: full-text search across cached Jira JSON files."""
    q = query.lower()
    tickets = []
    for path in sorted(_JIRA_DIR.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            # Check epic summary
            if q in data.get("summary", "").lower() or q in (data.get("description") or "").lower():
                tickets.append({
                    "key": data.get("epic_key", ""),
                    "summary": data.get("summary", ""),
                    "status": data.get("status", ""),
                    "type": "Epic",
                })
            # Check child tickets
            for t in data.get("tickets", []):
                text = (t.get("summary", "") + " " + (t.get("description") or "")).lower()
                if q in text:
                    if not status or status.lower() in t.get("status", "").lower():
                        tickets.append({
                            "key": t.get("ticket_key", ""),
                            "summary": t.get("summary", ""),
                            "status": t.get("status", ""),
                            "type": t.get("issuetype", ""),
                            "assignee": (t.get("assignee") or {}).get("name", ""),
                        })
        except Exception:
            pass
    return {"tickets": tickets[:limit], "total": len(tickets), "source": "cache"}
