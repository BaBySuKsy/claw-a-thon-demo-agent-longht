"""
Cross-source relationship builder for Acme Data Platform Knowledge Graph.

Scans Confluence tree cache + Jira ticket cache at engine load time,
extracts entity mentions, and wires typed relationship edges.

Relationship types wired:
  dataset/pipeline  → DOCUMENTED_BY  → confluence:{page_id}
  dataset/pipeline  → REQUESTED_BY   → jira:{epic_key}
  jira:{epic_key}   → IMPLEMENTED_BY → pipeline entity

Performance contract:
- Runs ONCE at engine load time (singleton via get_engine()).
- Per-query lookups are O(1) via KnowledgeEngine._rel_out / _rel_in dicts.
- Name matching uses a pre-built {short_name → entity_id} dict.
"""

import json
import re
import logging
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from src.core.engine import KnowledgeEngine

logger = logging.getLogger(__name__)

_JIRA_DIR = Path("src/data_platform/cache/jira")
_CONFLUENCE_TREE_DIR = Path("src/data_platform/cache/confluence_tree")

# Edge type constants (use these everywhere to avoid typos)
DOCUMENTED_BY = "DOCUMENTED_BY"
REQUESTED_BY = "REQUESTED_BY"
IMPLEMENTED_BY = "IMPLEMENTED_BY"

# Module-level metadata caches for O(1) display-data lookup in get_entity_context()
_jira_meta: Dict[str, dict] = {}        # epic_key → {epic_key, summary, status, project}
_confluence_meta: Dict[str, dict] = {}  # page_id  → {page_id, title}


# ── Name index ────────────────────────────────────────────────────────────────

def _build_name_index(engine: KnowledgeEngine) -> Dict[str, str]:
    """
    Build {normalized_name → entity_id} lookup for fast text-mention matching.

    Includes three forms per entity:
      - Leaf segment: 'identity_mart'
      - Two-segment:  'warehouse.identity_mart'
      - Full name:    'acme.analytics.warehouse.identity_mart'

    Minimum length 6 to avoid false positives on short words (e.g. 'data', 'log').
    """
    index: Dict[str, str] = {}
    for eid, entity in engine.entities.items():
        name = entity.name.lower()
        parts = name.replace("-", ".").split(".")

        leaf = parts[-1]
        if len(leaf) >= 6:
            index.setdefault(leaf, eid)

        if len(parts) >= 2:
            medium = f"{parts[-2]}.{parts[-1]}"
            if len(medium) >= 8:
                index.setdefault(medium, eid)

        if len(name) >= 6:
            index.setdefault(name, eid)

    return index


# ── Confluence tree text extraction ───────────────────────────────────────────

def _extract_node_texts(node: dict) -> List[str]:
    """Recursively collect section heading + body text from a Confluence tree node."""
    texts = []
    for section in node.get("content_structure", {}).get("sections", []):
        h = section.get("heading", "")
        b = section.get("body", "")
        if h:
            texts.append(h)
        if b:
            texts.append(b)
    for child in node.get("child_pages", []):
        texts.extend(_extract_node_texts(child))
    return texts


# ── Compiled patterns ─────────────────────────────────────────────────────────

# Identifier: starts with lowercase letter, at least 6 chars, underscores/digits ok
_IDENT_RE = re.compile(r'[a-z][a-z0-9_]{5,}')

# GitLab project URL pattern in Jira: extract project name from MR URL
_GITLAB_RE = re.compile(r'dataeng/(?:datainfra|[a-z0-9_-]+)/([a-z][a-z0-9_-]+)/')


# ── Main builder ──────────────────────────────────────────────────────────────

