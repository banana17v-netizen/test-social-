import json
from collections import defaultdict
from pathlib import Path
from statistics import mean
from harness.contracts import EvalReport, JudgeVerdict, UserProfile
from harness.graph import app
from harness.llm.harness import MODEL_CHEAP, llm_structured

ROOT = Path(__file__).parent

def load_cases(path=ROOT / "golden"):
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(Path(path).glob("*.json"))]

def build_state_from_snapshot(case):
    path = Path(case["raw_data_snapshot"])
    if not path.is_absolute(): path = ROOT.parent.parent / path
    snapshot = json.loads(path.read_text(encoding="utf-8"))
    return {"token_symbol": case["input"]["token_symbol"], "raw_data": snapshot["raw_data"],
        "evidence": [], "errors": [], "feed_items": [], "realized_direction": snapshot.get("realized_direction"),
        "user_profile": UserProfile.model_validate(snapshot["user_profile"])}

def _type_recall(out, expected):
    actual = {e.type for e in out["bundle"].items}
    return len(actual.intersection(expected)) / max(1, len(expected))

def run_eval(cases):
    rows = []
    for c in cases:
        out = app.invoke(build_state_from_snapshot(c))
        rows.append({"case_id": c["case_id"],
            "stage_correct": out["narrative"].lifecycle_stage == c["expected"]["narrative_stage"],
            "groundedness": out["verification"].passed,
            "evidence_recall": _type_recall(out, c["expected"]["must_include_evidence_types"]),
            "confidence": out["confidence"],
            "actual_correct": c["expected"]["direction"] == out.get("realized_direction"),
            "signal_type": out["bundle"].signal_type})
    return EvalReport(rows=rows)

def judge_explanation(attr, bundle):
    prompt = f"Evidence: {[e.summary for e in bundle.items]}\nExplanation: {attr.explanation_text}\nReturn JSON JudgeVerdict."
    return llm_structured(prompt, JudgeVerdict, model=MODEL_CHEAP)

def build_calibration(reports):
    buckets = defaultdict(list)
    for report in reports:
        for row in report.rows: buckets[row["signal_type"]].append(row["actual_correct"])
    return {signal: mean(hits) for signal, hits in buckets.items()}

