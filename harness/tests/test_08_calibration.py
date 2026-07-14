from harness.contracts import EvalReport
from harness.eval.run import build_calibration

def test_build_calibration_from_reports():
    report = EvalReport(rows=[{"signal_type":"price_move", "actual_correct":True},
                              {"signal_type":"price_move", "actual_correct":False}])
    assert build_calibration([report]) == {"price_move": .5}
