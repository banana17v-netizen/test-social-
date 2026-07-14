import uuid
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from harness.contracts import PipelineState
from harness.nodes.deterministic import (confidence_node, format_output_node, ingest_market_node,
    ingest_onchain_node, ingest_social_node, personalize_node, signal_detection_node)
from harness.nodes.llm_nodes import attribution_node, narrative_node
from harness.obs.tracing import trace_span, use_trace_id
from harness.verify.gate import fallback_node, verification_node

def _traced(name, fn):
    def wrapped(state):
        with use_trace_id(state.get("trace_id")):
            with trace_span(name, node=name, token_in=0, token_out=0, cost_usd=0.0):
                return fn(state)
    wrapped.__name__ = name
    return wrapped

g = StateGraph(PipelineState)
nodes = {
    "ingest_social": ingest_social_node, "ingest_onchain": ingest_onchain_node,
    "ingest_market": ingest_market_node, "signal_detection": signal_detection_node,
    "narrative": narrative_node, "attribution": attribution_node, "confidence": confidence_node,
    "verify": verification_node, "fallback": fallback_node, "personalize": personalize_node,
    "format_output": format_output_node,
}
for name, fn in nodes.items(): g.add_node(name, _traced(name, fn))
for name in ["ingest_social", "ingest_onchain", "ingest_market"]:
    g.add_edge(START, name)
    g.add_edge(name, "signal_detection")
g.add_edge("signal_detection", "narrative")
g.add_edge("narrative", "attribution")
g.add_edge("attribution", "confidence")
g.add_edge("confidence", "verify")
def route_after_verify(state): return "personalize" if state["verification"].passed else "fallback"
g.add_conditional_edges("verify", route_after_verify, {"personalize": "personalize", "fallback": "fallback"})
g.add_edge("fallback", "format_output")
g.add_edge("personalize", "format_output")
g.add_edge("format_output", END)
checkpointer = MemorySaver()
_compiled = g.compile(checkpointer=checkpointer)

class HarnessApp:
    def invoke(self, state, config=None, **kwargs):
        state = dict(state)
        state.setdefault("trace_id", str(uuid.uuid4()))
        state.setdefault("raw_data", [])
        state.setdefault("evidence", [])
        state.setdefault("errors", [])
        state.setdefault("feed_items", [])
        config = config or {"configurable": {"thread_id": state["trace_id"]}}
        return _compiled.invoke(state, config=config, **kwargs)

app = HarnessApp()
