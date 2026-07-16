import contextvars, time, uuid
from contextlib import contextmanager
from harness import LOGGER as log

_TRACE_ID = contextvars.ContextVar("harness_trace_id", default=None)

class SpanLogger:
    def __init__(self): self.spans: list[dict] = []
    def emit(self, span):
        self.spans.append(span)
        log.info("span", extra={"span": span})
    def clear(self): self.spans.clear()

LOGGER = SpanLogger()

class CostMeter:
    # Free-tier Gemini models are $0/token; update these if the project moves to a paid billing tier.
    RATES = {
        "gemini-3.1-flash-lite": (0.0, 0.0),
        "gemini-flash-lite-latest": (0.0, 0.0),
    }
    def __init__(self): self.entries: list[dict] = []
    def add(self, model, input_tokens, output_tokens, trace_id=None):
        rin, rout = self.RATES.get(model, (0.0, 0.0))
        cost = input_tokens * rin / 1_000_000 + output_tokens * rout / 1_000_000
        self.entries.append({"trace_id": trace_id or current_trace_id(), "model": model, "cost": cost})
    def total_for_trace(self, trace_id): return sum(e["cost"] for e in self.entries if e["trace_id"] == trace_id)

COST_METER = CostMeter()
PIPELINE_COST_BUDGET_USD = 0.50

def current_trace_id():
    trace_id = _TRACE_ID.get()
    if trace_id is None:
        trace_id = str(uuid.uuid4())
        _TRACE_ID.set(trace_id)
    return trace_id

@contextmanager
def use_trace_id(trace_id=None):
    token = _TRACE_ID.set(trace_id or str(uuid.uuid4()))
    try: yield current_trace_id()
    finally: _TRACE_ID.reset(token)

@contextmanager
def trace_span(name: str, **meta):
    t0 = time.time()
    span = {"name": name, "meta": meta, "trace_id": current_trace_id()}
    try:
        yield span
        span["passed"] = True
    except Exception:
        span["passed"] = False
        raise
    finally:
        span["latency_ms"] = (time.time() - t0) * 1000
        LOGGER.emit(span)

def check_pipeline_budget(trace_id: str):
    from harness.llm.harness import HarnessError
    spent = COST_METER.total_for_trace(trace_id)
    if spent > PIPELINE_COST_BUDGET_USD:
        log.error(f"Trace {trace_id} vượt budget: ${spent:.2f}")
        raise HarnessError(f"pipeline cost budget exceeded: ${spent:.2f}")

