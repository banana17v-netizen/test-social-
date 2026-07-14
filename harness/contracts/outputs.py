from typing import Literal
from pydantic import BaseModel, Field

class NarrativeClassification(BaseModel):
    narrative_name: str
    lifecycle_stage: Literal["emerging", "strengthening", "peaking", "weakening", "dead"]
    supporting_evidence_ids: list[str]
    reasoning: str

class Factor(BaseModel):
    evidence_id: str
    attribution_weight: float
    label: str

class AttributionResult(BaseModel):
    price_event_id: str
    contributing_factors: list[Factor]
    explanation_text: str
    caveat: str = "Đây là các yếu tố tương quan, không phải quan hệ nhân quả."

class FeedItem(BaseModel):
    token_symbol: str
    narrative: str
    attribution: AttributionResult
    confidence: float
    personal_relevance: str

class Holding(BaseModel):
    token: str
    size_usd: float

class UserProfile(BaseModel):
    holdings: list[Holding]
    watchlist: list[str]
    risk_appetite: Literal["conservative", "moderate", "aggressive"]
    interested_narratives: list[str] = Field(default_factory=list)
    excluded_narratives: list[str] = Field(default_factory=list)
    time_horizon: Literal["intraday", "swing", "long"]

class VerificationResult(BaseModel):
    passed: bool
    problems: list[str] = Field(default_factory=list)

class JudgeVerdict(BaseModel):
    relevance: int
    hallucinated_claims: list[str]
    verdict: Literal["pass", "fail"]

class EvalReport(BaseModel):
    rows: list[dict]

