from harness.graph import app

def test_end_to_end_one_token_with_mocks(mocked_pipeline, profile):
    out = app.invoke({"token_symbol":"BTC", "user_profile":profile})
    assert out["verification"].passed
    assert len(out["feed_items"]) == 1

