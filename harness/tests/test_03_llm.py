from pydantic import BaseModel
import harness.llm.harness as module

class Strict(BaseModel): value: int

def test_llm_structured_retries_and_self_corrects(monkeypatch):
    prompts = []
    def fake(model, prompt, temperature, json_mode):
        prompts.append(prompt)
        return '{"wrong": true}' if len(prompts) == 1 else '{"value": 7}'
    monkeypatch.setattr(module, "call_provider", fake)
    assert module.llm_structured("return value", Strict, "fake", max_retries=1).value == 7
    assert "KHÔNG khớp schema" in prompts[1]

