import logging
import json
import asyncio
from pathlib import Path
from typing import Optional

from src.core.engine import KnowledgeEngine
from src.core.schema import Dataset, Pipeline, KnowledgeArticle, Team, Domain
from src.tools.cross_source import build_cross_source_index, get_entity_context

logger = logging.getLogger(__name__)

# ── Module-level singleton (BUG-05: prevents reload on every tool call) ────────
_engine: Optional[KnowledgeEngine] = None

_TIER_ORDER = {"Tier1": 0, "Tier2": 1, "Tier3": 2}

# ── Normalizers (BUG-01: bridge JSON format → dataclass fields) ────────────────

def _normalize_dataset(d: dict) -> dict:
    """Transform datasets.json entry → Dataset dataclass kwargs."""
    d = dict(d)
    d.setdefault("type", d.pop("entityType", "dataset"))
    lineage = d.pop("lineage", {})
    d.setdefault("upstream", lineage.get("upstream", []))
    d.setdefault("downstream", lineage.get("downstream", []))
    schema_data = d.pop("schema", None)
    if schema_data:
        meta = d.get("metadata", {})
        meta["schema"] = schema_data
        d["metadata"] = meta
    return d


def _normalize_pipeline(d: dict) -> dict:
    """Transform pipelines.json entry → Pipeline dataclass kwargs."""
    d = dict(d)
    d.setdefault("type", d.pop("entityType", "pipeline"))
    lineage = d.pop("lineage", {})
    d.setdefault("inputs", lineage.get("upstream", []))
    d.setdefault("outputs", lineage.get("downstream", []))
    extra = {}
    for key in ("directory_structure", "files"):
        val = d.pop(key, None)
        if val is not None:
            extra[key] = val
    if extra:
        meta = d.get("metadata", {})
        meta.update(extra)
        d["metadata"] = meta
    return d


def _normalize_article(d: dict) -> dict:
    """Transform confluence_knowledge.json entry → KnowledgeArticle dataclass kwargs."""
    d = dict(d)
    d.setdefault("type", d.pop("entityType", "knowledge_article"))
    # Only keep fields defined in KnowledgeArticle dataclass
    allowed = {"id", "name", "type", "description", "owner", "domain", "tier",
               "status", "tags", "metadata", "page_id", "content_chunks", "relations"}
    return {k: v for k, v in d.items() if k in allowed}


def _normalize_domain(d: dict) -> dict:
    """Transform domains.json entry → Domain dataclass kwargs."""
    d = dict(d)
    d.setdefault("type", d.pop("entityType", "domain"))
    allowed = {"id", "name", "type", "description", "owner", "domain", "tier",
               "status", "tags", "metadata", "teams"}
    return {k: v for k, v in d.items() if k in allowed}


def _normalize_team(d: dict) -> dict:
    """Transform teams.json entry → Team dataclass kwargs."""
    d = dict(d)
    d.setdefault("type", d.pop("entityType", "team"))
    allowed = {"id", "name", "type", "description", "owner", "domain", "tier",
               "status", "tags", "metadata", "members", "projects"}
    return {k: v for k, v in d.items() if k in allowed}


# ── Engine builder ─────────────────────────────────────────────────────────────

