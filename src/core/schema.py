from typing import List, Optional, Dict
from dataclasses import dataclass, field

@dataclass
class Entity:
    id: str
    name: str
    type: str
    description: Optional[str] = None
    owner: Optional[Dict] = None
    domain: Optional[str] = None
    tier: Optional[str] = None
    status: str = "active"
    tags: List[str] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)

@dataclass
class Dataset(Entity):
    type: str = "dataset"
    upstream: List[str] = field(default_factory=list)
    downstream: List[str] = field(default_factory=list)

@dataclass
class Pipeline(Entity):
    type: str = "pipeline"
    inputs: List[str] = field(default_factory=list)
    outputs: List[str] = field(default_factory=list)

@dataclass
class Team(Entity):
    type: str = "team"
    members: List[str] = field(default_factory=list)
    projects: List[str] = field(default_factory=list)

@dataclass
class Domain(Entity):
    type: str = "domain"
    teams: List[str] = field(default_factory=list)

@dataclass
class KnowledgeArticle(Entity):
    type: str = "knowledge_article"
    page_id: str = ""
    content_chunks: List[Dict] = field(default_factory=list)
    relations: Dict = field(default_factory=dict)
