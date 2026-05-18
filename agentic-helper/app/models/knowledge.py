from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class KnowledgeChunk:
    id: str
    source: str
    content: str
    metadata_json: dict[str, Any] = field(default_factory=dict)
    score: float | None = None