def load_data_platform_engine() -> KnowledgeEngine:
    """Build a fresh KnowledgeEngine from all JSON data files."""
    engine = KnowledgeEngine()

    with open("src/data_platform/datasets.json", "r", encoding="utf-8") as f:
        for d in json.load(f):
            try:
                engine.add_entity(Dataset(**_normalize_dataset(d)))
            except TypeError:
                pass  # Skip malformed entries

    with open("src/data_platform/pipelines.json", "r", encoding="utf-8") as f:
        for p in json.load(f):
            try:
                engine.add_entity(Pipeline(**_normalize_pipeline(p)))
            except TypeError:
                pass

    confluence_path = Path("src/data_platform/confluence_knowledge.json")
    if confluence_path.exists():
        with open(confluence_path, "r", encoding="utf-8") as f:
            for a in json.load(f):
                try:
                    engine.add_entity(KnowledgeArticle(**_normalize_article(a)))
                except TypeError:
                    pass

    # Load business domains + owning teams (onboarding grounding)
    domains_path = Path("src/data_platform/domains.json")
    if domains_path.exists():
        with open(domains_path, "r", encoding="utf-8") as f:
            for dom in json.load(f):
                try:
                    engine.add_entity(Domain(**_normalize_domain(dom)))
                except TypeError:
                    pass

    teams_path = Path("src/data_platform/teams.json")
    if teams_path.exists():
        with open(teams_path, "r", encoding="utf-8") as f:
            for tm in json.load(f):
                try:
                    engine.add_entity(Team(**_normalize_team(tm)))
                except TypeError:
                    pass

    # Cross-team consumer datasets: tables owned by OTHER teams (Risk/Fraud/Finance/
    # Collection) that consume Data-Platform lending marts. Loaded as normal Dataset
    # entities, then their edges are wired into the mart.downstream IN MEMORY so
    # analyze_impact's downstream BFS surfaces the cross-team blast radius. datasets.json
    # stays untouched (clean, reversible).
    cross_team_path = Path("src/data_platform/cross_team.json")
    if cross_team_path.exists():
        with open(cross_team_path, "r", encoding="utf-8") as f:
            ct = json.load(f)
        for d in ct.get("consumer_datasets", []):
            try:
                engine.add_entity(Dataset(**_normalize_dataset(d)))
            except TypeError:
                pass
        for edge in ct.get("edges", []):
            src = engine.get_entity(edge.get("from"))
            tgt_id = edge.get("to")
            if src is not None and hasattr(src, "downstream") and tgt_id not in src.downstream:
                src.downstream.append(tgt_id)

    # Wire cross-source relationships: Confluence tree ↔ DataHub, Jira ↔ DataHub/GitLab
    build_cross_source_index(engine)

    return engine


def get_engine() -> KnowledgeEngine:
    """Return the module-level singleton KnowledgeEngine (lazy init)."""
    global _engine
    if _engine is None:
        _engine = load_data_platform_engine()
        from src.tools.semantic import get_bm25_index
        get_bm25_index(_engine)  # build BM25 index at startup
    return _engine


# ── Tool implementations ───────────────────────────────────────────────────────

_FUZZY_MIN_RESULTS = 3  # below this, trigger fuzzy fallback for typo resilience


def search_metadata(query: str, limit: int = 15) -> list:
    engine = get_engine()
    from src.tools.semantic import get_bm25_index, _normalize
    results = get_bm25_index(engine).search(query, top_k=limit * 2)
    seen, deduped = set(), []
    for e in results:
        if e.id not in seen:
            seen.add(e.id)
            deduped.append(e)

    # Fuzzy fallback (RAGFlow-style exact→partial→fuzzy): when BM25 returns too few
    # hits — e.g. the user typed "credit statment" — match against entity short-names
    # with difflib (stdlib, no extra dependency). Appended AFTER BM25 hits so exact/
    # semantic matches always rank first; dedup prevents duplicates.
    if len(deduped) < _FUZZY_MIN_RESULTS:
        import difflib
        nq = _normalize(query)
        candidates = []  # (score, entity)
        for e in engine.entities.values():
            if e.id in seen:
                continue
            short = (e.name or "").split(".")[-1]
            for cand in {_normalize(short), _normalize(e.name or "")}:
                if not cand:
                    continue
                # substring match → strong; else ratio-based fuzzy
                if nq and nq in cand:
                    candidates.append((0.95, e))
                    break
                ratio = difflib.SequenceMatcher(None, nq, cand).ratio()
                if ratio >= 0.6:
                    candidates.append((ratio, e))
                    break
        candidates.sort(key=lambda x: -x[0])
        for _score, e in candidates:
            if e.id not in seen:
                seen.add(e.id)
                deduped.append(e)
            if len(deduped) >= limit:
                break

    deduped.sort(key=lambda e: _TIER_ORDER.get(getattr(e, "tier", None) or "", 3))
    return deduped[:limit]


# ── Multi-query retrieval (Reciprocal Rank Fusion) ─────────────────────────────
# Generic words that carry no entity signal — excluded from sub-query generation so
# we don't waste a fusion slot searching for "what" / "bảng" / "của".
_QUERY_STOPWORDS = {
    # English
    "what", "which", "who", "where", "when", "how", "the", "and", "for", "are",
    "is", "of", "to", "in", "on", "do", "does", "show", "me", "list", "all",
    "table", "tables", "dataset", "datasets", "find", "get", "about", "with",
    # Vietnamese (normalized, no diacritics)
    "la", "gi", "nao", "cho", "cua", "co", "cac", "nhung", "bang", "bao",
    "nhieu", "the", "ai", "o", "va", "tim", "liet", "ke", "thong", "tin",
    "ve", "voi", "hay", "duoc", "khong", "mot", "nay", "do",
}

