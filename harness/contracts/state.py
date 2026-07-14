from operator import add
from typing import Annotated
from typing_extensions import TypedDict
from .evidence import EvidenceBundle, EvidenceItem
from .outputs import AttributionResult, FeedItem, NarrativeClassification, UserProfile, VerificationResult

class PipelineState(TypedDict, total=False):
    token_symbol: str
    user_profile: UserProfile
    trace_id: str
    raw_data: Annotated[list[dict], add]
    evidence: Annotated[list[EvidenceItem], add]
    errors: Annotated[list[str], add]
    bundle: EvidenceBundle | None
    narrative: NarrativeClassification | None
    attribution: AttributionResult | None
    confidence: float | None
    verification: VerificationResult | None
    feed_items: list[FeedItem]
    price_event: dict
    personal_relevance: str
    realized_direction: str

