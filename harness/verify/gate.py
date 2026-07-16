import math, re
from harness import LOGGER as log
from harness.contracts import AttributionResult, Factor, VerificationResult

NUM_RE = re.compile(r"-?\d+(?:[.,]\d+)?\s*(?:%|k|tr|m|b|triệu|nghìn|ngàn)?", re.IGNORECASE)
_UNIT_MULT = {"triệu": 1e6, "nghìn": 1e3, "ngàn": 1e3, "tr": 1e6, "k": 1e3, "m": 1e6, "b": 1e9}

def _parse_number(raw):
    s = raw.strip().lower()
    mult = 1.0
    for suffix, m in sorted(_UNIT_MULT.items(), key=lambda kv: -len(kv[0])):
        if s.endswith(suffix): mult, s = m, s[:-len(suffix)].strip(); break
    s = s.rstrip("%").strip()
    if "," in s:
        whole, _, frac = s.partition(",")
        # LLM explanations are often in English prose ("41,000 views"), where a comma followed
        # by exactly 3 digits is a thousands separator, not a decimal point -- treating it as
        # decimal (old behavior) turned real, grounded numbers into false "hallucination" flags.
        s = whole + frac if len(frac) == 3 else whole + "." + frac
    try: return float(s) * mult
    except ValueError: return None

def extract_numbers(text):
    return [v for m in NUM_RE.finditer(text) if (v := _parse_number(m.group())) is not None]

def _numbers_match(a, b, rel_tol=0.02, abs_tol=0.01):
    return math.isclose(a, b, rel_tol=rel_tol, abs_tol=abs_tol)

def verify_attribution(attr, bundle):
    problems, valid = [], bundle.valid_ids()
    for f in attr.contributing_factors:
        if f.evidence_id not in valid: problems.append(f"Hallucinated evidence_id: {f.evidence_id}")
    total = sum(f.attribution_weight for f in attr.contributing_factors)
    if not (0.9 <= total <= 1.1): problems.append(f"Tổng weight = {total:.2f}, cần ≈ 1")
    # magnitude is shown to the LLM in the prompt's evidence block (`| magnitude=...`), so it's
    # a legitimate number the model may cite — not including it caused false "hallucination" flags.
    evidence_nums = []
    for e in bundle.items: evidence_nums += extract_numbers(e.summary) + e.raw_numbers + [e.magnitude]
    for n in extract_numbers(attr.explanation_text):
        if not any(_numbers_match(n, ev) for ev in evidence_nums):
            problems.append(f"Số '{n}' trong explanation không khớp (dung sai 2%) với evidence nào")
    return VerificationResult(passed=not problems, problems=problems)

def verification_node(state):
    if state.get("attribution") is None:
        return {"verification": VerificationResult(passed=False, problems=["attribution_node harness fail — xem state.errors"])}
    result = verify_attribution(state["attribution"], state["bundle"])
    if not result.passed: log.warning(f"Verification FAIL: {result.problems}")
    return {"verification": result}

def fallback_node(state):
    bundle = state["bundle"]
    top = sorted(bundle.items, key=lambda e: e.magnitude, reverse=True)[:3]
    safe_text = "Các tín hiệu nổi bật: " + "; ".join(e.summary for e in top)
    factors = [Factor(evidence_id=e.evidence_id, attribution_weight=1 / len(top), label=e.type) for e in top] if top else []
    safe_attr = AttributionResult(price_event_id=state.get("price_event", {}).get("id", "na"),
        contributing_factors=factors, explanation_text=safe_text + " [tự động tổng hợp — độ tin cậy giảm]")
    return {"attribution": safe_attr, "confidence": (state.get("confidence") or 0.5) * 0.6,
            "personal_relevance": "Degraded output"}