_RRF_K = 60          # standard RRF damping constant
_MAX_QUERY_VARIANTS = 5  # cap fan-out so fusion stays bounded


def _query_variants(query: str, max_variants: int = _MAX_QUERY_VARIANTS) -> list:
    """Generate cheap, deterministic query variants for multi-angle retrieval.

    variant[0] is always the FULL original query (its hits dominate via RRF).
    Then each significant content token becomes its own focused sub-query — this
    is what rescues multi-concept questions like "ai sở hữu bảng thanh toán qrpay",
    where a single BM25 pass dilutes the score across every token. All searches are
    in-memory (instant), so adding variants costs no latency.
    """
    from src.tools.semantic import _normalize
    variants = [query]
    seen = {_normalize(query)}  # dedup against the full query (single-token queries)
    for tok in _normalize(query).split():
        if len(tok) < 3 or tok in _QUERY_STOPWORDS or tok in seen:
            continue
        seen.add(tok)
        variants.append(tok)
        if len(variants) >= max_variants:
            break
    return variants


def search_metadata_multi(query: str, limit: int = 15) -> list:
    """Multi-query retrieval with Reciprocal Rank Fusion (RRF).

    Runs the full query plus a few focused sub-queries, then fuses their ranked
    lists: an entity surfaced by several angles (or ranked high by the full query)
    rises to the top. Boosts recall on multi-concept / paraphrased questions while
    keeping the full-query signal dominant. Falls back to single-query results if
    fusion yields nothing. Tier is the tie-breaker so Tier1 still wins on ties.
    """
    from src.tools.semantic import _normalize
    variants = _query_variants(query)
    if len(variants) <= 1:
        return search_metadata(query, limit=limit)

    rrf_scores: dict = {}
    entity_by_id: dict = {}
    for variant in variants:
        for rank, e in enumerate(search_metadata(variant, limit=limit)):
            rrf_scores[e.id] = rrf_scores.get(e.id, 0.0) + 1.0 / (_RRF_K + rank)
            entity_by_id[e.id] = e

    if not entity_by_id:
        return search_metadata(query, limit=limit)

    # Instant precision rerank (no LLM round-trip): when the user typed something
    # that matches an entity's short-name, float it to the top. An exact short-name
    # match (user typed the table name) gets a strong boost that dominates RRF; a
    # token-substring match gets a gentle nudge (~one RRF hit).
    q_tokens = {
        t for t in _normalize(query).split()
        if len(t) >= 3 and t not in _QUERY_STOPWORDS
    }
    if q_tokens:
        for eid, e in entity_by_id.items():
            short = _normalize((e.name or "").split(".")[-1])
            if short and short in q_tokens:
                rrf_scores[eid] += 0.5
            elif short and any(tok in short for tok in q_tokens):
                rrf_scores[eid] += 0.05

    ranked = sorted(
        entity_by_id.values(),
        key=lambda e: (
            -rrf_scores[e.id],
            _TIER_ORDER.get(getattr(e, "tier", None) or "", 3),
        ),
    )
    return ranked[:limit]


def resolve_entity_id(entity_id: str) -> str:
    """Resolve a short name / partial to a real entity ID (URN).

    The LLM often passes a short table name where a full DataHub URN is expected.
    Returns the exact id if it exists, otherwise the best search_metadata match,
    otherwise the original input unchanged.
    """
    engine = get_engine()
    if engine.get_entity(entity_id):
        return entity_id
    short = entity_id.split(".")[-1] if "." in entity_id else entity_id
    nshort = short.lower().strip()
    fallback = None
    for q in dict.fromkeys((short, entity_id)):  # dedupe when short == entity_id
        hits = search_metadata(q)
        if not hits:
            continue
        # Prefer an EXACT short-name (or full-name) match before any tier-ranked hit
        for h in hits:
            hshort = (h.name or "").split(".")[-1].lower()
            if hshort == nshort or (h.name or "").lower() == entity_id.lower():
                return h.id
        if fallback is None:
            fallback = hits[0].id
    return fallback or entity_id


def get_ownership(entity_id: str):
    """Retrieve the owner and domain of a specific entity."""
    engine = get_engine()
    entity_id = resolve_entity_id(entity_id)
    entity = engine.get_entity(entity_id)
    if entity:
        return {"id": entity.id, "owner": entity.owner, "domain": entity.domain}
    return None


