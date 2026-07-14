from datetime import datetime
from typing import Literal
import uuid
from pydantic import BaseModel, Field

class EvidenceItem(BaseModel):
    evidence_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: Literal["exchange_flow", "funding_rate", "social", "whale", "github", "tvl"]
    summary: str
    magnitude: float
    raw_numbers: list[float] = Field(default_factory=list)
    timestamp: datetime
    source_url: str | None = None

class EvidenceBundle(BaseModel):
    token_symbol: str
    window_start: datetime
    window_end: datetime
    items: list[EvidenceItem]
    signal_type: str
    def valid_ids(self) -> set[str]:
        return {e.evidence_id for e in self.items}

