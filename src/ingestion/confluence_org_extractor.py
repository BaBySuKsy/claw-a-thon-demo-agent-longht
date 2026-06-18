"""
Confluence ORG / team extractor — grounds the agent's cross-team analysis in REAL
Acme org data instead of seeds.

What it does (read-only Confluence REST, targeted scope):
  1. Fetch the global space catalog → {key: name} (these names ARE the team/department names).
  2. For each data-platform anchor term (credit/lending/qrpay/merchant/identity/...), CQL-search
     Confluence for pages that reference it. Group hits by space, EXCLUDING the data spaces
     themselves and personal spaces (~user). A non-data space that references a data term is
     real evidence that the owning team CONSUMES that data-platform data.
  3. Map each (team-space, term) → a real data-platform dataset anchor (resolved by name from
     datasets.json) → emit a cross-team consumer entity + a lineage edge.

Outputs:
  - RAW evidence  → src/data_platform/cache/confluence_org/evidence.json   (gitignored; may
                    contain page titles/ids — kept out of the public repo)
  - CURATED CLEAN → src/data_platform/cross_team.json   (REAL teams + dataset edges; org-level
                    team names + public dataset URNs only — NO person PII)

Run (needs VPN + Confluence creds in .env):
    PYTHONPATH=. venv/bin/python src/ingestion/confluence_org_extractor.py
"""

import json
import logging
import re
from collections import defaultdict
from pathlib import Path

import requests

from src.ingestion.confluence_client import ConfluenceClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Spaces that ARE the data org → not "cross-team" consumers, exclude from evidence.
_DATA_SPACES = {"DataServices", "DP", "DA", "HAUOB", "DSPC", "DTM", "DataZMC", "BADE", "ZDS"}

# Anchor terms → (search terms, dataset-name substring to resolve a real URN from datasets.json,
# business domain). The dataset anchor must sit on the data-platform side so that changing an
# upstream table surfaces the consuming team in analyze_impact.
_ANCHORS = [
    {"key": "credit",     "terms": ["credit", "lending mart", "installment"],
     "dataset_like": "curated.lending.loan_statement_fact", "domain": "lending"},
    {"key": "qrpay",   "terms": ["qrpay", "mrt_qrpay"],
     "dataset_like": "warehouse.qrpay_user", "domain": "payment"},
    {"key": "merchant", "terms": ["merchant_info", "merchant mart"],
     "dataset_like": "partner.merchant_info", "domain": "merchant"},
    {"key": "identity",      "terms": ["identity_mart", "identity mart"],
     "dataset_like": "warehouse.identity_mart", "domain": "identity"},
]

# Spaces whose names are clearly not a consuming "team" (noise) — skip.
_SKIP_NAMES = {"document", "documents", "backlogs", "demonstration space", "slideshare",
               "confluence to outline"}


def _is_personal(key: str, name: str) -> bool:
    """Filter out personal/individual spaces (not real teams; also avoids person-name PII).

    Catches: ~userid keys; keys like 'Ngan123' (handle+digits); names like 'Acme_Ngan'
    or any single-token underscore name (personal handle, not a multi-word org/team name).
    """
    key = key or ""
    name = (name or "").strip()
    if key.startswith("~"):
        return True
    if re.match(r"^[A-Za-z]+\d+$", key):                 # e.g. Ngan123
        return True
    if re.match(r"(?i)^zalo(pay)?_\w+$", name):           # e.g. Acme_Ngan
        return True
    if "_" in name and " " not in name:                   # single-token handle like Foo_Bar
        return True
    return False

_OUT_CROSS = Path("src/data_platform/cross_team.json")
_RAW_DIR = Path("src/data_platform/cache/confluence_org")
_DATASETS = Path("src/data_platform/datasets.json")


def _all_spaces(client) -> dict:
    """Return {space_key: space_name} for all global spaces (paginated)."""
    out, start = {}, 0
    while True:
        r = requests.get(f"{client.url}/rest/api/space", headers=client.headers,
                         params={"type": "global", "limit": 100, "start": start}, timeout=25)
        if r.status_code != 200:
            break
        results = r.json().get("results", [])
        for s in results:
            out[s.get("key")] = s.get("name", "")
        if len(results) < 100:
            break
        start += 100
    return out


def _search(client, term: str, limit: int = 50) -> list:
    """CQL full-text search → list of {id, title, space_key}."""
    safe = term.replace('"', '')
    r = requests.get(f"{client.url}/rest/api/content/search", headers=client.headers,
                     params={"cql": f'text ~ "{safe}"', "limit": limit, "expand": "space"}, timeout=25)
    if r.status_code != 200:
        return []
    return [{"id": c.get("id"), "title": c.get("title", ""),
             "space_key": c.get("space", {}).get("key", "?")} for c in r.json().get("results", [])]


