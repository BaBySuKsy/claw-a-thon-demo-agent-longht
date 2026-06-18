from typing import Dict, List, Optional
from src.core.schema import Entity, Dataset, Pipeline, Team, Domain


class KnowledgeEngine:
    def __init__(self):
        self.entities: Dict[str, Entity] = {}
        self.relationships: List[Dict] = []

        # O(1) relationship adjacency indexes (populated by add_relationship)
        self._rel_out: Dict[str, List[Dict]] = {}  # source_id → [{target, type}]
        self._rel_in: Dict[str, List[Dict]] = {}   # target_id → [{source, type}]

        # Lineage reverse-index cache (invalidated on add_entity, rebuilt lazily)
        self._lineage_cache_valid: bool = False
        self._pipeline_consumes: Dict[str, List[str]] = {}  # dataset_id → pipeline_ids
        self._pipeline_produces: Dict[str, List[str]] = {}  # dataset_id → pipeline_ids

    # ── Entity management ─────────────────────────────────────────────────────

    def add_entity(self, entity: Entity):
        self.entities[entity.id] = entity
        self._lineage_cache_valid = False  # Invalidate on any entity addition

    def get_entity(self, entity_id: str) -> Optional[Entity]:
        return self.entities.get(entity_id)

    def search_by_type(self, entity_type: str) -> List[Entity]:
        return [e for e in self.entities.values() if e.type == entity_type]

    # ── Relationship management ───────────────────────────────────────────────

    def add_relationship(self, source_id: str, target_id: str, relation_type: str):
        """Store a typed relationship edge and update adjacency indexes."""
        rel = {"source": source_id, "target": target_id, "type": relation_type}
        self.relationships.append(rel)
        self._rel_out.setdefault(source_id, []).append(rel)
        self._rel_in.setdefault(target_id, []).append(rel)

    def find_by_relation(
        self,
        entity_id: str,
        relation_type: Optional[str] = None,
        direction: str = "outbound",
    ) -> List[str]:
        """O(1) lookup of connected entity IDs by relationship type.

        Args:
            entity_id: Source or target entity ID.
            relation_type: Filter by edge type (None = all types).
            direction: 'outbound' (entity is source) or 'inbound' (entity is target).
        """
        if direction == "outbound":
            rels = self._rel_out.get(entity_id, [])
            if relation_type:
                return [r["target"] for r in rels if r["type"] == relation_type]
            return [r["target"] for r in rels]
        else:
            rels = self._rel_in.get(entity_id, [])
            if relation_type:
                return [r["source"] for r in rels if r["type"] == relation_type]
            return [r["source"] for r in rels]

    # ── Lineage traversal ─────────────────────────────────────────────────────

    def _build_lineage_cache(self):
        """Build pipeline↔dataset reverse index. O(pipelines × avg_io). Called once."""
        self._pipeline_consumes = {}
        self._pipeline_produces = {}
        for eid, entity in self.entities.items():
            if isinstance(entity, Pipeline):
                for inp in entity.inputs:
                    self._pipeline_consumes.setdefault(inp, []).append(eid)
                for out in entity.outputs:
                    self._pipeline_produces.setdefault(out, []).append(eid)
        self._lineage_cache_valid = True

    def get_lineage(self, entity_id: str, direction: str = "downstream") -> List[Dict]:
        """BFS lineage traversal — crosses Dataset ↔ Pipeline boundaries."""
        if not self.get_entity(entity_id):
            return []

        if not self._lineage_cache_valid:
            self._build_lineage_cache()

        queue = [(entity_id, 0)]
        visited = {entity_id}
        results = []

        while queue:
            current_id, depth = queue.pop(0)

            if depth > 0:
                results.append({"id": current_id, "depth": depth})

            entity = self.get_entity(current_id)
            if not entity:
                continue

            neighbors: List[str] = []
            if direction == "downstream":
                if isinstance(entity, Dataset):
                    neighbors = list(entity.downstream)
                    neighbors += self._pipeline_consumes.get(current_id, [])
                elif isinstance(entity, Pipeline):
                    neighbors = list(entity.outputs)
            elif direction == "upstream":
                if isinstance(entity, Dataset):
                    neighbors = list(entity.upstream)
                    neighbors += self._pipeline_produces.get(current_id, [])
                elif isinstance(entity, Pipeline):
                    neighbors = list(entity.inputs)

            for neighbor_id in neighbors:
                if neighbor_id not in visited:
                    visited.add(neighbor_id)
                    queue.append((neighbor_id, depth + 1))

        return results

    def get_lineage_graph(self, entity_id: str, direction: str = "downstream") -> List[Dict]:
        """BFS lineage that records actual parent→child EDGES (for visualization).

        Returns a list of {"source": id, "target": id} edges discovered during the
        same cross-entity traversal used by get_lineage(). Mirrors get_lineage()'s
        neighbor logic so the graph matches impact analysis exactly.
        """
        if not self.get_entity(entity_id):
            return []
        if not self._lineage_cache_valid:
            self._build_lineage_cache()

        queue = [entity_id]
        visited = {entity_id}
        edges = []

        while queue:
            current_id = queue.pop(0)
            entity = self.get_entity(current_id)
            if not entity:
                continue

            neighbors: List[str] = []
            if direction == "downstream":
                if isinstance(entity, Dataset):
                    neighbors = list(entity.downstream) + self._pipeline_consumes.get(current_id, [])
                elif isinstance(entity, Pipeline):
                    neighbors = list(entity.outputs)
            elif direction == "upstream":
                if isinstance(entity, Dataset):
                    neighbors = list(entity.upstream) + self._pipeline_produces.get(current_id, [])
                elif isinstance(entity, Pipeline):
                    neighbors = list(entity.inputs)

            for neighbor_id in neighbors:
                edges.append({"source": current_id, "target": neighbor_id})
                if neighbor_id not in visited:
                    visited.add(neighbor_id)
                    queue.append(neighbor_id)

        return edges

    def find_owner(self, entity_id: str) -> Optional[str]:
        entity = self.get_entity(entity_id)
        return entity.owner if entity else None
