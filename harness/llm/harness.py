import json, os, re
from pydantic import BaseModel, ValidationError
from harness.contracts.evidence import EvidenceBundle, EvidenceItem
from harness.obs.tracing import COST_METER, check_pipeline_budget, current_trace_id, trace_span

MODEL_STRONG = "gemini-3.1-flash-lite"
MODEL_CHEAP = "gemini-flash-lite-latest"

class HarnessError(Exception): pass

def count_tokens(text: str) -> int:
    return max(1, len(text) // 4)

def _strip_fences(txt: str) -> str:
    return re.sub(r"^```(json)?|```$", "", txt.strip(), flags=re.MULTILINE).strip()

def compact_context(value, k: int = 12):
    if isinstance(value, str):
        return value[: k * 4]
    bundle: EvidenceBundle = value
    ranked = sorted(bundle.items, key=lambda e: e.magnitude, reverse=True)
    kept, dropped = ranked[:k], ranked[k:]
    if dropped:
        threshold = kept[-1].magnitude if kept else 0
        kept.append(EvidenceItem(type="social", magnitude=0.1,
            summary=f"(+{len(dropped)} tín hiệu nhỏ khác, magnitude < {threshold:.2f})",
            timestamp=bundle.window_end))
    return bundle.model_copy(update={"items": kept})

def call_provider(model, prompt, temperature, json_mode):
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise HarnessError("GEMINI_API_KEY is unset; supply it to call Gemini")
    from google import genai
    from google.genai import types
    client = genai.Client(api_key=key)
    config = types.GenerateContentConfig(temperature=temperature, max_output_tokens=2048)
    if json_mode:
        config.response_mime_type = "application/json"
    response = client.models.generate_content(model=model, contents=prompt, config=config)
    text = response.text or ""
    usage = response.usage_metadata
    COST_METER.add(model, usage.prompt_token_count or 0, usage.candidates_token_count or 0)
    return text

def llm_structured(prompt: str, schema: type[BaseModel], model: str, max_retries: int = 2,
                   max_input_tokens: int = 8000) -> BaseModel:
    if count_tokens(prompt) > max_input_tokens:
        prompt = compact_context(prompt, max_input_tokens)
    temps = [0.0, 0.0, 0.2]
    last_err = None
    for attempt in range(max_retries + 1):
        spent_before = COST_METER.total_for_trace(current_trace_id())
        try:
            with trace_span("llm_call", model=model, attempt=attempt) as span:
                raw = call_provider(model, prompt, temperature=temps[attempt], json_mode=True)
                span["meta"].update(token_in=count_tokens(prompt), token_out=count_tokens(raw),
                                    cost_usd=COST_METER.total_for_trace(current_trace_id()) - spent_before)
        except HarnessError:
            raise  # not retryable (e.g. missing API key) -- don't waste attempts
        except Exception as e:
            # provider-level failure (rate limit, 5xx, timeout) -- retry like a schema miss
            # instead of crashing the node; caller only ever sees HarnessError once retries exhaust.
            last_err = e
            continue
        try:
            result = schema.model_validate_json(_strip_fences(raw))
            check_pipeline_budget(current_trace_id())
            return result
        except ValidationError as e:
            last_err = e
            prompt += (f"\n\n[HARNESS] Output lần trước KHÔNG khớp schema. Lỗi: {e}. "
                       "Trả về DUY NHẤT JSON đúng schema, không thêm bất kỳ text nào.")
    raise HarnessError(f"{schema.__name__} fail sau {max_retries} retry: {last_err}")