def _resolve_dataset(datasets: list, name_like: str):
    """Find the exact dataset id/name whose name contains name_like."""
    for d in datasets:
        if name_like in (d.get("name") or ""):
            return d["id"], d["name"]
    return None, None


def main():
    client = ConfluenceClient()
    client.headers = client.get_headers()

    datasets = json.load(open(_DATASETS, encoding="utf-8"))
    spaces = _all_spaces(client)
    logger.info("Fetched %d global spaces", len(spaces))

    # space_key -> {anchor_key -> hit_count}, and evidence examples
    by_space = defaultdict(lambda: defaultdict(int))
    evidence = defaultdict(list)
    for anchor in _ANCHORS:
        for term in anchor["terms"]:
            for hit in _search(client, term):
                sk = hit["space_key"]
                if sk in _DATA_SPACES:
                    continue
                name = spaces.get(sk, "")
                if not name or name.strip().lower() in _SKIP_NAMES or _is_personal(sk, name):
                    continue
                by_space[sk][anchor["key"]] += 1
                if len(evidence[sk]) < 5:
                    evidence[sk].append({"anchor": anchor["key"], "term": term,
                                         "page_id": hit["id"], "title": hit["title"][:80]})

    # Build cross-team consumer entities + edges from the strongest (space, anchor) pairs.
    consumer_datasets, edges, summary = [], [], []
    _MIN_HITS = 3  # require real signal, not a single incidental mention
    for sk, anchors in by_space.items():
        team_name = spaces.get(sk, sk)
        for anchor_key, count in anchors.items():
            if count < _MIN_HITS:
                continue
            anchor = next(a for a in _ANCHORS if a["key"] == anchor_key)
            ds_id, ds_name = _resolve_dataset(datasets, anchor["dataset_like"])
            if not ds_id:
                logger.warning("anchor dataset not found: %s", anchor["dataset_like"])
                continue
            slug = re.sub(r"[^a-z0-9]+", "_", team_name.lower()).strip("_")[:40]
            cons_id = (f"urn:li:dataset:(urn:li:dataPlatform:confluence_ref,"
                       f"acme.cross_team.{slug}.{anchor['domain']}_consumer,PROD)")
            consumer_datasets.append({
                "id": cons_id,
                "name": f"{team_name} · {anchor['domain']} consumer",
                "entityType": "dataset",
                "description": (f"Team '{team_name}' (Confluence space {sk}) tham chiếu dữ liệu "
                                f"{anchor['domain']} của Data Platform ({count} trang nhắc tới "
                                f"'{anchor_key}') → phụ thuộc downstream."),
                "tier": "Tier2",
                "owner": {"type": "team", "name": team_name, "space": sk},
                "domain": f"domain:{anchor['domain']}",
                "tags": ["cross-team", "confluence-evidence", anchor["domain"]],
                "lineage": {"upstream": [ds_id], "downstream": []},
            })
            edges.append({"from": ds_id, "to": cons_id})
            summary.append((team_name, sk, anchor_key, count, ds_name))

    # Write RAW evidence (gitignored)
    _RAW_DIR.mkdir(parents=True, exist_ok=True)
    json.dump({"by_space": {k: dict(v) for k, v in by_space.items()}, "evidence": dict(evidence)},
              open(_RAW_DIR / "evidence.json", "w", encoding="utf-8"), indent=2, ensure_ascii=False)

    # Write CURATED clean cross_team.json (REAL, replaces seeds)
    out = {
        "_comment": ("REAL cross-team consumers derived from Confluence evidence by "
                     "src/ingestion/confluence_org_extractor.py — teams (non-data Confluence "
                     "spaces) that reference Data-Platform data, mapped to the dataset they "
                     "depend on. Org-level team names + public dataset URNs only (no PII). "
                     "Loaded by discovery.load_data_platform_engine(); analyze_impact aggregates "
                     "affected_teams from these."),
        "consumer_datasets": consumer_datasets,
        "edges": edges,
    }
    json.dump(out, open(_OUT_CROSS, "w", encoding="utf-8"), indent=2, ensure_ascii=False)

    print(f"\n=== EXTRACTION SUMMARY ===")
    print(f"global spaces: {len(spaces)} | non-data spaces referencing data: {len(by_space)}")
    print(f"REAL cross-team consumer edges (>= {_MIN_HITS} hits): {len(edges)}")
    for team, sk, ak, n, ds in sorted(summary, key=lambda x: -x[3]):
        print(f"  • {team} [{sk}] —{n}× '{ak}'→ {ds}")
    print(f"\nwrote {_OUT_CROSS} ({len(consumer_datasets)} consumers) + raw evidence (gitignored)")


if __name__ == "__main__":
    main()