def get_platform_overview(domain: str = None) -> dict:
    """Return a curated, structured overview of the Data Platform in ONE call.

    Used for onboarding / "where do I start" queries — collapses what would
    otherwise be 4+ search_metadata calls into a single grounded response built
    from the seed domains.json + teams.json (Domain/Team entities in the graph).

    Args:
        domain: Optional fuzzy filter (e.g. "lending", "payment"). None = all domains.
    """
    engine = get_engine()

    def _entity_brief(eid: str) -> dict:
        e = engine.get_entity(eid)
        if not e:
            short = eid.split(",")[1].split(".")[-1] if "," in eid else eid
            return {"id": eid, "name": short, "tier": None}
        return {"id": e.id, "name": e.name, "tier": getattr(e, "tier", None),
                "description": (e.description or "")[:140]}

    needle = (domain or "").strip().lower()
    domains_out = []
    for dom in engine.search_by_type("domain"):
        if needle and needle not in (dom.name or "").lower() \
                and needle not in (dom.id or "").lower() \
                and not any(needle in t for t in (dom.tags or [])):
            continue
        meta = dom.metadata or {}
        domains_out.append({
            "id": dom.id,
            "name": dom.name,
            "tier": dom.tier,
            "description": dom.description,
            "tags": dom.tags,
            "key_datasets": [_entity_brief(x) for x in meta.get("key_datasets", [])],
            "key_pipelines": [_entity_brief(x) for x in meta.get("key_pipelines", [])],
            "key_docs": meta.get("key_docs", []),
        })

    # Sort: Tier1 domains first
    domains_out.sort(key=lambda d: _TIER_ORDER.get(d.get("tier") or "", 3))

    teams = engine.search_by_type("team")
    teams_out = [{
        "id": t.id,
        "name": t.name,
        "description": t.description,
        "owner": t.owner,
        "domains": getattr(t, "domains", []),
        "projects": getattr(t, "projects", []),
        "onboarding_docs": (t.metadata or {}).get("onboarding_docs", []),
    } for t in teams]

    return {
        "domains": domains_out,
        "domain_count": len(domains_out),
        "teams": teams_out,
        "tier_system": {
            "Tier1": "Business-critical. Incidents = P0 escalation. Handle with extreme care.",
            "Tier2": "Important analytics. Incidents = P1.",
            "Tier3": "Experimental / dev-only. Lower urgency.",
        },
        "stack": "Hive/HDFS, Spark, Airflow, GitLab CI, Confluence, DataHub, Jira",
    }


# Curated fields are the source of truth — live DataHub/GitLab data must NEVER
# override them (a live "tier" heuristic was demoting seeded Tier1 tables).
_CURATED_FIELDS = ("tier", "owner", "domain", "description")


def _merge_fresh_into_existing(existing, fresh_data: dict):
    """Update freshness-sensitive fields (schema/columns, lineage) on the existing
    entity IN MEMORY, while PRESERVING curated tier/owner/domain/description.
    No write-back to JSON files at request time (blocking I/O + corrupts seed)."""
    fresh = dict(fresh_data)
    # Refresh schema/columns into metadata
    schema_data = fresh.get("schema") or (fresh.get("metadata") or {}).get("columns")
    if schema_data:
        existing.metadata = existing.metadata or {}
        existing.metadata["schema"] = schema_data
    # Lineage is ALSO curated source-of-truth: only FILL when the existing entity
    # has none (enriches the 800+ bare tables) — never overwrite a curated chain
    # (keeps the clean lending lineage graph intact for impact analysis).
    lineage = fresh.get("lineage", {})
    up, down = lineage.get("upstream"), lineage.get("downstream")
    if hasattr(existing, "upstream") and up and not existing.upstream:
        existing.upstream = up
    if hasattr(existing, "downstream") and down and not existing.downstream:
        existing.downstream = down
    # Fill curated fields ONLY if currently empty (never override a seeded value)
    for f in _CURATED_FIELDS:
        if not getattr(existing, f, None) and fresh.get(f):
            setattr(existing, f, fresh.get(f))


