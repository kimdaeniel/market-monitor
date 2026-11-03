import unittest

import pandas as pd

import analyze as a

U, F, D = a.UP, a.FLAT, a.DOWN


class PhaseTest(unittest.TestCase):
    def test_table_from_videos(self):
        self.assertEqual(a.classify_phase(U, U, U), "expansion")
        self.assertEqual(a.classify_phase(U, D, D), "recovery")
        self.assertEqual(a.classify_phase(D, U, U), "slowdown")
        self.assertEqual(a.classify_phase(D, D, D), "recession")
        self.assertEqual(a.classify_phase(D, D, U), "deep_slowdown")
        self.assertEqual(a.classify_phase(U, U, D), "late_recovery")

    def test_missing_data_is_not_guessed(self):
        self.assertEqual(a.classify_phase(None, U, U), "mixed")


class WeeklyTest(unittest.TestCase):
    def frame(self, close):
        index = pd.date_range("2022-01-03", periods=len(close), freq="B")
        series = pd.Series(close, index=index, dtype=float)
        return pd.DataFrame({"High": series + 1, "Low": series - 1, "Close": series})

    def test_falling_market_is_oversold(self):
        result = a.analyze_weekly("t", self.frame([1000 - i for i in range(700)]))
        self.assertEqual(result["signal"], "oversold")

    def test_rising_market_is_overbought(self):
        result = a.analyze_weekly("t", self.frame([100 + i for i in range(700)]))
        self.assertEqual(result["signal"], "overbought")


class FredTest(unittest.TestCase):
    def test_unemployment_rise_is_negative(self):
        spec = {"name": "x", "group": "lagging", "core": True, "transform": "inverse"}
        result = a.analyze_fred("x", spec, a.as_series([4.0] * 12 + [4.5] * 3))
        self.assertEqual(result["trend"], D)

    def test_cpi_warning(self):
        spec = {"name": "x", "group": "inflation", "core": True, "transform": "yoy"}
        result = a.analyze_fred("x", spec, a.as_series([100] * 12 + [104] * 12))
        self.assertEqual(result["status"], "warn")
        self.assertEqual(result["value"], 4.0)


class ChangeTest(unittest.TestCase):
    def snapshot(self, status="ok", phase="expansion"):
        return {
            "daily": [{"id": "wti", "name": "WTI", "kind": "oil", "status": status, "value": 101, "unit": "달러"}],
            "weekly": [], "monthly": [], "phase": {"key": phase, "name": phase},
        }

    def test_first_run_has_no_changes(self):
        self.assertEqual(a.detect_changes(self.snapshot(), None), [])

    def test_status_and_phase_changes_are_reported(self):
        changes = a.detect_changes(self.snapshot("warn", "slowdown"), self.snapshot())
        self.assertIn("경기 국면 변경", changes[0])
        self.assertIn("정상 → 경고", changes[1])


if __name__ == "__main__":
    unittest.main()
