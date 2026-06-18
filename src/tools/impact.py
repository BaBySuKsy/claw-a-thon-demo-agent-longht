from src.tools.discovery import get_engine, resolve_entity_id
from src.tools.viz import build_mermaid_lineage


def analyze_impact(entity_id: str) -> dict:
    """Calculate downstream impact of changing a dataset or pipeline."""
    engine = get_engine()
    entity_id = resolve_entity_id(entity_id)
    impacted_nodes = engine.get_lineage(entity_id, direction="downstream")

    results = []
    for node in impacted_nodes:
        entity = engine.get_entity(node["id"])
        if entity:
            results.append({
                "id": entity.id,
                "name": entity.name,
                "type": entity.type,
                "tier": getattr(entity, "tier", None),
                "depth": node["depth"],
            })

    # Sort: Tier1 first, then Tier2, then others; within same tier by depth
    _TIER_ORDER = {"Tier1": 0, "Tier2": 1, "Tier3": 2}
    results.sort(key=lambda r: (_TIER_ORDER.get(r["tier"] or "", 3), r["depth"]))

    critical_tier1_count = sum(1 for r in results if r.get("tier") == "Tier1")

    # ── Cross-team blast radius ────────────────────────────────────────────────
    # Aggregate the owning team of every impacted entity. Teams OTHER than the
    # target's own owner are "cross-team" — changing this table breaks them too.
    def _team_of(entity):
        owner = getattr(entity, "owner", None)
        if isinstance(owner, dict):
            return owner.get("name"), owner.get("slack")
        if isinstance(owner, str):
            return owner, None
        return None, None

    target_entity = engine.get_entity(entity_id)
    target_team, _ = _team_of(target_entity) if target_entity else (None, None)

    teams: dict = {}
    for r in results:
        e = engine.get_entity(r["id"])
        if not e:
            continue
        team, slack = _team_of(e)
        if not team:
            continue
        info = teams.setdefault(team, {"team": team, "slack": slack, "entity_count": 0, "is_cross_team": team != target_team})
        info["entity_count"] += 1

    affected_teams = sorted(teams.values(), key=lambda t: (not t["is_cross_team"], -t["entity_count"]))
    cross_teams = [t for t in affected_teams if t["is_cross_team"]]

    response = {
        "target": entity_id,
        "target_owner_team": target_team,
        "impact_count": len(results),
        "critical_tier1_count": critical_tier1_count,
        "impacted_entities": results,
        "affected_teams": affected_teams,
        "cross_team_count": len(cross_teams),
        # Visual lineage graph (Mermaid) built from real engine edges — the LLM
        # should embed this block verbatim so the blast radius renders as a diagram.
        "mermaid": build_mermaid_lineage(engine, entity_id, direction="downstream"),
    }

    warnings = []
    if critical_tier1_count > 0:
        warnings.append(
            f"⚠️ This change affects {critical_tier1_count} Tier1 table(s). "
            "Follow the P0 change-management process before proceeding."
        )
    if cross_teams:
        team_str = ", ".join(f"{t['team']} ({t['slack']})" if t["slack"] else t["team"] for t in cross_teams)
        warnings.append(
            f"🚨 CROSS-TEAM IMPACT: this change also breaks {len(cross_teams)} OTHER team(s) — "
            f"{team_str}. Coordinate with them BEFORE the change, not after."
        )
    if warnings:
        response["warning"] = " ".join(warnings)

    return response