def _verify_and_update_entity(entity_id: str, engine: KnowledgeEngine):
    """JIT freshness verification. Preserves curated metadata; in-memory only."""
    existing = engine.get_entity(entity_id)
    if entity_id.startswith("urn:li:dataset:"):
        try:
            from src.ingestion.datahub_client import DataHubClient
            fresh_data = DataHubClient().fetch_dataset_by_urn(entity_id)
            if fresh_data:
                if existing is not None:
                    _merge_fresh_into_existing(existing, fresh_data)
                else:
                    engine.add_entity(Dataset(**_normalize_dataset(fresh_data)))
            return None
        except Exception as e:
            return f"DataHub API Connection Error: {e}"

    elif entity_id.startswith("urn:li:dataFlow:"):
        try:
            from src.ingestion.gitlab_client import GitLabClient
            fresh_data = GitLabClient().fetch_pipeline_by_id(entity_id)
            if fresh_data:
                if existing is not None:
                    _merge_fresh_into_existing(existing, fresh_data)
                else:
                    engine.add_entity(Pipeline(**_normalize_pipeline(fresh_data)))
            return None
        except Exception as e:
            return f"GitLab API Connection Error: {e}"

    return None


def get_entity_details(entity_id: str):
    """Get full details of a specific entity, with JIT freshness verification."""
    engine = get_engine()
    warning_msg = _verify_and_update_entity(entity_id, engine)
    entity = engine.get_entity(entity_id)
    if entity:
        data = {
            "id": entity.id,
            "name": entity.name,
            "description": entity.description,
            "owner": entity.owner,
            "tier": entity.tier,
            "tags": entity.tags,
            "metadata": entity.metadata,
        }
        if warning_msg:
            data["_warning"] = f"Failed to verify real-time freshness. Returning cached data. Error: {warning_msg}"
        return data
    return {"error": f"Entity '{entity_id}' not found locally or remotely."}


def get_related_context(entity_id: str) -> dict:
    """
    Return all cross-source context for an entity:
    - Jira tickets that requested or tracked it
    - Confluence pages that document it
    - GitLab pipelines linked via Jira tickets

    Use this when user asks:
    - "Has there been a Jira ticket for this table?"
    - "Which team/project is working on this?"
    - "Is there any documentation for this dataset?"
    - "If I modify this, is there a project currently building it?"
    """
    engine = get_engine()
    return get_entity_context(entity_id, engine)


def read_gitlab_file(project_name: str, file_path: str) -> dict:
    """
    Read the content of a specific file from a GitLab project.
    JIT fetch with local cache fallback.
    """
    local_path = Path(f"src/data_platform/cache/gitlab/{project_name}/{file_path}")
    cached_content = None

    if local_path.exists():
        with open(local_path, "r", encoding="utf-8") as f:
            cached_content = f.read()

    try:
        import requests
        from src.ingestion.gitlab_client import GitLabClient
        import urllib.parse

        client = GitLabClient()
        if not client.authenticate():
            raise Exception("GitLab Authentication Failed")

        p_id, _, _ = client.get_project_id(project_name)
        if not p_id:
            raise Exception(f"Project '{project_name}' not found on GitLab.")

        branch = "main"
        with open("src/data_platform/pipelines.json", "r") as f:
            for p in json.load(f):
                if p["name"] == project_name:
                    branch = p.get("metadata", {}).get("branch_tracked", "main")
                    break

        encoded_file = urllib.parse.quote(file_path, safe="")
        encoded_branch = urllib.parse.quote(branch, safe="")
        raw_url = f"{client.base_url}/api/v4/projects/{p_id}/repository/files/{encoded_file}/raw?ref={encoded_branch}"
        res = requests.get(raw_url, headers=client.headers, timeout=10)

        if res.status_code == 200:
            live_content = res.text
            if cached_content != live_content:
                local_path.parent.mkdir(parents=True, exist_ok=True)
                with open(local_path, "w", encoding="utf-8") as f:
                    f.write(live_content)
                return {"content": live_content, "status": "Fetched live and updated cache."}
            return {"content": live_content, "status": "Fetched live (no changes from cache)."}
        else:
            raise Exception(f"HTTP {res.status_code}: {res.text}")

    except Exception as e:
        if cached_content is not None:
            return {
                "content": cached_content,
                "status": "Loaded from local cache.",
                "_warning": f"Failed to fetch live file from GitLab. Using local cache. Error: {e}",
            }
        return {"error": f"Failed to read file both remotely and locally. Error: {e}"}


