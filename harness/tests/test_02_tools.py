from harness.tools.base import tool_harness

def test_tool_degrades_to_down_without_raising():
    @tool_harness(max_retries=0)
    def unplugged(): raise ConnectionError("offline")
    assert unplugged().source_health == "down"