def build_cross_source_index(engine: KnowledgeEngine) -> dict:
    """
    Scan Confluence tree + Jira caches. Extract entity mentions. Wire edges.

    Call this ONCE inside load_data_platform_engine() before returning the engine.
    After this, all lookups go through engine.find_by_relation() — O(1).

    Returns:
        dict with edge counts per source: {confluence_edges, jira_entity_edges, jira_pipeline_edges}
    """
    global _jira_meta, _confluence_meta
    _jira_meta.clear()
    _confluence_meta.clear()

    name_index = _build_name_index(engine)
    if not name_index:
        logger.warning("cross_source: empty name index — no entities loaded yet?")
        return {}

    stats = {
        "confluence_edges": 0,
        "jira_entity_edges": 0,
        "jira_pipeline_edges": 0,
    }

    # Pipeline name → entity_id for IMPLEMENTED_BY lookup
    pipeline_index: Dict[str, str] = {
        entity.name.lower(): eid
        for eid, entity in engine.entities.items()
        if hasattr(entity, "inputs")
    }

    # ── 1. Confluence tree → DOCUMENTED_BY ────────────────────────────────────
    if _CONFLUENCE_TREE_DIR.exists():
        for tree_file in sorted(_CONFLUENCE_TREE_DIR.glob("*.json")):
            try:
                data = json.loads(tree_file.read_bytes())
                page_id = str(data.get("page_id", ""))
                title = data.get("title", tree_file.stem)

                _confluence_meta[page_id] = {"page_id": page_id, "title": title}
                article_target = f"confluence:{page_id}"

                # Only scan body/heading text — not raw JSON keys
                texts = _extract_node_texts(data)
                if not texts:
                    continue
                combined = " ".join(texts).lower()

                seen: Set[Tuple[str, str]] = set()
                for m in _IDENT_RE.finditer(combined):
                    term = m.group()
                    entity_id = name_index.get(term)
                    if entity_id:
                        pair = (entity_id, article_target)
                        if pair not in seen:
                            seen.add(pair)
                            engine.add_relationship(entity_id, article_target, DOCUMENTED_BY)
                            stats["confluence_edges"] += 1

            except Exception as exc:
                logger.warning("cross_source: confluence %s — %s", tree_file.name, exc)

    # ── 2. Jira tickets → REQUESTED_BY + IMPLEMENTED_BY ──────────────────────
    if _JIRA_DIR.exists():
        for jira_file in sorted(_JIRA_DIR.glob("*.json")):
            if jira_file.stem == "other_epic":
                continue
            try:
                data = json.loads(jira_file.read_bytes())
                epic_key = data.get("epic_key", jira_file.stem)
                jira_source = f"jira:{epic_key}"

                _jira_meta[epic_key] = {
                    "epic_key": epic_key,
                    "summary": data.get("summary", ""),
                    "status": data.get("status", ""),
                    "project": data.get("project", ""),
                    "created_at": data.get("created_at", ""),
                }

                # Aggregate all text in this epic
                parts = [
                    data.get("summary", ""),
                    data.get("description") or "",
                ]
                for ticket in data.get("tickets", []):
                    parts.append(ticket.get("summary", ""))
                    parts.append(ticket.get("description") or "")
                combined = " ".join(parts).lower()

                # Entity name mentions → REQUESTED_BY
                seen: Set[Tuple[str, str]] = set()
                for m in _IDENT_RE.finditer(combined):
                    term = m.group()
                    entity_id = name_index.get(term)
                    if entity_id:
                        pair = (entity_id, jira_source)
                        if pair not in seen:
                            seen.add(pair)
                            engine.add_relationship(entity_id, jira_source, REQUESTED_BY)
                            stats["jira_entity_edges"] += 1

                # GitLab project references → IMPLEMENTED_BY
                for gm in _GITLAB_RE.finditer(combined):
                    project_name = gm.group(1).lower()
                    pipeline_eid = pipeline_index.get(project_name)
                    if pipeline_eid:
                        engine.add_relationship(jira_source, pipeline_eid, IMPLEMENTED_BY)
                        stats["jira_pipeline_edges"] += 1

            except Exception as exc:
                logger.warning("cross_source: jira %s — %s", jira_file.name, exc)

    total = sum(stats.values())
    logger.info(
        "Cross-source index built: %d total edges "
        "(%d confluence, %d jira-entity, %d jira-pipeline)",
        total,
        stats["confluence_edges"],
        stats["jira_entity_edges"],
        stats["jira_pipeline_edges"],
    )
    return stats


# ── Query helper ──────────────────────────────────────────────────────────────

def get_entity_context(entity_id: str, engine: KnowledgeEngine) -> dict:
    """
    Return all cross-source context for an entity: Jira tickets + Confluence pages.

    O(1) per source using engine adjacency index.
    Used by discovery.get_related_context() tool.
    """
    # Jira tickets that reference this entity (entity → jira:KEY)
    jira_targets = engine.find_by_relation(entity_id, REQUESTED_BY, "outbound")
    jira_tickets = []
    for jid in jira_targets:
        epic_key = jid.replace("jira:", "")
        meta = _jira_meta.get(epic_key, {})
        if meta:
            jira_tickets.append({
                "key": epic_key,
                "summary": meta.get("summary", ""),
                "status": meta.get("status", ""),
                "project": meta.get("project", ""),
            })

    # Confluence pages that document this entity (entity → confluence:PAGE_ID)
    conf_targets = engine.find_by_relation(entity_id, DOCUMENTED_BY, "outbound")
    confluence_pages = []
    for cid in conf_targets:
        page_id = cid.replace("confluence:", "")
        meta = _confluence_meta.get(page_id, {})
        if meta:
            confluence_pages.append({
                "page_id": page_id,
                "title": meta.get("title", ""),
            })

    # Pipelines implemented by Jira tickets that reference this entity
    related_pipelines = []
    for jid in jira_targets:
        pipeline_eids = engine.find_by_relation(jid, IMPLEMENTED_BY, "outbound")
        for peid in pipeline_eids:
            pipeline = engine.get_entity(peid)
            if pipeline:
                related_pipelines.append({
                    "id": peid,
                    "name": pipeline.name,
                    "via_ticket": jid.replace("jira:", ""),
                })

    return {
        "entity_id": entity_id,
        "jira_ticket_count": len(jira_tickets),
        "jira_tickets": jira_tickets,
        "confluence_page_count": len(confluence_pages),
        "confluence_pages": confluence_pages,
        "related_pipelines": related_pipelines,
    }
