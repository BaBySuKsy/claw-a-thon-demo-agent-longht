import os
import requests
import asyncio
import logging
from datetime import datetime, timedelta
from urllib.parse import quote

logger = logging.getLogger(__name__)

_PREFIXES = ["dataeng/", "dataeng/datainfra/", "dataeng/", ""]

_PROJECT_ID_CACHE = {}


def _base() -> str:
    return os.getenv("GITLAB_BASE_URL", "")


def _headers() -> dict:
    return {
        "PRIVATE-TOKEN": os.getenv("GITLAB_TOKEN", ""),
        "Accept": "application/json",
    }


def _find_project_id(project_name: str) -> int:
    """Resolve a GitLab project name → numeric ID.

    1) Fast path: try known namespace prefixes as an exact path lookup.
    2) Fallback: GitLab search API — resolves a project in ANY namespace by its
       repo name (e.g. credit-curated-etl lives under dataeng/), so we no longer
       depend on hardcoded prefixes. Prefers an exact last-segment match.
    """
    if project_name in _PROJECT_ID_CACHE:
        return _PROJECT_ID_CACHE[project_name]
    # 1) Exact path via known prefixes
    for prefix in _PREFIXES:
        path = quote(f"{prefix}{project_name}", safe="")
        r = requests.get(f"{_base()}/api/v4/projects/{path}", headers=_headers(), timeout=10)
        if r.status_code == 200:
            pid = r.json()["id"]
            _PROJECT_ID_CACHE[project_name] = pid
            return pid
    # 2) Search-API fallback (any namespace)
    r = requests.get(
        f"{_base()}/api/v4/projects",
        headers=_headers(),
        params={"search": project_name, "per_page": 50, "simple": "true"},
        timeout=12,
    )
    if r.status_code == 200 and isinstance(r.json(), list) and r.json():
        results = r.json()
        # exact repo-name match wins; else first result
        match = next((p for p in results if p.get("path") == project_name), results[0])
        pid = match["id"]
        _PROJECT_ID_CACHE[project_name] = pid
        return pid
    raise ValueError(f"GitLab project not found: {project_name}")


async def get_recent_commits(project_name: str, days: int = 7, limit: int = 20) -> dict:
    """Get recent commits from a GitLab project. Returns commit id, message, author, date."""
    loop = asyncio.get_event_loop()
    since = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")

    def _fetch():
        pid = _find_project_id(project_name)
        r = requests.get(
            f"{_base()}/api/v4/projects/{pid}/repository/commits",
            headers=_headers(),
            params={"since": since, "per_page": limit},
            timeout=15,
        )
        r.raise_for_status()
        return r.json()

    try:
        raw = await loop.run_in_executor(None, _fetch)
        commits = [
            {
                "id": c["short_id"],
                "message": c["title"],
                "author": c["author_name"],
                "date": c["committed_date"],
            }
            for c in raw
        ]
        return {"project": project_name, "commits": commits, "days": days, "count": len(commits)}
    except Exception as e:
        logger.error("get_recent_commits(%s): %s", project_name, e)
        return {"error": str(e), "project": project_name, "commits": []}


async def get_commit_diff(project_name: str, sha: str, max_files: int = 6, max_chars: int = 1200) -> dict:
    """Fetch the diff of a single commit — the 'smoking gun' for incident RCA.

    Returns the changed file paths plus a truncated diff snippet per file. Bounded
    output so it never floods the LLM context. Graceful error dict on failure.
    """
    loop = asyncio.get_event_loop()

    def _fetch():
        pid = _find_project_id(project_name)
        r = requests.get(
            f"{_base()}/api/v4/projects/{pid}/repository/commits/{sha}/diff",
            headers=_headers(),
            params={"per_page": max_files},
            timeout=15,
        )
        r.raise_for_status()
        return r.json()

    try:
        raw = await loop.run_in_executor(None, _fetch)
        files = []
        for d in raw[:max_files]:
            path = d.get("new_path") or d.get("old_path", "")
            snippet = (d.get("diff") or "")[:max_chars]
            files.append({
                "path": path,
                "new_file": d.get("new_file", False),
                "deleted_file": d.get("deleted_file", False),
                "renamed_file": d.get("renamed_file", False),
                "diff": snippet,
            })
        return {
            "project": project_name,
            "sha": sha,
            "changed_files": [f["path"] for f in files],
            "files": files,
            "file_count": len(raw),
        }
    except Exception as e:
        logger.error("get_commit_diff(%s, %s): %s", project_name, sha, e)
        return {"error": str(e), "project": project_name, "sha": sha, "files": []}


async def get_merge_requests(project_name: str, state: str = "opened") -> dict:
    """Get open or recently merged MRs — shows in-progress work and breaking changes."""
    loop = asyncio.get_event_loop()

    def _fetch():
        pid = _find_project_id(project_name)
        r = requests.get(
            f"{_base()}/api/v4/projects/{pid}/merge_requests",
            headers=_headers(),
            params={"state": state, "per_page": 10},
            timeout=15,
        )
        r.raise_for_status()
        return [
            {
                "id": m["iid"],
                "title": m["title"],
                "author": m["author"]["name"],
                "state": m["state"],
                "created_at": m["created_at"],
                "source_branch": m["source_branch"],
            }
            for m in r.json()
        ]

    try:
        mrs = await loop.run_in_executor(None, _fetch)
        return {"project": project_name, "merge_requests": mrs, "state": state}
    except Exception as e:
        logger.error("get_merge_requests(%s): %s", project_name, e)
        return {"error": str(e), "project": project_name, "merge_requests": []}
