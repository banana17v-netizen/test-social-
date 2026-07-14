import re
from harness.contracts import AttributionResult, Factor, NarrativeClassification
from harness.eval.run import load_cases, run_eval

def test_eval_runner_is_100_percent_grounded(monkeypatch):
    import harness.nodes.llm_nodes as llmn
    def fake(prompt, schema, model, **kw):
        ids = re.findall(r"\[([0-9a-f-]{36})\]", prompt)
        if schema is NarrativeClassification:
            stage = "weakening" if "softened" in prompt else "strengthening"
            return schema(narrative_name="market", lifecycle_stage=stage, supporting_evidence_ids=ids, reasoning="evidence")
        return AttributionResult(price_event_id="p", contributing_factors=[Factor(evidence_id=ids[0], attribution_weight=1, label="observed")], explanation_text="Observed evidence")
    monkeypatch.setattr(llmn, "llm_structured", fake)
    report = run_eval(load_cases())
    assert len(report.rows) == 2
    assert all(row["groundedness"] for row in report.rows)

