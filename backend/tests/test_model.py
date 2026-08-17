import unittest

from floodsense.model import compare, load_network, simulate


class ModelTests(unittest.TestCase):
    def test_network_ids_are_unique_and_links_resolve(self):
        drains = load_network()["drains"]
        ids = {d["id"] for d in drains}
        self.assertEqual(len(ids), len(drains))
        self.assertTrue(all(d["downstream"] is None or d["downstream"] in ids for d in drains))

    def test_no_rain_does_not_overflow(self):
        result = simulate(0, 60)
        self.assertEqual(result["summary"]["total_overflow_m3"], 0)

    def test_heavy_rain_produces_a_failure_prediction(self):
        result = simulate(48, 90)
        self.assertIsNotNone(result["summary"]["first_overflow"])

    def test_crew_recommendation_appears_before_overflow(self):
        result = simulate(48, 90)
        actionable = next(frame for frame in result["timeline"] if frame["recommendation"]["requires_action"])
        first_overflow = min(
            drain["overflow_at_minute"]
            for frame in result["timeline"]
            for drain in frame["drains"]
            if drain["overflow_at_minute"] is not None
        )
        self.assertLess(actionable["minute"], first_overflow)

    def test_cleaning_reduces_overflow(self):
        result = compare(48, "OX-103", 12, 90)
        self.assertGreater(result["impact"]["prevented_overflow_m3"], 0)

    def test_outputs_remain_bounded(self):
        result = simulate(60, 120)
        for frame in result["timeline"]:
            for drain in frame["drains"]:
                self.assertGreaterEqual(drain["fill_pct"], 0)
                self.assertLessEqual(drain["fill_pct"], 100)

    def test_rainfall_schedule_changes_only_future_conditions(self):
        result = simulate(20, 220, rainfall_schedule=[{"minute": 0, "rainfall_mmh": 20}, {"minute": 100, "rainfall_mmh": 60}])
        self.assertEqual(result["timeline"][99]["rainfall_mmh"], 20)
        self.assertEqual(result["timeline"][100]["rainfall_mmh"], 60)
        self.assertIsNotNone(result["summary"]["first_overflow"])

    def test_multiple_cleanings_are_preserved(self):
        first = compare(38, "OX-103", 15, 120)
        previous = first["intervention"]["scenario"]["interventions"]
        second = compare(38, "OX-108", 39, 120, interventions=previous)
        frame = {item["id"]: item for item in second["intervention"]["timeline"][40]["drains"]}
        self.assertEqual(frame["OX-103"]["risk"], "normal")
        self.assertEqual(frame["OX-108"]["risk"], "normal")
        self.assertEqual(len(second["intervention"]["scenario"]["interventions"]), 2)

    def test_long_storm_keeps_producing_staggered_failures(self):
        result = simulate(38, 420)
        seen = {drain["id"]: set() for drain in result["network"]["drains"]}
        for frame in result["timeline"]:
            for drain in frame["drains"]:
                if drain["overflow_at_minute"] is not None:
                    seen[drain["id"]].add(drain["overflow_at_minute"])
        self.assertTrue(all(events for events in seen.values()))
        self.assertTrue(any(len(events) >= 2 for events in seen.values()))


if __name__ == "__main__":
    unittest.main()
