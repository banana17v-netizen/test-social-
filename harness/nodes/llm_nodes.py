from harness import LOGGER as log
from harness.contracts import AttributionResult, NarrativeClassification
from harness.llm.harness import HarnessError, MODEL_STRONG, llm_structured
from harness.llm.prompts import build_attribution_prompt, build_narrative_prompt

def narrative_node(state):
    try:
        result = llm_structured(build_narrative_prompt(state["bundle"]), NarrativeClassification, model=MODEL_STRONG)
    except HarnessError as e:
        log.error(f"narrative_node harness fail: {e}")
        return {"narrative": None, "errors": [str(e)]}
    return {"narrative": result}

def attribution_node(state):
    try:
        result = llm_structured(build_attribution_prompt(state["bundle"], state.get("price_event", {})),
                                AttributionResult, model=MODEL_STRONG)
    except HarnessError as e:
        log.error(f"attribution_node harness fail: {e}")
        return {"attribution": None, "errors": [str(e)]}
    return {"attribution": result}

