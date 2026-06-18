from rank_bm25 import BM25Okapi
import unicodedata, re, logging
from typing import List

logger = logging.getLogger(__name__)

_SYNONYMS = {
    "bảng": ["table", "dataset"], "table": ["bảng", "dataset"],
    "vay": ["lending", "credit", "loan"], "lending": ["vay", "credit"],
    "thanh toán": ["payment"], "payment": ["thanh toán"],
    "giao dịch": ["transaction"], "transaction": ["giao dịch"],
    "người dùng": ["user"], "user": ["người dùng"],
    "chủ sở hữu": ["owner"], "owner": ["chủ sở hữu"],
    "ảnh hưởng": ["impact", "downstream"], "sửa": ["modify", "change", "update"],
    "pipeline": ["dag", "etl", "airflow"], "dag": ["pipeline", "etl"],
    "identity": ["xác minh", "identity"], "merchant": ["đối tác", "partner"],
    "payment": ["qrpay", "acme", "thanh toán"],
    "data": ["dữ liệu", "bảng", "table"],
}

def _normalize(text: str) -> str:
    text = unicodedata.normalize('NFD', text.lower())
    text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^\w\s]', ' ', text)

def _tokenize(text: str) -> List[str]:
    return [t for t in _normalize(text).split() if len(t) >= 2]

def _expand(tokens: List[str]) -> List[str]:
    expanded = list(tokens)
    for t in tokens:
        for syn in _SYNONYMS.get(t, []):
            expanded.extend(_tokenize(syn))
    return list(dict.fromkeys(expanded))


class BM25Index:
    def __init__(self):
        self._entities = []
        self._bm25 = None

    def build(self, entities: dict) -> None:
        self._entities = []
        corpus = []
        for entity in entities.values():
            parts = [entity.name or "", entity.description or ""]
            parts += list(entity.tags or [])
            if getattr(entity, "domain", None):
                parts.append(entity.domain)
            tokens = _tokenize(" ".join(parts))
            if tokens:
                corpus.append(tokens)
                self._entities.append(entity)
        self._bm25 = BM25Okapi(corpus) if corpus else None
        logger.info("BM25 index built: %d entities", len(self._entities))

    def search(self, query: str, top_k: int = 30) -> list:
        if not self._bm25:
            return []
        tokens = _expand(_tokenize(query))
        if not tokens:
            return []
        scores = self._bm25.get_scores(tokens)
        ranked = sorted(zip(scores, self._entities), key=lambda x: -x[0])
        return [e for s, e in ranked if s > 0][:top_k]


_index: BM25Index = None


def get_bm25_index(engine=None) -> BM25Index:
    global _index
    if _index is None:
        if engine is None:
            from src.tools.discovery import get_engine
            engine = get_engine()
        _index = BM25Index()
        _index.build(engine.entities)
    return _index


def invalidate_index() -> None:
    global _index
    _index = None