async def read_confluence_page(page_id: str) -> dict:
    """
    Read the content of a specific Confluence page. (BUG-02: now async)
    JIT fetch with local cache fallback.
    """
    import glob

    cache_dir = Path("src/data_platform/cache/confluence")
    cached_content = None
    local_path = None

    existing_files = glob.glob(f"src/data_platform/cache/confluence/{page_id}_*.md")
    if existing_files:
        local_path = Path(existing_files[0])
        with open(local_path, "r", encoding="utf-8") as f:
            cached_content = f.read()

    try:
        from src.ingestion.confluence_client import ConfluenceClient

        client = ConfluenceClient()
        client.headers = client.get_headers()

        page_data = client.fetch_page(page_id)
        if not page_data:
            raise Exception(f"Page {page_id} not found on Confluence.")

        title = page_data["title"]
        version = page_data.get("version", {}).get("number", 1)
        space_key = page_data.get("space", {}).get("key", "UNKNOWN")
        html_content = page_data.get("body", {}).get("storage", {}).get("value", "")

        # BUG-02 FIX: await the coroutine directly (was asyncio.run() which crashes)
        live_markdown = await client.convert_html_to_markdown(html_content, page_id)

        full_live_content = f"# {title}\n**Space:** {space_key} | **Page ID:** {page_id} | **Version:** {version}\n\n{live_markdown}"

        if cached_content != full_live_content:
            safe_title = "".join(c if c.isalnum() else "_" for c in title)
            new_file_name = f"{page_id}_{safe_title}.md"
            new_local_path = cache_dir / new_file_name

            if local_path and local_path != new_local_path and local_path.exists():
                local_path.unlink()

            cache_dir.mkdir(parents=True, exist_ok=True)
            with open(new_local_path, "w", encoding="utf-8") as f:
                f.write(full_live_content)

            try:
                index_path = "src/data_platform/confluence_index.json"
                import os
                if os.path.exists(index_path):
                    with open(index_path, "r") as f:
                        index = json.load(f)
                    updated = False
                    for entry in index:
                        if entry["page_id"] == page_id:
                            entry.update({"title": title, "version": version, "file_name": new_file_name})
                            updated = True
                            break
                    if not updated:
                        index.append({
                            "id": f"urn:li:dataset:(urn:li:dataPlatform:confluence,{page_id},PROD)",
                            "page_id": page_id,
                            "title": title,
                            "space": space_key,
                            "file_name": new_file_name,
                            "version": version,
                        })
                    with open(index_path, "w", encoding="utf-8") as f:
                        json.dump(index, f, indent=2, ensure_ascii=False)
            except Exception as ex:
                print(f"Warning: Failed to update confluence_index.json: {ex}")

            return {"content": full_live_content, "status": "Fetched live and updated cache."}
        return {"content": full_live_content, "status": "Fetched live (no changes from cache)."}

    except Exception as e:
        if cached_content is not None:
            return {
                "content": cached_content,
                "status": "Loaded from local cache.",
                "_warning": f"Failed to fetch live page from Confluence. Using local cache. Error: {e}",
            }
        return {"error": f"Failed to read Confluence page both remotely and locally. Error: {e}"}


async def get_schema(entity_id: str) -> dict:
    """Return column-level schema for a dataset.
    Checks in-memory cache first, then fetches live from DataHub."""
    engine = get_engine()
    entity = engine.get_entity(entity_id)

    # Resolve by short name if full URN not given
    if not entity:
        short_name = entity_id.split(".")[-1]
        results = search_metadata(short_name)
        if results:
            entity = results[0]
            entity_id = entity.id

    # Check in-memory metadata cache
    cached_schema = (getattr(entity, "metadata", None) or {}).get("schema") if entity else None
    if cached_schema:
        return {
            "entity_id": entity_id,
            "columns": cached_schema,
            "count": len(cached_schema),
            "source": "cache",
        }

    # Live fetch from DataHub
    loop = asyncio.get_event_loop()
    try:
        from src.ingestion.datahub_client import DataHubClient
        client = DataHubClient()
        await loop.run_in_executor(None, client.authenticate)
        dataset = await loop.run_in_executor(None, lambda: client.fetch_dataset_by_urn(entity_id))
        if dataset:
            columns = dataset.get("schema", [])
            if entity and columns:
                entity.metadata = entity.metadata or {}
                entity.metadata["schema"] = columns
            # Temporal layer: record the live schema so schema-drift can be detected later.
            try:
                from src.tools.temporal import record_observation
                record_observation(entity_id, "schema", columns)
            except Exception:
                pass
            return {
                "entity_id": entity_id,
                "columns": columns,
                "count": len(columns),
                "source": "datahub_live",
            }
    except Exception as e:
        logger.warning("get_schema failed for %s: %s", entity_id, e)

    return {
        "entity_id": entity_id,
        "columns": [],
        "source": "unavailable",
        "note": "Schema not in cache and DataHub did not return schema data",
    }
