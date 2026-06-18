"""
Mermaid diagram generation for lineage / impact analysis.

Turns the knowledge graph's real edges into a Mermaid `flowchart` that renders
as a visual lineage tree in any Markdown viewer — a high-signal way to show
blast radius in the demo. The graph is built from actual engine edges (not the
LLM), so it is always faithful to the data.
"""

import re

_TIER_STYLE = {
    "Tier1": "fill:#ffcdd2,stroke:#c0392b,stroke-width:2.5px,color:#7a1f16",  # red — critical
    "Tier2": "fill:#ffe7a3,stroke:#c5860b,stroke-width:1.5px,color:#6b4e08",  # amber
    "Tier3": "fill:#cfe0ff,stroke:#0033C9,stroke-width:1.5px,color:#0a2a7a",  # blue — dev
}


def _node_id(idx: int) -> str:
    return f"n{idx}"


def _short(name: str) -> str:
    if not name:
        return "?"
    # Names can be dotted table paths OR malformed URN remnants with commas/PROD.
    # Strip Mermaid-structural chars FIRST, then drop platform/env tokens.
    cleaned = re.sub(r'["\[\]{}|<>()]', "", name)
    tokens = [t for t in re.split(r"[.,]", cleaned) if t and t.upper() not in ("PROD", "DEV", "STAGING")]
    short = tokens[-1] if tokens else cleaned
    return (short[:34] + "…") if len(short) > 35 else (short or "?")


def build_mermaid_lineage(engine, target_id: str, direction: str = "downstream", max_edges: int = 40) -> str:
    """Build a ```mermaid flowchart string for the lineage graph rooted at target_id.

    Nodes are colored by tier (Tier1 red / Tier2 amber / Tier3 blue), shaped by
    type (pipelines as [[...]], datasets as [...]). Returns "" if no edges.
    """
    edges = engine.get_lineage_graph(target_id, direction=direction)
    if not edges:
        return ""
    if len(edges) > max_edges:
        edges = edges[:max_edges]

    # Stable id mapping for every entity referenced
    ids = []
    for e in edges:
        for k in ("source", "target"):
            if e[k] not in ids:
                ids.append(e[k])
    if target_id not in ids:
        ids.insert(0, target_id)
    alias = {eid: _node_id(i) for i, eid in enumerate(ids)}

    lines = ["```mermaid", "flowchart TD"]
    styles = []
    for eid in ids:
        ent = engine.get_entity(eid)
        label = _short(getattr(ent, "name", "") or eid)
        tier = getattr(ent, "tier", None)
        etype = getattr(ent, "type", "dataset")
        if tier:
            label = f"{label}<br/>{tier}"
        node = alias[eid]
        # pipelines: subroutine shape [[..]]; datasets: rounded [..]
        if etype == "pipeline":
            lines.append(f'    {node}[["{label}"]]')
        else:
            lines.append(f'    {node}["{label}"]')
        if tier in _TIER_STYLE:
            styles.append(f"    style {node} {_TIER_STYLE[tier]}")

    for e in edges:
        lines.append(f"    {alias[e['source']]} --> {alias[e['target']]}")

    # Emphasize the root with Acme blue
    if target_id in alias:
        styles.append(f"    style {alias[target_id]} fill:#0033C9,color:#fff,stroke:#00269e,stroke-width:2.5px")

    lines.extend(styles)
    lines.append("```")
    return "\n".join(lines)
