"""Test strict 10 fixed + 10 AI + 10 IBKR unique-ticker budget.

Run offline from repository root:
    python -m unittest RudraScanner.tests.test_selection_caps -v
"""

import unittest

from RudraScanner.universe import (
    MAX_STOCK_TICKERS,
    MAX_PER_SOURCE,
    common_tickers,
    merge_shared_universe,
    selection_summary,
)


class SelectionCapTests(unittest.TestCase):
    def test_full_budget_with_cross_source_duplicates(self):
        fixed = [{"ticker": f"F{i:02d}"} for i in range(19)]
        fixed.append({"ticker": "INTC"})
        ai = [
            {"ticker": "INTC", "priority": "1", "freshness": "FRESH"},
            {"ticker": "F00", "priority": "2", "freshness": "FRESH"},
        ]
        ai += [
            {"ticker": f"A{i:02d}", "priority": str(i + 3),
             "freshness": "FRESH"} for i in range(24)
        ]
        ibkr = [
            {"ticker": "INTC", "scan_code": "TOP_PERC_GAIN", "rank": 1},
            {"ticker": "F01", "scan_code": "MOST_ACTIVE", "rank": 1},
            {"ticker": "A01", "scan_code": "HOT_BY_VOLUME", "rank": 1},
        ]
        ibkr += [
            {"ticker": f"I{i:02d}", "scan_code": "MOST_ACTIVE", "rank": i + 2}
            for i in range(32)
        ]
        selected = merge_shared_universe(fixed, ai, ibkr)
        counts = selection_summary(selected)
        self.assertEqual(MAX_PER_SOURCE, 10)
        self.assertEqual(MAX_STOCK_TICKERS, 30)
        self.assertEqual(counts["selected_total"], 30)
        self.assertEqual(counts["selected_by_source"],
                         {"FIXED": 10, "AI": 10, "IBKR": 10})
        self.assertEqual(len(set(common_tickers(selected))), 30)
        self.assertIn("INTC", common_tickers(selected))
        info = {r["ticker"]: r for r in selected}
        self.assertEqual(info["INTC"]["selection_source"], "FIXED")
        self.assertEqual(info["INTC"]["sources"], ["FIXED", "AI", "IBKR"])

    def test_unfilled_source_quota_is_not_lent_to_another_source(self):
        fixed = [{"ticker": "INTC"}]
        ai = [{"ticker": "INTC", "priority": "1"},
              {"ticker": "AMD", "priority": "2"}]
        ibkr = [{"ticker": f"I{i:02d}", "scan_code": "MOST_ACTIVE",
                 "rank": i + 1} for i in range(23)]
        selected = merge_shared_universe(fixed, ai, ibkr)
        self.assertEqual(selection_summary(selected)["selected_by_source"],
                         {"FIXED": 1, "AI": 1, "IBKR": 10})
        self.assertEqual(len(selected), 12)

    def test_priority_is_deterministic_and_protects_mandatory_monitors(self):
        fixed = [{"ticker": f"F{i:02d}", "notes": ""} for i in range(14)]
        fixed += [{"ticker": "AKAM", "notes": "OPEN POSITION - mandatory"},
                  {"ticker": "WTTR", "notes": "OPEN POSITION"},
                  {"ticker": "INTC", "notes": "permanent monitor"}]
        ai = [
            {"ticker": "AAA", "priority": "9", "freshness": "FRESH"},
            {"ticker": "BBB", "priority": "1", "freshness": "FRESH"},
            {"ticker": "CCC", "priority": "2", "freshness": "FRESH"},
        ]
        selected = merge_shared_universe(fixed, ai, [])
        selected_fixed = {r["ticker"] for r in selected
                          if r["selection_source"] == "FIXED"}
        self.assertEqual(len(selected_fixed), 10)
        self.assertTrue({"AKAM", "WTTR", "INTC"}.issubset(selected_fixed))
        ai_rows = [r for r in selected if r["selection_source"] == "AI"]
        self.assertEqual({r["ticker"] for r in ai_rows}, {"AAA", "BBB", "CCC"})

    def test_avoid_excluded_names_and_reject_oversized_configuration(self):
        rows = merge_shared_universe(
            [{"ticker": "INTC"}, {"ticker": "ONDS"}],
            [{"ticker": "BEAT", "priority": 1}], [
                {"ticker": "ONDS", "scan_code": "MOST_ACTIVE"},
                {"ticker": "WDC", "scan_code": "MOST_ACTIVE"}
            ]
        )
        self.assertEqual(common_tickers(rows), ["INTC", "WDC"])
        with self.assertRaisesRegex(ValueError, "confirmed 10"):
            merge_shared_universe([], [], [], max_per_source=11)


if __name__ == "__main__":
    unittest.main()
